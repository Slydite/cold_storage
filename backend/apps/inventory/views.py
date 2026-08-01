from django.http import HttpResponse
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from libs.renderers import PDFRenderer
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from libs.choices import ChargeMode
from .selectors import (
    get_commodities_list,
    get_commodity_by_id,
    get_grns_list,
    get_grn_by_id,
    get_lots_list,
    get_lot_by_id
)
from .services import (
    create_commodity,
    update_commodity,
    create_grn,
    post_grn,
    cancel_grn,
    withdraw_stock_from_lot,
    build_grn_pdf,
    email_grn_to_party,
    adjust_lot_stock
)
from .serializers import (
    CommodityInputSerializer,
    CommodityOutputSerializer,
    GRNCreateInputSerializer,
    GRNOutputSerializer,
    LotOutputSerializer,
    LotWithdrawalInputSerializer,
    LotReserveNumberInputSerializer,
    LotReserveNumberOutputSerializer,
    LotAdjustmentInputSerializer
)
from .models import Commodity, GRN, Lot

class CommodityViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Commodity.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('is_active', OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False, description="Filter by active status"),
        ],
        responses={200: CommodityOutputSerializer(many=True)},
        summary="List all commodities for a facility"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})

        is_active_param = request.query_params.get('is_active')
        is_active_filter = None
        if is_active_param is not None:
            is_active_filter = is_active_param.lower() in ['true', '1', 'yes']

        try:
            commodities = get_commodities_list(facility_id=int(facility_id), is_active=is_active_filter)
        except ValueError:
            raise ValidationError({"facility_id": "Must be an integer."})

        serializer = CommodityOutputSerializer(commodities, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: CommodityOutputSerializer, 404: None},
        summary="Retrieve a commodity by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            commodity = get_commodity_by_id(pk)
        except (Commodity.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CommodityOutputSerializer(commodity)
        return Response(serializer.data)

    @extend_schema(
        request=CommodityInputSerializer,
        responses={201: CommodityOutputSerializer, 400: None},
        summary="Create a new commodity (code is auto-generated server-side)"
    )
    def create(self, request):
        serializer = CommodityInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            commodity = create_commodity(
                facility_id=serializer.validated_data['facility_id'],
                name=serializer.validated_data['name'],
                unit=serializer.validated_data.get('unit', 'BAGS'),
                description=serializer.validated_data.get('description', ''),
                is_active=serializer.validated_data.get('is_active', True)
            )
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = CommodityOutputSerializer(commodity)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=CommodityInputSerializer,
        responses={200: CommodityOutputSerializer, 400: None},
        summary="Update an existing commodity"
    )
    def update(self, request, pk=None):
        serializer = CommodityInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            commodity = update_commodity(
                commodity_id=pk,
                name=serializer.validated_data['name'],
                unit=serializer.validated_data.get('unit', 'BAGS'),
                description=serializer.validated_data.get('description', ''),
                is_active=serializer.validated_data.get('is_active', True)
            )
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = CommodityOutputSerializer(commodity)
        return Response(output_serializer.data)



class GRNViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = GRN.objects.none()
    search_fields = ('grn_number', 'party__name', 'vehicle_number', 'legacy_ref')

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('party_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Party ID"),
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by Status (DRAFT, POSTED, CANCELLED)"),
        ],
        responses={200: GRNOutputSerializer(many=True)},
        summary="List Goods Receipt Notes (GRNs)"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})

        party_id = request.query_params.get('party_id')
        status_param = request.query_params.get('status')

        try:
            grns = get_grns_list(
                facility_id=int(facility_id),
                party_id=int(party_id) if party_id else None,
                status=status_param
            )
        except ValueError:
            raise ValidationError({"facility_id": "Invalid ID format."})

        serializer = GRNOutputSerializer(grns, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: GRNOutputSerializer, 404: None},
        summary="Retrieve a GRN by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            grn = get_grn_by_id(pk)
        except (GRN.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = GRNOutputSerializer(grn)
        return Response(serializer.data)

    @extend_schema(
        request=GRNCreateInputSerializer,
        responses={201: GRNOutputSerializer, 400: None},
        summary="Create a new Goods Receipt Note (GRN)"
    )
    def create(self, request):
        serializer = GRNCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            grn = create_grn(
                facility_id=serializer.validated_data['facility_id'],
                party_id=serializer.validated_data['party_id'],
                receipt_date=serializer.validated_data['receipt_date'],
                vehicle_number=serializer.validated_data.get('vehicle_number', ''),
                driver_name=serializer.validated_data.get('driver_name', ''),
                remarks=serializer.validated_data.get('remarks', ''),
                loading_charge=serializer.validated_data.get('loading_charge', 0),
                bill_no=serializer.validated_data.get('bill_no', ''),
                bilty_no=serializer.validated_data.get('bilty_no', ''),
                transporter=serializer.validated_data.get('transporter', ''),
                preservation_rate_per_bag_per_month=serializer.validated_data.get('preservation_rate_per_bag_per_month', 0),
                loading_unloading_rate_per_bag=serializer.validated_data.get('loading_unloading_rate_per_bag', 0),
                loading_charge_mode=serializer.validated_data.get('loading_charge_mode', ChargeMode.FLAT),
                inward_time=serializer.validated_data.get('inward_time', None),
                status=serializer.validated_data.get('status', GRN.Status.POSTED),
                items=serializer.validated_data.get('items', []),
                require_location=True
            )
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = GRNOutputSerializer(grn)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={200: GRNOutputSerializer, 400: None},
        summary="Post a DRAFT GRN"
    )
    @action(detail=True, methods=['post'], url_path='post')
    def post_grn_action(self, request, pk=None):
        try:
            grn = post_grn(grn_id=pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(GRNOutputSerializer(grn).data)

    @extend_schema(
        responses={200: GRNOutputSerializer, 400: None},
        summary="Cancel a DRAFT GRN"
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_grn_action(self, request, pk=None):
        try:
            grn = cancel_grn(grn_id=pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(GRNOutputSerializer(grn).data)

    @extend_schema(
        responses={(200, 'application/pdf'): OpenApiTypes.BINARY, 400: None, 404: None},
        summary="Stream PDF for a GRN"
    )
    @action(detail=True, methods=['get'], url_path='pdf', renderer_classes=[PDFRenderer])
    def pdf(self, request, pk=None):
        try:
            grn = get_grn_by_id(pk)
            pdf_bytes = build_grn_pdf(grn_id=grn.id)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (GRN.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{grn.grn_number}.pdf"'
        return response

    @extend_schema(
        request=None,
        responses={200: GRNOutputSerializer, 400: OpenApiTypes.OBJECT, 502: OpenApiTypes.OBJECT},
        summary="Email GRN PDF to the client/party"
    )
    @action(detail=True, methods=['post'], url_path='email')
    def email(self, request, pk=None):
        try:
            email_grn_to_party(grn_id=pk)
            grn = get_grn_by_id(pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"Failed to send email: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(GRNOutputSerializer(grn).data)



class LotViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Lot.objects.none()
    search_fields = ('lot_number', 'grn__grn_number', 'legacy_ref')

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Facility (cold storage) ID. Omit to view stock across every facility."),
            OpenApiParameter('party_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Party ID"),
            OpenApiParameter('commodity_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Commodity ID"),
            OpenApiParameter('chamber', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by Chamber text"),
            OpenApiParameter('floor', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by Floor text"),
            OpenApiParameter('chamber_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Chamber ID"),
            OpenApiParameter('floor_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Floor ID"),
            OpenApiParameter('block_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Block ID"),
            OpenApiParameter('in_stock_only', OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False, description="Only show lots with remaining_qty > 0"),
        ],
        responses={200: LotOutputSerializer(many=True)},
        summary="List inventory lots"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        party_id = request.query_params.get('party_id')
        commodity_id = request.query_params.get('commodity_id')
        chamber = request.query_params.get('chamber')
        floor = request.query_params.get('floor')
        chamber_id = request.query_params.get('chamber_id')
        floor_id = request.query_params.get('floor_id')
        block_id = request.query_params.get('block_id')
        in_stock_param = request.query_params.get('in_stock_only')

        in_stock_only = False
        if in_stock_param is not None:
            in_stock_only = in_stock_param.lower() in ['true', '1', 'yes']

        try:
            lots = get_lots_list(
                facility_id=int(facility_id) if facility_id else None,
                party_id=int(party_id) if party_id else None,
                commodity_id=int(commodity_id) if commodity_id else None,
                chamber=chamber,
                floor=floor,
                chamber_id=int(chamber_id) if chamber_id else None,
                floor_id=int(floor_id) if floor_id else None,
                block_id=int(block_id) if block_id else None,
                in_stock_only=in_stock_only
            )
        except ValueError:
            raise ValidationError({"detail": "Invalid query parameter format."})

        serializer = LotOutputSerializer(lots, many=True)
        return Response(serializer.data)


    @extend_schema(
        responses={200: LotOutputSerializer, 404: None},
        summary="Retrieve a lot by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            lot = get_lot_by_id(pk)
        except (Lot.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = LotOutputSerializer(lot)
        return Response(serializer.data)

    @extend_schema(
        request=LotWithdrawalInputSerializer,
        responses={200: LotOutputSerializer, 400: None},
        summary="Withdraw stock from a lot"
    )
    @action(detail=True, methods=['post'], url_path='withdraw')
    def withdraw(self, request, pk=None):
        serializer = LotWithdrawalInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_lot = withdraw_stock_from_lot(
                lot_id=pk,
                qty_to_withdraw=serializer.validated_data['qty']
            )
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = LotOutputSerializer(updated_lot)
        return Response(output_serializer.data)

    @extend_schema(
        request=LotReserveNumberInputSerializer,
        responses={201: LotReserveNumberOutputSerializer, 400: None},
        summary="Reserve a sequential lot number for a facility"
    )
    @action(detail=False, methods=['post'], url_path='reserve-number')
    def reserve_number(self, request):
        serializer = LotReserveNumberInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        facility_id = serializer.validated_data['facility_id']

        try:
            from libs.sequences import get_next_sequence_number
            from libs.lookups import get_facility_or_raise
            facility = get_facility_or_raise(facility_id)
            lot_number = get_next_sequence_number(facility=facility, sequence_type='LOT')
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = LotReserveNumberOutputSerializer({"lot_number": lot_number})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=LotAdjustmentInputSerializer,
        responses={200: LotOutputSerializer, 400: None},
        summary="Adjust stock of a lot"
    )
    @action(detail=True, methods=['post'], url_path='adjust')
    def adjust(self, request, pk=None):
        serializer = LotAdjustmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        adjustment_date = serializer.validated_data.get('adjustment_date') or timezone.localdate()

        try:
            adjust_lot_stock(
                lot_id=pk,
                reason=serializer.validated_data['reason'],
                adjustment_date=adjustment_date,
                new_qty=serializer.validated_data.get('new_qty'),
                qty_delta=serializer.validated_data.get('qty_delta'),
                note=serializer.validated_data.get('note', ''),
                adjusted_by=request.user
            )
            updated_lot = get_lot_by_id(pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = LotOutputSerializer(updated_lot)
        return Response(output_serializer.data)

