from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .selectors import get_facility_list, get_facility_by_id
from .services import create_facility, update_facility
from .serializers import FacilityInputSerializer, FacilityOutputSerializer

from .models import Facility

class FacilityViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Facility.objects.none()

    @extend_schema(
        responses={200: FacilityOutputSerializer(many=True)},
        summary="List all facilities"
    )
    def list(self, request):
        facilities = get_facility_list()
        serializer = FacilityOutputSerializer(facilities, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: FacilityOutputSerializer, 404: None},
        summary="Retrieve a facility by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            facility = get_facility_by_id(pk)
        except Exception:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = FacilityOutputSerializer(facility)
        return Response(serializer.data)

    @extend_schema(
        request=FacilityInputSerializer,
        responses={201: FacilityOutputSerializer, 400: None},
        summary="Create a new facility"
    )
    def create(self, request):
        serializer = FacilityInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            facility = create_facility(
                name=serializer.validated_data['name'],
                code=serializer.validated_data['code'],
                address=serializer.validated_data.get('address', '')
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        output_serializer = FacilityOutputSerializer(facility)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=FacilityInputSerializer,
        responses={200: FacilityOutputSerializer, 400: None},
        summary="Update an existing facility"
    )
    def update(self, request, pk=None):
        serializer = FacilityInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            facility = update_facility(
                facility_id=pk,
                name=serializer.validated_data['name'],
                code=serializer.validated_data['code'],
                address=serializer.validated_data.get('address', '')
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        output_serializer = FacilityOutputSerializer(facility)
        return Response(output_serializer.data)
