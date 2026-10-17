from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from works.models import Work

from .models import Comment
from .pagination import CommentPagination
from .permissions import IsCommentOwnerOrWorkAuthorOrStaff
from .serializers import CommentCreateSerializer, CommentSerializer


class WorkCommentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = CommentPagination

    def get_work(self):
        if not hasattr(self, '_work'):
            self._work = get_object_or_404(Work, pk=self.kwargs['work_id'])
        return self._work

    def get_queryset(self):
        return (
            Comment.objects
            .filter(work=self.get_work(), parent__isnull=True)
            .select_related('user', 'work', 'reply_to')
            .prefetch_related('replies__user', 'replies__reply_to')
        )

    def get_serializer_class(self):
        return CommentCreateSerializer if self.request.method == 'POST' else CommentSerializer

    def create(self, request, *args, **kwargs):
        work = self.get_work()
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        if Comment.objects.filter(user=request.user,
                                  created_at__gte=now - timedelta(seconds=2)).exists():
            return Response({'detail': '发送太频繁，请稍后再试'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        parent = None
        reply_to = None
        parent_id = serializer.validated_data.get('parent_id')
        if parent_id:
            target = (Comment.objects
                      .filter(pk=parent_id, work=work)
                      .select_related('parent', 'user').first())
            if not target:
                return Response({'detail': '要回复的评论不存在'},
                                status=status.HTTP_400_BAD_REQUEST)
            if target.parent_id:          # 回复“回复”：归到同一条顶层评论
                parent = target.parent
                reply_to = target.user
            else:
                parent = target

        comment = Comment.objects.create(
            work=work,
            user=request.user,
            parent=parent,
            reply_to=reply_to,
            content=serializer.validated_data['content'],
        )
        data = CommentSerializer(comment, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)


class CommentRepliesView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CommentSerializer
    pagination_class = CommentPagination

    def get_queryset(self):
        parent = get_object_or_404(Comment, pk=self.kwargs['pk'])
        return (Comment.objects
                .filter(parent=parent)
                .select_related('user', 'work', 'reply_to')
                .order_by('created_at'))


class CommentDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCommentOwnerOrWorkAuthorOrStaff]
    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.select_related('work')