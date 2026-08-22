from rest_framework import viewsets, permissions, filters,status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Work, Like
from .serializers import WorkSerializer
from django.http import FileResponse, HttpResponse
from django.conf import settings
import os
import mimetypes
import shutil
from datetime import datetime


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

    def perform_destroy(self, instance):
        if instance.file:
            instance.file.delete(save=False)
        if instance.cover:
            instance.cover.delete(save=False)
        instance.delete()


# ============================================================
# ✅ 视频流接口（使用 FileResponse）
# ============================================================

def video_stream(request, path):
    """
    视频流接口
    使用 FileResponse 流式返回视频文件
    """
    # 构建完整文件路径
    file_path = os.path.join(settings.MEDIA_ROOT, path)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return HttpResponse(status=404)

    # 获取文件类型
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'video/mp4'

    # ✅ 使用 FileResponse 流式返回
    response = FileResponse(
        open(file_path, 'rb'),
        content_type=content_type
    )

    # ✅ 添加 Accept-Ranges 头
    response['Accept-Ranges'] = 'bytes'

    return response


@action(detail=False, methods=['post'])
def chunk_upload(self, request):
    """
    分片上传接口
    接收: chunk_index, total_chunks, file_id, chunk_data
    """
    chunk_index = request.POST.get('chunk_index')
    total_chunks = request.POST.get('total_chunks')
    file_id = request.POST.get('file_id')
    chunk_file = request.FILES.get('chunk')

    if not all([chunk_index, total_chunks, file_id, chunk_file]):
        return Response({'error': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        chunk_index = int(chunk_index)
        total_chunks = int(total_chunks)
    except ValueError:
        return Response({'error': '参数格式错误'}, status=status.HTTP_400_BAD_REQUEST)

    # 临时目录：media/temp_uploads/{file_id}/
    temp_dir = os.path.join(settings.MEDIA_ROOT, f'temp_uploads/{file_id}')
    os.makedirs(temp_dir, exist_ok=True)

    # 保存分片
    chunk_path = os.path.join(temp_dir, f'chunk_{chunk_index}')
    with open(chunk_path, 'wb+') as destination:
        for chunk in chunk_file.chunks():
            destination.write(chunk)

    # 检查是否所有分片都已上传
    uploaded_chunks = os.listdir(temp_dir)

    if len(uploaded_chunks) >= total_chunks:
        # 所有分片已上传，执行合并
        return self._merge_chunks(file_id, temp_dir, total_chunks, request)

    return Response({
        'status': 'partial',
        'chunk_index': chunk_index,
        'total': total_chunks,
        'uploaded': len(uploaded_chunks)
    }, status=status.HTTP_200_OK)


def _merge_chunks(self, file_id, temp_dir, total_chunks, request):
    """合并分片为完整文件"""
    # 构建合并后文件名
    file_ext = request.POST.get('file_ext', '.mp4')
    filename = f'{file_id}{file_ext}'

    # 保存路径：media/works/videos/年/月/
    date_path = datetime.now().strftime('%Y/%m')
    save_dir = os.path.join(settings.MEDIA_ROOT, f'works/videos/{date_path}')
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, filename)

    # 合并分片
    with open(save_path, 'wb') as output_file:
        for i in range(total_chunks):
            chunk_path = os.path.join(temp_dir, f'chunk_{i}')
            if not os.path.exists(chunk_path):
                return Response({
                    'error': f'分片 {i} 缺失'
                }, status=status.HTTP_400_BAD_REQUEST)

            with open(chunk_path, 'rb') as chunk_file:
                output_file.write(chunk_file.read())

    # 删除临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)

    # 返回文件路径
    relative_path = f'works/videos/{date_path}/{filename}'

    return Response({
        'status': 'complete',
        'file_path': relative_path,
        'full_url': f'/media/{relative_path}'
    }, status=status.HTTP_200_OK)