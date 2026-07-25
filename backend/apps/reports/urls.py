from django.urls import path
from .views import StockSummaryView, GRNRegisterView, DNRegisterView, RentRunReportView, InvoiceRegisterView

urlpatterns = [
    path('reports/stock-summary/', StockSummaryView.as_view(), name='report-stock-summary'),
    path('reports/grn-register/', GRNRegisterView.as_view(), name='report-grn-register'),
    path('reports/dn-register/', DNRegisterView.as_view(), name='report-dn-register'),
    path('reports/rent-runs/<int:rent_run_id>/', RentRunReportView.as_view(), name='report-rent-run'),
    path('reports/invoices/', InvoiceRegisterView.as_view(), name='report-invoice-register'),
]
