from rest_framework.routers import DefaultRouter
from .views import WorkViewSet

router = DefaultRouter()
router.register(r'works', WorkViewSet, basename='work')

urlpatterns = router.urls