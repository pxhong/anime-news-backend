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

    # ✅ 删除时清理文件
    def perform_destroy(self, instance):
        if instance.file:
            instance.file.delete(save=False)
        if instance.cover:
            instance.cover.delete(save=False)
        instance.delete()


# ============================================================
# 视频流接口
# ============================================================

def video_stream(request, path):
    """
    视频流接口（简化版）
    """
    import os
    from django.http import FileResponse
    from django.conf import settings

    file_path = os.path.join(settings.MEDIA_ROOT, path)

    if not os.path.exists(file_path):
        return HttpResponse(status=404)

    # ✅ 直接返回 FileResponse，让 Django 处理 Range
    response = FileResponse(
        open(file_path, 'rb'),
        content_type='video/mp4',
        as_attachment=False
    )
    response['Accept-Ranges'] = 'bytes'
    response['Content-Length'] = os.path.getsize(file_path)
    return response