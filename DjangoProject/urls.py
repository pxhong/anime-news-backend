from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from works.views import video_stream

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('works.urls')),

    # ✅ 视频流接口（支持拖动进度条）
    # 用户访问 /media/video/xxx.mp4 时会走视频流接口
    path('media/<path:path>', video_stream),
]

# 开发环境下提供静态文件和媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)