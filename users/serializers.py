from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'account', 'username', 'email', 'password', 'avatar', 'avatar_url', 'bio']
        read_only_fields = ['account']

    def get_avatar_url(self, obj):
        return obj.get_avatar_url()

    def create(self, validated_data):
        # ✅ 自动生成账号
        account = User.generate_account()
        user = User.objects.create_user(
            account=account,
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user


class LoginSerializer(serializers.Serializer):
    account = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        try:
            user = User.objects.get(account=data['account'])
        except User.DoesNotExist:
            raise serializers.ValidationError('账号不存在')

        if not user.check_password(data['password']):
            raise serializers.ValidationError('密码错误')

        if not user.is_active:
            raise serializers.ValidationError('账号已禁用')

        return {'user': user}


class UserProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'account', 'username', 'email', 'avatar', 'avatar_url', 'bio']
        read_only_fields = ['id', 'account', 'email', 'avatar_url']

    def get_avatar_url(self, obj):
        return obj.get_avatar_url()

    def validate_username(self, value):
        """验证昵称是否可用"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("昵称不能为空")
        if len(value) < 2:
            raise serializers.ValidationError("昵称至少2个字符")
        # ✅ 检查是否已存在（排除当前用户）
        if User.objects.filter(username=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("该昵称已被使用")
        return value.strip()