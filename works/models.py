from django.db import models
from django.conf import settings

class Work(models.Model):
    class WorkType(models.TextChoices):
        ARTICLE = 'article', '文章'
        VIDEO = 'video', '视频'

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='works',
        verbose_name='作者'
    )
    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(blank=True, verbose_name='正文/简介')
    work_type = models.CharField(
        max_length=10,
        choices=WorkType.choices,
        default=WorkType.ARTICLE,
        verbose_name='作品类型'
    )
    file = models.FileField(
        upload_to='works/videos/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='视频文件'
    )
    cover = models.ImageField(
        upload_to='works/covers/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='封面图'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    views = models.PositiveIntegerField(default=0, verbose_name='浏览量')
    likes = models.PositiveIntegerField(default=0, verbose_name='点赞数')

    class Meta:
        db_table = 'works'
        ordering = ['-created_at']
        verbose_name = '作品'
        verbose_name_plural = '作品'

    def __str__(self):
        return self.title


# ✅ Like 模型必须放在 Work 模型外面，独立定义
class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name='用户'
    )
    work = models.ForeignKey(
        Work,  # 引用 Work 模型
        on_delete=models.CASCADE,
        related_name='likes_set',
        verbose_name='作品'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='点赞时间')

    class Meta:
        db_table = 'likes'
        unique_together = ['user', 'work']  # 防止重复点赞
        verbose_name = '点赞'
        verbose_name_plural = '点赞'

    def __str__(self):
        return f'{self.user.username} 点赞了 {self.work.title}'