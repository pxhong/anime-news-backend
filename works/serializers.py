from rest_framework import serializers
from .models import Work,Like
from users.serializers import UserSerializer


class WorkSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    file = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    class Meta:
        model = Work
        fields = [
            'id', 'author', 'title', 'content', 'work_type',
            'file', 'cover', 'created_at', 'updated_at', 'views', 'likes'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at', 'views', 'likes']

    class LikeSerializer(serializers.ModelSerializer):
        class Meta:
            model = Like
            fields = ['id', 'user', 'work', 'created_at']
            read_only_fields = ['user', 'created_at']