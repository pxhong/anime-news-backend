from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
from .models import User, EmailVerifyCode
from .serializers import (
    UserSerializer, LoginSerializer, UserProfileSerializer,
    SendCodeSerializer, RegisterSerializer
)
from .utils import generate_code, send_verify_email, generate_random_username
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny

User = get_user_model()


class SendCodeView(APIView):
    """发送邮箱验证码（注册用）"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        # 防刷：60秒内不能重复发送
        recent = EmailVerifyCode.objects.filter(
            email=email, purpose='register',
            created_at__gte=timezone.now() - timedelta(seconds=60)
        ).exists()
        if recent:
            return Response(
                {'detail': '发送太频繁，请60秒后再试'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        code = generate_code()
        EmailVerifyCode.objects.create(email=email, code=code, purpose='register')
        ok = send_verify_email(email, code)
        if not ok:
            return Response(
                {'detail': '邮件发送失败，请稍后重试'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response({'detail': '验证码已发送到您的邮箱'})


class RegisterView(APIView):
    """邮箱+验证码+密码注册，成功后自动登录"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # 自动生成账号和随机用户名
        account = User.generate_account()
        username = generate_random_username()

        user = User.objects.create_user(
            account=account,
            username=username,
            email=email,
            password=password
        )

        # 自动登录：生成 token
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'message': '注册成功'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserProfileSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AvatarUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if 'avatar' not in request.FILES:
            return Response({'error': '没有上传文件'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['avatar']

        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if file.content_type not in allowed_types:
            return Response({'error': '只支持 JPG, PNG, GIF, WEBP 格式'}, status=status.HTTP_400_BAD_REQUEST)

        if file.size > 5 * 1024 * 1024:
            return Response({'error': '文件大小不能超过5MB'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.avatar = file
        user.save()

        serializer = UserProfileSerializer(user)
        return Response(serializer.data)


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        if user.is_superuser:
            return Response(
                {'error': '超级管理员不能通过此方式注销账号'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.delete()
        return Response({'message': '账号已成功注销'}, status=status.HTTP_200_OK)


class CheckUsernameView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        username = request.GET.get('username', '')
        if not username:
            return Response({'exists': False})
        exists = User.objects.filter(username=username).exists()
        return Response({'exists': exists})