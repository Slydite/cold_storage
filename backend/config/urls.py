from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from apps.facilities.views import FacilityViewSet
from apps.parties.views import PartyViewSet
from apps.inventory.views import CommodityViewSet, GRNViewSet, LotViewSet

router = DefaultRouter()
router.register(r'facilities', FacilityViewSet, basename='facility')
router.register(r'parties', PartyViewSet, basename='party')
router.register(r'commodities', CommodityViewSet, basename='commodity')
router.register(r'grns', GRNViewSet, basename='grn')
router.register(r'lots', LotViewSet, basename='lot')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include(router.urls)),
    
    # OpenAPI Schema and documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
