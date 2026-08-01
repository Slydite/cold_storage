from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet
from .views_exports import InvoiceRegisterExportView, TallyExportView

router = DefaultRouter()
router.register('invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('exports/invoice-register/', InvoiceRegisterExportView.as_view(), name='export-invoice-register'),
    path('exports/tally/', TallyExportView.as_view(), name='export-tally'),
] + router.urls

