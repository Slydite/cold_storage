from rest_framework.routers import DefaultRouter
from .views import ChamberViewSet, FloorViewSet, BlockViewSet

router = DefaultRouter()
router.register(r'chambers', ChamberViewSet, basename='chamber')
router.register(r'floors', FloorViewSet, basename='floor')
router.register(r'blocks', BlockViewSet, basename='block')

urlpatterns = router.urls

