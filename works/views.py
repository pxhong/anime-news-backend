import os
import mimetypes
import shutil
import subprocess
from datetime import datetime

from django.conf import settings
from django.http import FileResponse, HttpResponse
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Work, Like
from .serializers import WorkSerializer


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user


# ============================================================
# 转码工具函数（模块级，OK）
# ============================================================

def _run_cmd(cmd, timeout=900):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stderr
    except FileNotFoundError:
        return False, '未找到 ffmpeg/ffprobe'
    except subprocess.TimeoutExpired:
        return False, '执行超时'
    except Exception as e:
        return False, str(e)


def _get_codec(path, stream_type):
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', f'{stream_type}:0',
        '-show_entries', 'stream=codec_name',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        path,
    ]
    ok, _ = _run_cmd(cmd, timeout=60)
    if not ok:
        return ''
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
        return out.strip().split('\n')[0].strip()
    except Exception:
        return ''


def transcode_video(source_path):
    if not os.path.exists(source_path):
        return False, source_path

    video_codec = _get_codec(source_path, 'v')
    audio_codec = _get_codec(source_path, 'a')

    dir_name = os.path.dirname(source_path)
    base, ext = os.path.splitext(os.path.basename(source_path))
    tmp_path = os.path.join(dir_name, f'.transcoding_{base}{ext or ".mp4"}')

    already_compatible = video_codec == 'h264' and audio_codec in ('aac', '')

    if already_compatible:
        cmd = ['ffmpeg', '-y', '-i', source_path,
               '-c', 'copy', '-movflags', '+faststart', tmp_path]
    else:
        cmd = ['ffmpeg', '-y', '-i', source_path,
               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
               '-c:a', 'aac', '-b:a', '128k',
               '-movflags', '+faststart', tmp_path]

    ok, _ = _run_cmd(cmd)
    if ok and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
        os.replace(tmp_path, source_path)
        return True, source_path

    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    return False, source_path


# ============================================================
# 作品视图（chunk_upload / _merge_chunks 必须在类里面！）
# ============================================================

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
            return Response({'liked': False, 'likes_count': work.likes})
        else:
            Like.objects.create(user=user, work=work)
            work.likes += 1
            work.save()
            return Response({'liked': True, 'likes_count': work.likes})

    @action(detail=True, methods=['get'])
    def like_status(self, request, pk=None):
        work = self.get_object()
        user = request.user
        if not user.is_authenticated:
            return Response({'liked': False, 'likes_count': work.likes})
        liked = Like.objects.filter(user=user, work=work).exists()
        return Response({'liked': liked, 'likes_count': work.likes})

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

    # ⬇️⬇️ 关键：chunk_upload 必须在类里面（缩进4格）⬇️⬇️
    @action(detail=False, methods=['post'])
    def chunk_upload(self, request):
        """分片上传接口，接收: chunk_index, total_chunks, file_id, chunk"""
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

        temp_dir = os.path.join(settings.MEDIA_ROOT, f'temp_uploads/{file_id}')
        os.makedirs(temp_dir, exist_ok=True)

        chunk_path = os.path.join(temp_dir, f'chunk_{chunk_index}')
        with open(chunk_path, 'wb+') as destination:
            for chunk in chunk_file.chunks():
                destination.write(chunk)

        uploaded_chunks = os.listdir(temp_dir)
        if len(uploaded_chunks) >= total_chunks:
            return self._merge_chunks(file_id, temp_dir, total_chunks, request)

        return Response({
            'status': 'partial',
            'chunk_index': chunk_index,
            'total': total_chunks,
            'uploaded': len(uploaded_chunks)
        }, status=status.HTTP_200_OK)

    def _merge_chunks(self, file_id, temp_dir, total_chunks, request):
        """合并分片 + 自动转码"""
        file_ext = request.POST.get('file_ext', '.mp4')
        filename = f'{file_id}{file_ext}'

        date_path = datetime.now().strftime('%Y/%m')
        save_dir = os.path.join(settings.MEDIA_ROOT, f'works/videos/{date_path}')
        os.makedirs(save_dir, exist_ok=True)

        save_path = os.path.join(save_dir, filename)

        with open(save_path, 'wb') as output_file:
            for i in range(total_chunks):
                chunk_path = os.path.join(temp_dir, f'chunk_{i}')
                if not os.path.exists(chunk_path):
                    return Response({'error': f'分片 {i} 缺失'}, status=status.HTTP_400_BAD_REQUEST)
                with open(chunk_path, 'rb') as chunk_file:
                    output_file.write(chunk_file.read())

        shutil.rmtree(temp_dir, ignore_errors=True)

        # 自动转码
        transcoded, final_path = transcode_video(save_path)

        relative_path = f'works/videos/{date_path}/{os.path.basename(final_path)}'

        return Response({
            'status': 'complete',
            'file_path': relative_path,
            'full_url': f'/media/{relative_path}',
            'transcoded': transcoded,
            'warning': '' if transcoded else '视频转码失败，已保留原文件'
        }, status=status.HTTP_200_OK)


# ============================================================
# 视频流接口（模块级普通视图，OK）
# ============================================================

def video_stream(request, path):
    file_path = os.path.join(settings.MEDIA_ROOT, path)

    if not os.path.exists(file_path):
        return HttpResponse(status=404)

    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'video/mp4'

    try:
        from django_ranged_response import RangedFileResponse
        return RangedFileResponse(
            open(file_path, 'rb'),
            request=request,
            content_type=content_type,
        )
    except ImportError:
        response = FileResponse(open(file_path, 'rb'), content_type=content_type)
        response['Accept-Ranges'] = 'bytes'
        return response