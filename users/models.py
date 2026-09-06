from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string


class User(AbstractUser):
    # ✅ 昵称（唯一，可修改，注册时自动生成）
    username = models.CharField(
        max_length=150,
        verbose_name='昵称',
        unique=True  # ✅ 改为唯一
    )

    # ✅ 账号（保留 11 位数字，作登录凭证之一）
    account = models.CharField(
        max_length=11,
        unique=True,
        blank=False,
        verbose_name='账号'
    )

    # ✅ 邮箱（唯一，可登录）
    email = models.EmailField(
        unique=True,
        blank=True,
        null=True,
        verbose_name='邮箱'
    )

    # ✅ 手机号（唯一，可登录，可空）
    phone = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name='手机号'
    )

    # 设置 account 为 USERNAME_FIELD（登录字段）
    USERNAME_FIELD = 'account'

    REQUIRED_FIELDS = ['username']

    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='头像'
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        verbose_name='个人简介'
    )

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return f'{self.username} ({self.account})'

    def get_avatar_url(self):
        if self.avatar:
            url = self.avatar.url
            if 'http://127.0.0.1' in url:
                media_index = url.find('/media/')
                if media_index != -1:
                    return url[media_index:]
            if url.startswith('/media/'):
                return url
            if url.startswith('https://'):
                return url
            return f'/media/{self.avatar.name}'
        return f'https://ui-avatars.com/api/?name={self.username}&background=FB7299&color=fff&size=128'

    @staticmethod
    def generate_account():
        """生成11位唯一数字账号"""
        while True:
            first_digit = str(random.randint(1, 9))
            rest_digits = ''.join([str(random.randint(0, 9)) for _ in range(10)])
            account = first_digit + rest_digits
            if not User.objects.filter(account=account).exists():
                return account

    @staticmethod
    def generate_username():
        """生成随机唯一昵称：用户 + 时间戳 + 随机字符，如 用户16725361xs"""
        while True:
            # 格式：用户 + 时间戳后6位 + 2位随机字符
            ts = str(int(random.random() * 1000000))
            chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=2))
            username = f'用户{ts}{chars}'
            if not User.objects.filter(username=username).exists():
                return username
class EmailVerifyCode(models.Model):
    """邮箱验证码"""
    email = models.EmailField(verbose_name='邮箱')
    code = models.CharField(max_length=6, verbose_name='验证码')
    purpose = models.CharField(
        max_length=20,
        default='register',
        verbose_name='用途(register/reset)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    is_used = models.BooleanField(default=False, verbose_name='是否已使用')

    class Meta:
        db_table = 'email_verify_codes'
        verbose_name = '邮箱验证码'
        verbose_name_plural = '邮箱验证码'
        ordering = ['-created_at']

    def is_expired(self):
        """验证码10分钟有效"""
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f'{self.email} - {self.code}'

    class EmailVerifyCode(models.Model):
        """邮箱验证码"""
        email = models.EmailField(verbose_name='邮箱')
        code = models.CharField(max_length=6, verbose_name='验证码')
        purpose = models.CharField(
            max_length=20,
            default='register',
            verbose_name='用途(register/reset)'
        )
        created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
        is_used = models.BooleanField(default=False, verbose_name='是否已使用')

        class Meta:
            db_table = 'email_verify_codes'
            verbose_name = '邮箱验证码'
            verbose_name_plural = '邮箱验证码'
            ordering = ['-created_at']

        def is_expired(self):
            """验证码10分钟有效"""
            return timezone.now() > self.created_at + timedelta(minutes=10)

        def __str__(self):
            return f'{self.email} - {self.code}'