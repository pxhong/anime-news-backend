from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from works.views import video_stream

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('works.urls')),

    # ✅ 唯一视频流入口
    path('media/<path:path>', video_stream, name='video_stream'),
]

# ✅ 只在 DEBUG=True 时提供静态文件（不影响 media 路由）
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)