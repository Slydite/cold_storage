from django.http import HttpResponse
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
    get_delivery_notes_list,
    get_delivery_note_by_id
)
from .services import (
    create_delivery_note,
    post_delivery_note,
    cancel_delivery_note,
    build_delivery_note_pdf,
    email_delivery_note_to_party
)
from .serializers import (
    DeliveryNoteCreateInputSerializer,
    DeliveryNoteOutputSerializer
)
from .models import DeliveryNote


class DeliveryNoteViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = DeliveryNote.objects.none()
    search_fields = ('dn_number', 'party__name', 'vehicle_number', 'legacy_ref')

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('party_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Party ID"),
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by Status (DRAFT, POSTED, CANCELLED)"),
        ],
        responses={200: DeliveryNoteOutputSerializer(many=True)},
        summary="List Delivery Notes"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})

        party_id = request.query_params.get('party_id')
        status_param = request.query_params.get('status')

        try:
            dns = get_delivery_notes_list(
                facility_id=int(facility_id),
                party_id=int(party_id) if party_id else None,
                status=status_param
            )
        except ValueError:
            raise ValidationError({"facility_id": "Invalid ID format."})

        serializer = DeliveryNoteOutputSerializer(dns, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: DeliveryNoteOutputSerializer, 404: None},
        summary="Retrieve a Delivery Note by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            dn = get_delivery_note_by_id(pk)
        except (DeliveryNote.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DeliveryNoteOutputSerializer(dn)
        return Response(serializer.data)

    @extend_schema(
        request=DeliveryNoteCreateInputSerializer,
        responses={201: DeliveryNoteOutputSerializer, 400: None},
        summary="Create a new Delivery Note"
    )
    def create(self, request):
        serializer = DeliveryNoteCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dn = create_delivery_note(
                facility_id=serializer.validated_data['facility_id'],
                party_id=serializer.validated_data['party_id'],
                dispatch_date=serializer.validated_data['dispatch_date'],
                vehicle_number=serializer.validated_data.get('vehicle_number', ''),
                driver_name=serializer.validated_data.get('driver_name', ''),
                transporter=serializer.validated_data.get('transporter', ''),
                remarks=serializer.validated_data.get('remarks', ''),
                loading_charge=serializer.validated_data.get('loading_charge', 0),
                loading_unloading_rate_per_unit=serializer.validated_data.get('loading_unloading_rate_per_unit', 0),
                loading_charge_mode=serializer.validated_data.get('loading_charge_mode', ChargeMode.FLAT),
                status=serializer.validated_data.get('status', DeliveryNote.Status.DRAFT),
                lines=serializer.validated_data.get('lines', [])
            )
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = DeliveryNoteOutputSerializer(dn)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={200: DeliveryNoteOutputSerializer, 400: None},
        summary="Post a DRAFT Delivery Note"
    )
    @action(detail=True, methods=['post'], url_path='post')
    def post_delivery_note_action(self, request, pk=None):
        try:
            dn = post_delivery_note(delivery_note_id=pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DeliveryNoteOutputSerializer(dn).data)

    @extend_schema(
        responses={200: DeliveryNoteOutputSerializer, 400: None},
        summary="Cancel a DRAFT Delivery Note"
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_delivery_note_action(self, request, pk=None):
        try:
            dn = cancel_delivery_note(delivery_note_id=pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DeliveryNoteOutputSerializer(dn).data)

    @extend_schema(
        responses={(200, 'application/pdf'): OpenApiTypes.BINARY, 400: None, 404: None},
        summary="Stream PDF for a Delivery Note"
    )
    @action(detail=True, methods=['get'], url_path='pdf', renderer_classes=[PDFRenderer])
    def pdf(self, request, pk=None):
        try:
            dn = get_delivery_note_by_id(pk)
            pdf_bytes = build_delivery_note_pdf(delivery_note_id=dn.id)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (DeliveryNote.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{dn.dn_number}.pdf"'
        return response

    @extend_schema(
        request=None,
        responses={200: DeliveryNoteOutputSerializer, 400: OpenApiTypes.OBJECT, 502: OpenApiTypes.OBJECT},
        summary="Email Delivery Note PDF to the client/party"
    )
    @action(detail=True, methods=['post'], url_path='email')
    def email(self, request, pk=None):
        try:
            email_delivery_note_to_party(delivery_note_id=pk)
            dn = get_delivery_note_by_id(pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"Failed to send email: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(DeliveryNoteOutputSerializer(dn).data)


