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

    # ✅ 当前登录用户的作品列表（分页）
    @action(detail=False, methods=['get'])
    def mine(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': '请先登录'}, status=401)
        queryset = Work.objects.filter(author=request.user).order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # ✅ 修复：perform_destroy 必须在类内部（缩进 4 格）
    def perform_destroy(self, instance):
        # 删除视频文件
        if instance.file:
            instance.file.delete(save=False)
        # 删除封面图
        if instance.cover:
            instance.cover.delete(save=False)
        instance.delete()


# ============================================================
# 视频流接口
# ============================================================

def video_stream(request, path):
    """视频流接口，支持 Range 请求"""
    file_path = os.path.join(settings.MEDIA_ROOT, path)

    if not os.path.exists(file_path):
        return HttpResponse(status=404)

    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'video/mp4'

    range_header = request.META.get('HTTP_RANGE', '').strip()

    if not range_header or not range_header.startswith('bytes='):
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type
        )
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = file_size
        return response

    range_value = range_header[6:]
    start = 0
    end = file_size - 1

    if '-' in range_value:
        parts = range_value.split('-')
        if parts[0]:
            start = int(parts[0])
        if parts[1]:
            end = int(parts[1])

    if range_value.startswith('-'):
        start = file_size - int(range_value[1:])
        end = file_size - 1

    if start >= file_size or start > end:
        response = HttpResponse(status=416)
        response['Content-Range'] = f'bytes */{file_size}'
        return response

    start = max(0, start)
    end = min(end, file_size - 1)
    length = end - start + 1

    response = FileResponse(
        open(file_path, 'rb'),
        content_type=content_type,
        status=206
    )
    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    response['Accept-Ranges'] = 'bytes'
    response['Content-Length'] = length

    return response