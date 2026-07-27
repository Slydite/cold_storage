from django.core.exceptions import ValidationError as DjangoValidationError
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
        summary="Create a new facility (code is auto-generated server-side)"
    )
    def create(self, request):
        serializer = FacilityInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            facility = create_facility(
                name=serializer.validated_data['name'],
                address=serializer.validated_data.get('address', ''),
                gstin=serializer.validated_data.get('gstin', ''),
                phone=serializer.validated_data.get('phone', ''),
                factory_phone=serializer.validated_data.get('factory_phone', ''),
                bank_account_no=serializer.validated_data.get('bank_account_no', ''),
                bank_ifsc=serializer.validated_data.get('bank_ifsc', ''),
                terms_and_conditions=serializer.validated_data.get('terms_and_conditions', '')
            )
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)
        
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
                address=serializer.validated_data.get('address', ''),
                gstin=serializer.validated_data.get('gstin', ''),
                phone=serializer.validated_data.get('phone', ''),
                factory_phone=serializer.validated_data.get('factory_phone', ''),
                bank_account_no=serializer.validated_data.get('bank_account_no', ''),
                bank_ifsc=serializer.validated_data.get('bank_ifsc', ''),
                terms_and_conditions=serializer.validated_data.get('terms_and_conditions', '')
            )
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response({"detail": str(msg)}, status=status.HTTP_400_BAD_REQUEST)
            
        output_serializer = FacilityOutputSerializer(facility)
        return Response(output_serializer.data)


