from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Comment

User = get_user_model()


class CommentUserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'avatar_url']

    def get_avatar_url(self, obj):
        raw = getattr(obj, 'avatar', None)
        if not raw:
            return None
        if hasattr(raw, 'url'):
            try:
                return raw.url
            except Exception:
                return None
        return str(raw)


class CommentSerializer(serializers.ModelSerializer):
    user = CommentUserSerializer(read_only=True)
    reply_to_user = CommentUserSerializer(source='reply_to', read_only=True)
    replies = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at',
                  'reply_to_user', 'replies', 'reply_count', 'can_delete']

    def get_replies(self, obj):
        if obj.parent_id:          # 回复不再嵌套，只做两级
            return []
        qs = obj.replies.select_related('user', 'reply_to').order_by('created_at')[:3]
        return CommentSerializer(qs, many=True, context=self.context).data

    def get_reply_count(self, obj):
        return 0 if obj.parent_id else obj.replies.count()

    def get_can_delete(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or obj.user_id == user.id:
            return True
        return obj.work.author_id == user.id


class CommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=500, trim_whitespace=True)
    parent_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_content(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('评论内容不能为空')
        return value