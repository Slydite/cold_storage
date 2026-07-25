from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.inventory.selectors import get_lots_list, get_grns_list
from apps.inventory.serializers import GRNOutputSerializer
from apps.delivery.selectors import get_delivery_notes_list
from apps.delivery.serializers import DeliveryNoteOutputSerializer
from apps.billing.selectors import get_rent_run_by_id
from apps.billing.serializers import RentRunOutputSerializer
from apps.billing.models import RentRun
from apps.invoicing.selectors import get_invoices_list
from apps.invoicing.serializers import InvoiceOutputSerializer

from .csv_utils import csv_response


class StockSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, description="Filter by Facility ID (omit for all facilities)"),
            OpenApiParameter('export_format', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Response format: 'json' (default) or 'csv'. Named export_format (not 'format') to avoid colliding with DRF's reserved content-negotiation query parameter."),
        ],
        summary="Stock summary report grouped by commodity and chamber"
    )
    def get(self, request):
        facility_id_param = request.query_params.get('facility_id')
        facility_id = None
        if facility_id_param:
            try:
                facility_id = int(facility_id_param)
            except ValueError:
                raise ValidationError({"facility_id": "Must be an integer."})

        fmt = request.query_params.get('export_format', 'json').lower()

        lots = get_lots_list(facility_id=facility_id, in_stock_only=True)

        by_commodity_map = {}
        by_chamber_map = {}

        for lot in lots:
            fac_id = lot.facility_id
            fac_name = lot.facility.name if lot.facility else ""
            comm_id = lot.commodity_id
            comm_name = lot.commodity.name if lot.commodity else ""
            rem_qty = lot.remaining_qty
            unit_weight = lot.unit_weight or Decimal('0.00')

            comm_key = (fac_id, comm_id)
            if comm_key not in by_commodity_map:
                by_commodity_map[comm_key] = {
                    "facility_id": fac_id,
                    "facility_name": fac_name,
                    "commodity_id": comm_id,
                    "commodity_name": comm_name,
                    "total_qty": 0,
                    "total_weight_kg": Decimal('0.00'),
                }
            by_commodity_map[comm_key]["total_qty"] += rem_qty
            by_commodity_map[comm_key]["total_weight_kg"] += Decimal(str(rem_qty)) * Decimal(str(unit_weight))

            chamber = lot.chamber or ""
            chamber_key = (fac_id, chamber)
            if chamber_key not in by_chamber_map:
                by_chamber_map[chamber_key] = {
                    "facility_id": fac_id,
                    "facility_name": fac_name,
                    "chamber": chamber,
                    "total_qty": 0,
                }
            by_chamber_map[chamber_key]["total_qty"] += rem_qty

        by_commodity = []
        for item in by_commodity_map.values():
            by_commodity.append({
                "facility_id": item["facility_id"],
                "facility_name": item["facility_name"],
                "commodity_id": item["commodity_id"],
                "commodity_name": item["commodity_name"],
                "total_qty": item["total_qty"],
                "total_weight_kg": float(item["total_weight_kg"]),
            })

        by_chamber = list(by_chamber_map.values())

        if fmt == 'csv':
            header = ["facility_id", "facility_name", "commodity_id", "commodity_name", "total_qty", "total_weight_kg"]
            rows = [
                [row["facility_id"], row["facility_name"], row["commodity_id"], row["commodity_name"], row["total_qty"], row["total_weight_kg"]]
                for row in by_commodity
            ]
            return csv_response("stock-summary.csv", header, rows)

        return Response({
            "by_commodity": by_commodity,
            "by_chamber": by_chamber
        })


class GRNRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('date_from', OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False, description="Filter by receipt_date >= date_from"),
            OpenApiParameter('date_to', OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False, description="Filter by receipt_date <= date_to"),
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by GRN status"),
            OpenApiParameter('export_format', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Response format: 'json' (default) or 'csv'. Named export_format (not 'format') to avoid colliding with DRF's reserved content-negotiation query parameter."),
        ],
        summary="List Goods Receipt Notes (GRN) report"
    )
    def get(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})
        try:
            facility_id_int = int(facility_id)
        except ValueError:
            raise ValidationError({"facility_id": "Must be an integer."})

        status_param = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        fmt = request.query_params.get('export_format', 'json').lower()

        qs = get_grns_list(facility_id=facility_id_int, status=status_param)
        if date_from:
            qs = qs.filter(receipt_date__gte=date_from)
        if date_to:
            qs = qs.filter(receipt_date__lte=date_to)

        if fmt == 'csv':
            header = ["grn_number", "receipt_date", "party_name", "status", "loading_charge", "total_lots", "total_initial_qty"]
            rows = []
            for grn in qs:
                lots_list = list(grn.lots.all())
                total_initial_qty = sum(lot.initial_qty for lot in lots_list)
                rows.append([
                    grn.grn_number,
                    grn.receipt_date,
                    grn.party.name if grn.party else "",
                    grn.status,
                    grn.loading_charge,
                    len(lots_list),
                    total_initial_qty
                ])
            return csv_response("grn-register.csv", header, rows)

        serializer = GRNOutputSerializer(qs, many=True)
        return Response(serializer.data)


class DNRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('date_from', OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False, description="Filter by dispatch_date >= date_from"),
            OpenApiParameter('date_to', OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False, description="Filter by dispatch_date <= date_to"),
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by Delivery Note status"),
            OpenApiParameter('export_format', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Response format: 'json' (default) or 'csv'. Named export_format (not 'format') to avoid colliding with DRF's reserved content-negotiation query parameter."),
        ],
        summary="List Delivery Notes (DN) report"
    )
    def get(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})
        try:
            facility_id_int = int(facility_id)
        except ValueError:
            raise ValidationError({"facility_id": "Must be an integer."})

        status_param = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        fmt = request.query_params.get('export_format', 'json').lower()

        qs = get_delivery_notes_list(facility_id=facility_id_int, status=status_param)
        if date_from:
            qs = qs.filter(dispatch_date__gte=date_from)
        if date_to:
            qs = qs.filter(dispatch_date__lte=date_to)

        if fmt == 'csv':
            header = ["dn_number", "dispatch_date", "party_name", "status", "total_lines", "total_qty"]
            rows = []
            for dn in qs:
                lines_list = list(dn.lines.all())
                total_qty = sum(line.qty for line in lines_list)
                rows.append([
                    dn.dn_number,
                    dn.dispatch_date,
                    dn.party.name if dn.party else "",
                    dn.status,
                    len(lines_list),
                    total_qty
                ])
            return csv_response("dn-register.csv", header, rows)

        serializer = DeliveryNoteOutputSerializer(qs, many=True)
        return Response(serializer.data)


class RentRunReportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('export_format', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Response format: 'json' (default) or 'csv'. Named export_format (not 'format') to avoid colliding with DRF's reserved content-negotiation query parameter."),
        ],
        summary="Rent run detail report export"
    )
    def get(self, request, rent_run_id: int):
        try:
            rent_run = get_rent_run_by_id(rent_run_id)
        except (RentRun.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        fmt = request.query_params.get('export_format', 'json').lower()

        if fmt == 'csv':
            lines = list(rent_run.lines.all())
            header = ["lot_number", "commodity_name", "party_name", "qty", "weight_category", "rate_per_bag_per_month", "days_stored", "amount"]
            rows = []
            total_qty = 0
            total_amount = Decimal('0.00')
            for line in lines:
                qty = line.qty or 0
                amt = line.amount or Decimal('0.00')
                total_qty += qty
                total_amount += amt
                rows.append([
                    line.lot.lot_number if line.lot else "",
                    line.lot.commodity.name if (line.lot and line.lot.commodity) else "",
                    line.party.name if line.party else "",
                    qty,
                    line.weight_category,
                    line.rate_per_bag_per_month,
                    line.days_stored,
                    amt
                ])
            rows.append([
                "TOTAL",
                "",
                "",
                total_qty,
                "",
                "",
                "",
                total_amount
            ])
            return csv_response(f"rent-run-{rent_run_id}.csv", header, rows)

        serializer = RentRunOutputSerializer(rent_run)
        return Response(serializer.data)


class InvoiceRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('facility_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="Filter by Facility ID"),
            OpenApiParameter('date_from', OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False, description="Filter by invoice_date >= date_from"),
            OpenApiParameter('date_to', OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False, description="Filter by invoice_date <= date_to"),
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Filter by Invoice status"),
            OpenApiParameter('export_format', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="Response format: 'json' (default) or 'csv'. Named export_format (not 'format') to avoid colliding with DRF's reserved content-negotiation query parameter."),
        ],
        summary="List Invoices report"
    )
    def get(self, request):
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            raise ValidationError({"facility_id": "This query parameter is required."})
        try:
            facility_id_int = int(facility_id)
        except ValueError:
            raise ValidationError({"facility_id": "Must be an integer."})

        status_param = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        fmt = request.query_params.get('export_format', 'json').lower()

        qs = get_invoices_list(facility_id=facility_id_int, status=status_param)
        if date_from:
            qs = qs.filter(invoice_date__gte=date_from)
        if date_to:
            qs = qs.filter(invoice_date__lte=date_to)

        if fmt == 'csv':
            header = ["invoice_number", "invoice_date", "party_name", "party_gstin_snapshot", "status", "subtotal", "gst_amount", "total_amount"]
            rows = []
            for inv in qs:
                rows.append([
                    inv.invoice_number,
                    inv.invoice_date,
                    inv.party.name if inv.party else "",
                    inv.party_gstin_snapshot or "",
                    inv.status,
                    inv.subtotal,
                    inv.gst_amount,
                    inv.total_amount
                ])
            return csv_response("invoice-register.csv", header, rows)

        serializer = InvoiceOutputSerializer(qs, many=True)
        return Response(serializer.data)
