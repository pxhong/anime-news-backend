from django.contrib.auth.models import AbstractUser
from django.db import models
import random


class User(AbstractUser):
    # ✅ 将 username 改为可重复的昵称
    username = models.CharField(
        max_length=150,
        verbose_name='昵称',
        unique=False  # ✅ 允许重复
    )

    # ✅ 新增账号字段（作为登录凭证）
    account = models.CharField(
        max_length=11,
        unique=True,
        blank=False,
        verbose_name='账号'
    )

    # 设置 account 为 USERNAME_FIELD（登录字段）
    USERNAME_FIELD = 'account'

    # 注册时必须提供的字段（除了密码和 account）
    REQUIRED_FIELDS = ['username']  # ✅ 注册时需要提供昵称

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
        """获取头像URL，如果没有则生成默认头像"""
        if self.avatar:
            # ✅ 获取相对路径，从 URL 中提取 /media/ 开头的部分
            url = self.avatar.url
            # 如果包含 http://127.0.0.1，提取 /media/ 之后的部分
            if 'http://127.0.0.1' in url:
                # 找到 /media/ 的位置
                media_index = url.find('/media/')
                if media_index != -1:
                    return url[media_index:]  # 返回 /media/xxx 相对路径
            # 如果已经是相对路径，直接返回
            if url.startswith('/media/'):
                return url
            # 如果已经是 https 完整地址，直接返回
            if url.startswith('https://'):
                return url
            # 否则返回 /media/ + 文件名
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