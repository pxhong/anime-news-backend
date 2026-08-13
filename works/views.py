from rest_framework import viewsets, permissions, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Work, Like
from .serializers import WorkSerializer
from django.http import HttpResponse, FileResponse
from django.conf import settings
import os
import mimetypes


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user


class WorkViewSet(viewsets.ModelViewSet):
    queryset = Work.objects.all()
    serializer_class = WorkSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'views', 'likes']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        work = self.get_object()
        user = request.user

        existing_like = Like.objects.filter(user=user, work=work).first()
        if existing_like:
            existing_like.delete()
            work.likes = max(0, work.likes - 1)
            work.save()
            return Response({
                'liked': False,
                'likes_count': work.likes
            })
        else:
            Like.objects.create(user=user, work=work)
            work.likes += 1
            work.save()
            return Response({
                'liked': True,
                'likes_count': work.likes
            })

    @action(detail=True, methods=['get'])
    def like_status(self, request, pk=None):
        work = self.get_object()
        user = request.user

        if not user.is_authenticated:
            return Response({'liked': False, 'likes_count': work.likes})

        liked = Like.objects.filter(user=user, work=work).exists()
        return Response({
            'liked': liked,
            'likes_count': work.likes
        })


# ============================================================
# ✅ 视频流接口（支持拖动进度条）
# ============================================================

def video_stream(request, path):
    """
    视频流接口，支持拖动进度条（Range 请求）
    """
    # 构建完整文件路径
    file_path = os.path.join(settings.MEDIA_ROOT, path)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return HttpResponse(status=404)

    # 获取文件大小
    file_size = os.path.getsize(file_path)

    # 获取文件类型
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'video/mp4'

    # 处理 Range 请求（支持拖动进度条）
    range_header = request.META.get('HTTP_RANGE', '').strip()

    if range_header.startswith('bytes='):
        # 解析 Range
        range_value = range_header[6:]
        start = 0
        end = file_size - 1

        if '-' in range_value:
            parts = range_value.split('-')
            if parts[0]:
                start = int(parts[0])
            if parts[1]:
                end = int(parts[1])

        # 限制范围
        start = max(0, start)
        end = min(end, file_size - 1)
        length = end - start + 1

        # 读取文件片段
        with open(file_path, 'rb') as f:
            f.seek(start)
            data = f.read(length)

        # 返回 206 Partial Content
        response = HttpResponse(data, status=206, content_type=content_type)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = length
    else:
        # 完整文件
        with open(file_path, 'rb') as f:
            data = f.read()

        response = HttpResponse(data, content_type=content_type)
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = file_size

    return response