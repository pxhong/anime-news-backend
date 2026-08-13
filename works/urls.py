from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import WorkViewSet, video_stream

router = DefaultRouter()
router.register(r'works', WorkViewSet, basename='work')

urlpatterns = router.urls + [
    # ✅ 视频流接口（支持拖动进度条）
    path('video/<path:path>', video_stream, name='video_stream'),
]