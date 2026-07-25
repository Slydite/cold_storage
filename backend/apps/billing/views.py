from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .selectors import (
    get_rate_cards_list,
    get_rate_card_by_id,
    get_rent_runs_list,
    get_rent_run_by_id
)
from .services import (
    create_rate_card,
    create_rent_run,
    post_rent_run,
    cancel_rent_run
)
from .serializers import (
    RateCardInputSerializer,
    RateCardOutputSerializer,
    RentRunCreateInputSerializer,
    RentRunOutputSerializer
)
from .models import RateCard, RentRun


class RateCardViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RateCard.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('commodity_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Commodity ID"),
            OpenApiParameter('is_active', OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False, description="Filter by active status"),
        ],
        responses={200: RateCardOutputSerializer(many=True)},
        summary="List rate cards for a facility"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})

        commodity_id = request.query_params.get('commodity_id')
        is_active_param = request.query_params.get('is_active')
        is_active_filter = None
        if is_active_param is not None:
            is_active_filter = is_active_param.lower() in ['true', '1', 'yes']

        try:
            rate_cards = get_rate_cards_list(
                facility_id=int(facility_id),
                commodity_id=int(commodity_id) if commodity_id else None,
                is_active=is_active_filter
            )
        except ValueError:
            raise ValidationError({"facility_id": "Must be an integer."})

        serializer = RateCardOutputSerializer(rate_cards, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: RateCardOutputSerializer, 404: None},
        summary="Retrieve a rate card by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            rate_card = get_rate_card_by_id(pk)
        except (RateCard.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = RateCardOutputSerializer(rate_card)
        return Response(serializer.data)

    @extend_schema(
        request=RateCardInputSerializer,
        responses={201: RateCardOutputSerializer, 400: None},
        summary="Create a new rate card"
    )
    def create(self, request):
        serializer = RateCardInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rate_card = create_rate_card(
                facility_id=serializer.validated_data['facility_id'],
                commodity_id=serializer.validated_data['commodity_id'],
                weight_category=serializer.validated_data['weight_category'],
                rate_per_bag_per_month=serializer.validated_data['rate_per_bag_per_month'],
                effective_from=serializer.validated_data['effective_from'],
                is_active=serializer.validated_data.get('is_active', True)
            )
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = RateCardOutputSerializer(rate_card)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class RentRunViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RentRun.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by status (DRAFT, POSTED, CANCELLED)"),
        ],
        responses={200: RentRunOutputSerializer(many=True)},
        summary="List rent runs for a facility"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})

        status_param = request.query_params.get('status')

        try:
            rent_runs = get_rent_runs_list(
                facility_id=int(facility_id),
                status=status_param
            )
        except ValueError:
            raise ValidationError({"facility_id": "Must be an integer."})

        serializer = RentRunOutputSerializer(rent_runs, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: RentRunOutputSerializer, 404: None},
        summary="Retrieve a rent run by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            rent_run = get_rent_run_by_id(pk)
        except (RentRun.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = RentRunOutputSerializer(rent_run)
        return Response(serializer.data)

    @extend_schema(
        request=RentRunCreateInputSerializer,
        responses={201: RentRunOutputSerializer, 400: None},
        summary="Create a new rent run (DRAFT)"
    )
    def create(self, request):
        serializer = RentRunCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rent_run = create_rent_run(
                facility_id=serializer.validated_data['facility_id'],
                period_start=serializer.validated_data['period_start'],
                period_end=serializer.validated_data['period_end']
            )
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = RentRunOutputSerializer(rent_run)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={200: RentRunOutputSerializer, 400: None},
        summary="Post a DRAFT rent run"
    )
    @action(detail=True, methods=['post'], url_path='post')
    def post(self, request, pk=None):
        try:
            rent_run = post_rent_run(rent_run_id=pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RentRunOutputSerializer(rent_run).data)

    @extend_schema(
        responses={200: RentRunOutputSerializer, 400: None},
        summary="Cancel a DRAFT rent run"
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        try:
            rent_run = cancel_rent_run(rent_run_id=pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RentRunOutputSerializer(rent_run).data)
