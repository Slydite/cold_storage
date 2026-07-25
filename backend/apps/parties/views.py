from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .selectors import get_parties_list, get_party_by_id
from .services import create_party, update_party
from .serializers import PartyInputSerializer, PartyOutputSerializer

from .models import Party

class PartyViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Party.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('type', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by Party Type (DEPOSITOR, VENDOR, TRANSPORTER)"),
            OpenApiParameter('is_active', OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False, description="Filter by active status (true/false)"),
        ],
        responses={200: PartyOutputSerializer(many=True)},
        summary="List all parties in a facility"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})

        # Parse query params
        type_filter = request.query_params.get('type')
        is_active_param = request.query_params.get('is_active')
        
        is_active_filter = None
        if is_active_param is not None:
            is_active_filter = is_active_param.lower() in ['true', '1', 'yes']

        try:
            parties = get_parties_list(
                facility_id=int(facility_id),
                type=type_filter,
                is_active=is_active_filter
            )
        except ValueError:
            raise ValidationError({"facility_id": "Must be an integer."})
        
        serializer = PartyOutputSerializer(parties, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: PartyOutputSerializer, 404: None},
        summary="Retrieve a party by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            party = get_party_by_id(pk)
        except Exception:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PartyOutputSerializer(party)
        return Response(serializer.data)

    @extend_schema(
        request=PartyInputSerializer,
        responses={201: PartyOutputSerializer, 400: None},
        summary="Create a new party"
    )
    def create(self, request):
        serializer = PartyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            party = create_party(
                facility_id=serializer.validated_data['facility_id'],
                name=serializer.validated_data['name'],
                code=serializer.validated_data['code'],
                type=serializer.validated_data['type'],
                phone=serializer.validated_data.get('phone', ''),
                email=serializer.validated_data.get('email', ''),
                address=serializer.validated_data.get('address', ''),
                gstin=serializer.validated_data.get('gstin', ''),
                is_active=serializer.validated_data.get('is_active', True)
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        output_serializer = PartyOutputSerializer(party)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=PartyInputSerializer,
        responses={200: PartyOutputSerializer, 400: None},
        summary="Update an existing party"
    )
    def update(self, request, pk=None):
        serializer = PartyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            party = update_party(
                party_id=pk,
                name=serializer.validated_data['name'],
                code=serializer.validated_data['code'],
                type=serializer.validated_data['type'],
                phone=serializer.validated_data.get('phone', ''),
                email=serializer.validated_data.get('email', ''),
                address=serializer.validated_data.get('address', ''),
                gstin=serializer.validated_data.get('gstin', ''),
                is_active=serializer.validated_data.get('is_active', True)
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        output_serializer = PartyOutputSerializer(party)
        return Response(output_serializer.data)
