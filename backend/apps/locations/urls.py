from rest_framework.routers import DefaultRouter
from .views import FloorViewSet, ChamberViewSet

router = DefaultRouter()
router.register(r'floors', FloorViewSet, basename='floor')
router.register(r'chambers', ChamberViewSet, basename='chamber')

urlpatterns = router.urls
