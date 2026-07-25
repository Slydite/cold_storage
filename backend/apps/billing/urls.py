from rest_framework.routers import DefaultRouter
from .views import RateCardViewSet, RentRunViewSet

router = DefaultRouter()
router.register('rate-cards', RateCardViewSet, basename='rate-card')
router.register('rent-runs', RentRunViewSet, basename='rent-run')

urlpatterns = router.urls
