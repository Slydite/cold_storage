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

from .selectors import (
    get_invoices_list,
    get_invoice_by_id,
)
from .services import (
    generate_invoices_for_uninvoiced_deliveries,
    preview_uninvoiced_charges,
    post_invoice,
    cancel_invoice,
    record_payment,
    delete_payment,
    build_invoice_pdf,
)
from .serializers import (
    GenerateInvoicesInputSerializer,
    InvoiceOutputSerializer,
    InvoicePreviewPartyOutputSerializer,
    PaymentInputSerializer,
    PaymentOutputSerializer,
)
from .models import Invoice, Payment


class InvoiceViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Invoice.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('party_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Party ID"),
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by status (DRAFT, POSTED, CANCELLED)"),
            OpenApiParameter('payment_status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by payment_status (UNPAID, PARTIAL, PAID)"),
        ],
        responses={200: InvoiceOutputSerializer(many=True)},
        summary="List invoices for a facility"
    )
    def list(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})

        party_id = request.query_params.get('party_id')
        status_param = request.query_params.get('status')
        payment_status_param = request.query_params.get('payment_status')

        try:
            invoices = get_invoices_list(
                facility_id=int(facility_id),
                party_id=int(party_id) if party_id else None,
                status=status_param,
                payment_status=payment_status_param,
            )
        except ValueError:
            raise ValidationError({"facility_id": "Must be an integer."})

        serializer = InvoiceOutputSerializer(invoices, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: InvoiceOutputSerializer, 404: None},
        summary="Retrieve an invoice by ID"
    )
    def retrieve(self, request, pk=None):
        try:
            invoice = get_invoice_by_id(pk)
        except (Invoice.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = InvoiceOutputSerializer(invoice)
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('party_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Party ID"),
        ],
        responses={200: InvoicePreviewPartyOutputSerializer(many=True)},
        summary="Preview uninvoiced charges for a facility"
    )
    @action(detail=False, methods=['get'], url_path='preview')
    def preview(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})

        party_id = request.query_params.get('party_id')

        try:
            facility_id_int = int(facility_id)
            party_id_int = int(party_id) if party_id else None
        except ValueError:
            raise ValidationError({"facility_id": "Must be an integer."})

        try:
            previews = preview_uninvoiced_charges(
                facility_id=facility_id_int,
                party_id=party_id_int
            )
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = InvoicePreviewPartyOutputSerializer(previews, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=GenerateInvoicesInputSerializer,
        responses={201: InvoiceOutputSerializer(many=True), 400: None},
        summary="Generate invoices for uninvoiced stock withdrawals"
    )
    def create(self, request):
        serializer = GenerateInvoicesInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invoices = generate_invoices_for_uninvoiced_deliveries(
                facility_id=serializer.validated_data['facility_id'],
                party_id=serializer.validated_data.get('party_id')
            )
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = InvoiceOutputSerializer(invoices, many=True)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={200: InvoiceOutputSerializer, 400: None},
        summary="Post a DRAFT invoice"
    )
    @action(detail=True, methods=['post'], url_path='post')
    def post(self, request, pk=None):
        try:
            invoice = post_invoice(invoice_id=pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (Invoice.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InvoiceOutputSerializer(invoice).data)

    @extend_schema(
        responses={200: InvoiceOutputSerializer, 400: None},
        summary="Cancel a DRAFT invoice"
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        try:
            invoice = cancel_invoice(invoice_id=pk)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (Invoice.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InvoiceOutputSerializer(invoice).data)

    @extend_schema(
        methods=['get'],
        responses={200: PaymentOutputSerializer(many=True), 404: None},
        summary="List payments for an invoice"
    )
    @extend_schema(
        methods=['post'],
        request=PaymentInputSerializer,
        responses={200: InvoiceOutputSerializer, 400: None, 404: None},
        summary="Record a payment for an invoice"
    )
    @action(detail=True, methods=['get', 'post'], url_path='payments')
    def payments(self, request, pk=None):
        try:
            invoice = get_invoice_by_id(pk)
        except (Invoice.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'POST':
            serializer = PaymentInputSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            try:
                record_payment(
                    invoice_id=invoice.id,
                    amount=serializer.validated_data['amount'],
                    payment_date=serializer.validated_data['payment_date'],
                    method=serializer.validated_data.get('method', Payment.Method.CASH),
                    reference=serializer.validated_data.get('reference', ''),
                    notes=serializer.validated_data.get('notes', '')
                )
            except DjangoValidationError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            refreshed_invoice = get_invoice_by_id(invoice.id)
            return Response(InvoiceOutputSerializer(refreshed_invoice).data, status=status.HTTP_200_OK)
        else:
            serializer = PaymentOutputSerializer(invoice.payments.all(), many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: InvoiceOutputSerializer, 400: None, 404: None},
        summary="Delete a payment for an invoice"
    )
    @action(detail=True, methods=['delete'], url_path=r'payments/(?P<payment_id>[^/.]+)')
    def delete_payment_action(self, request, pk=None, payment_id=None):
        try:
            invoice = get_invoice_by_id(pk)
        except (Invoice.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            delete_payment(payment_id=int(payment_id))
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (Payment.DoesNotExist, ValueError):
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        refreshed_invoice = get_invoice_by_id(invoice.id)
        return Response(InvoiceOutputSerializer(refreshed_invoice).data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={(200, 'application/pdf'): OpenApiTypes.BINARY, 400: None, 404: None},
        summary="Stream PDF for an invoice"
    )
    @action(detail=True, methods=['get'], url_path='pdf', renderer_classes=[PDFRenderer])
    def pdf(self, request, pk=None):
        try:
            invoice = get_invoice_by_id(pk)
            pdf_bytes = build_invoice_pdf(invoice_id=invoice.id)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (Invoice.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{invoice.invoice_number}.pdf"'
        return response

