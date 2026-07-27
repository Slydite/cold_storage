from django.urls import path
from .views import StockSummaryView, GRNRegisterView, DNRegisterView, InvoiceRegisterView, PaymentRegisterView

urlpatterns = [
    path('reports/stock-summary/', StockSummaryView.as_view(), name='report-stock-summary'),
    path('reports/grn-register/', GRNRegisterView.as_view(), name='report-grn-register'),
    path('reports/dn-register/', DNRegisterView.as_view(), name='report-dn-register'),
    path('reports/invoices/', InvoiceRegisterView.as_view(), name='report-invoice-register'),
    path('reports/payments/', PaymentRegisterView.as_view(), name='report-payment-register'),
]

