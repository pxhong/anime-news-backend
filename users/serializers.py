from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, EmailVerifyCode
from .utils import generate_random_username


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
        # 正常注册流程：自动生成账号
        account = User.generate_account()
        user = User.objects.create_user(
            account=account,
            username=validated_data.get('username') or generate_random_username(),
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user


class SendCodeSerializer(serializers.Serializer):
    """发送邮箱验证码"""
    email = serializers.EmailField()

    def validate_email(self, value):
        # 注册时邮箱不能已存在
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('该邮箱已被注册')
        return value.lower()


class RegisterSerializer(serializers.Serializer):
    """邮箱+验证码+密码 注册"""
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    password = serializers.CharField(min_length=6, write_only=True)

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('该邮箱已被注册')
        return value

    def validate(self, data):
        # 校验验证码
        email = data['email']
        code = data['code']
        code_obj = EmailVerifyCode.objects.filter(
            email=email, code=code, purpose='register', is_used=False
        ).first()
        if not code_obj:
            raise serializers.ValidationError('验证码错误或已过期')
        if code_obj.is_expired():
            raise serializers.ValidationError('验证码已过期，请重新获取')
        # 标记验证码已使用
        code_obj.is_used = True
        code_obj.save()
        return data


class LoginSerializer(serializers.Serializer):
    """登录：支持 account / email / phone + 密码"""
    account = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        account = data['account'].strip()
        password = data['password']

        # 判断输入类型：纯数字11位=account，含@=email，否则尝试 phone
        user = None
        if '@' in account:
            user = User.objects.filter(email__iexact=account).first()
        else:
            # 先按 account 查
            user = User.objects.filter(account=account).first()
            if not user:
                # 再按 phone 查
                user = User.objects.filter(phone=account).first()

        if not user:
            raise serializers.ValidationError('账号/邮箱/手机号不存在')

        if not user.check_password(password):
            raise serializers.ValidationError('密码错误')

        if not user.is_active:
            raise serializers.ValidationError('账号已禁用')

        return {'user': user}


class UserProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'account', 'username', 'email', 'phone', 'avatar', 'avatar_url', 'bio']
        read_only_fields = ['id', 'account', 'email', 'avatar_url']

    def get_avatar_url(self, obj):
        return obj.get_avatar_url()

    def validate_username(self, value):
        """验证昵称是否可用（唯一）"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("昵称不能为空")
        if len(value) < 2:
            raise serializers.ValidationError("昵称至少2个字符")
        # 检查是否已存在（排除当前用户）
        if User.objects.filter(username=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("该昵称已被使用")
        return value.strip()

    def validate_phone(self, value):
        """手机号唯一校验"""
        if value:
            if User.objects.filter(phone=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("该手机号已被绑定")
        return value