from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .selectors import (
    get_chambers_list,
    get_chamber_by_id,
    get_floors_list,
    get_floor_by_id,
    get_blocks_list,
    get_block_by_id
)
from .services import (
    create_chamber,
    update_chamber,
    create_floor,
    update_floor,
    create_block,
    update_block
)
from .serializers import (
    ChamberInputSerializer,
    ChamberUpdateInputSerializer,
    ChamberOutputSerializer,
    FloorInputSerializer,
    FloorUpdateInputSerializer,
    FloorOutputSerializer,
    BlockInputSerializer,
    BlockUpdateInputSerializer,
    BlockOutputSerializer
)
from .models import Chamber, Floor, Block


class ChamberViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Chamber.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Facility ID"),
            OpenApiParameter('is_active', OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False, description="Filter by active status"),
        ],
        responses={200: ChamberOutputSerializer(many=True)},
        summary="List chambers"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        is_active_param = request.query_params.get('is_active')

        is_active_filter = None
        if is_active_param is not None:
            is_active_filter = is_active_param.lower() in ['true', '1', 'yes']

        try:
            chambers = get_chambers_list(
                facility_id=int(facility_id) if facility_id else None,
                is_active=is_active_filter
            )
        except ValueError:
            raise ValidationError({"detail": "Invalid ID format."})

        serializer = ChamberOutputSerializer(chambers, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: ChamberOutputSerializer, 404: None},
        summary="Retrieve a chamber by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            chamber = get_chamber_by_id(pk)
        except (Chamber.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ChamberOutputSerializer(chamber)
        return Response(serializer.data)

    @extend_schema(
        request=ChamberInputSerializer,
        responses={201: ChamberOutputSerializer, 400: None},
        summary="Create a new chamber"
    )
    def create(self, request):
        serializer = ChamberInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            chamber = create_chamber(
                facility_id=serializer.validated_data['facility_id'],
                name=serializer.validated_data['name'],
                sort_order=serializer.validated_data.get('sort_order', 0),
                is_active=serializer.validated_data.get('is_active', True)
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = ChamberOutputSerializer(chamber)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=ChamberUpdateInputSerializer,
        responses={200: ChamberOutputSerializer, 400: None},
        summary="Update an existing chamber"
    )
    def update(self, request, pk=None):
        serializer = ChamberUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            chamber = update_chamber(
                chamber_id=pk,
                **serializer.validated_data
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = ChamberOutputSerializer(chamber)
        return Response(output_serializer.data)


class FloorViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Floor.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Facility ID"),
            OpenApiParameter('chamber_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Chamber ID"),
            OpenApiParameter('is_active', OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False, description="Filter by active status"),
        ],
        responses={200: FloorOutputSerializer(many=True)},
        summary="List all floors"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        chamber_id = request.query_params.get('chamber_id')
        is_active_param = request.query_params.get('is_active')

        is_active_filter = None
        if is_active_param is not None:
            is_active_filter = is_active_param.lower() in ['true', '1', 'yes']

        try:
            floors = get_floors_list(
                chamber_id=int(chamber_id) if chamber_id else None,
                facility_id=int(facility_id) if facility_id else None,
                is_active=is_active_filter
            )
        except ValueError:
            raise ValidationError({"detail": "Invalid ID format."})

        serializer = FloorOutputSerializer(floors, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: FloorOutputSerializer, 404: None},
        summary="Retrieve a floor by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            floor = get_floor_by_id(pk)
        except (Floor.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = FloorOutputSerializer(floor)
        return Response(serializer.data)

    @extend_schema(
        request=FloorInputSerializer,
        responses={201: FloorOutputSerializer, 400: None},
        summary="Create a new floor"
    )
    def create(self, request):
        serializer = FloorInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            floor = create_floor(
                facility_id=serializer.validated_data.get('facility_id'),
                chamber_id=serializer.validated_data['chamber_id'],
                name=serializer.validated_data['name'],
                sort_order=serializer.validated_data.get('sort_order', 0),
                is_active=serializer.validated_data.get('is_active', True)
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = FloorOutputSerializer(floor)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=FloorUpdateInputSerializer,
        responses={200: FloorOutputSerializer, 400: None},
        summary="Update an existing floor"
    )
    def update(self, request, pk=None):
        serializer = FloorUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            floor = update_floor(
                floor_id=pk,
                **serializer.validated_data
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = FloorOutputSerializer(floor)
        return Response(output_serializer.data)


class BlockViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Block.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Facility ID"),
            OpenApiParameter('chamber_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Chamber ID"),
            OpenApiParameter('floor_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Floor ID"),
            OpenApiParameter('is_active', OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False, description="Filter by active status"),
        ],
        responses={200: BlockOutputSerializer(many=True)},
        summary="List blocks"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        chamber_id = request.query_params.get('chamber_id')
        floor_id = request.query_params.get('floor_id')
        is_active_param = request.query_params.get('is_active')

        is_active_filter = None
        if is_active_param is not None:
            is_active_filter = is_active_param.lower() in ['true', '1', 'yes']

        try:
            blocks = get_blocks_list(
                floor_id=int(floor_id) if floor_id else None,
                chamber_id=int(chamber_id) if chamber_id else None,
                facility_id=int(facility_id) if facility_id else None,
                is_active=is_active_filter
            )
        except ValueError:
            raise ValidationError({"detail": "Invalid ID format."})

        serializer = BlockOutputSerializer(blocks, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: BlockOutputSerializer, 404: None},
        summary="Retrieve a block by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            block = get_block_by_id(pk)
        except (Block.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BlockOutputSerializer(block)
        return Response(serializer.data)

    @extend_schema(
        request=BlockInputSerializer,
        responses={201: BlockOutputSerializer, 400: None},
        summary="Create a new block"
    )
    def create(self, request):
        serializer = BlockInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            block = create_block(
                facility_id=serializer.validated_data.get('facility_id'),
                chamber_id=serializer.validated_data.get('chamber_id'),
                floor_id=serializer.validated_data['floor_id'],
                name=serializer.validated_data['name'],
                sort_order=serializer.validated_data.get('sort_order', 0),
                capacity_bags=serializer.validated_data.get('capacity_bags'),
                is_active=serializer.validated_data.get('is_active', True)
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = BlockOutputSerializer(block)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=BlockUpdateInputSerializer,
        responses={200: BlockOutputSerializer, 400: None},
        summary="Update an existing block"
    )
    def update(self, request, pk=None):
        serializer = BlockUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            block = update_block(
                block_id=pk,
                **serializer.validated_data
            )
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = BlockOutputSerializer(block)
        return Response(output_serializer.data)

