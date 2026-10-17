from django.conf import settings
from django.db import models


class Comment(models.Model):
    work = models.ForeignKey('works.Work', on_delete=models.CASCADE,
                             related_name='comments', verbose_name='作品')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='comments', verbose_name='评论人')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                               related_name='replies', verbose_name='所属顶层评论')
    reply_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='reply_received',
                                 verbose_name='被回复人')
    content = models.CharField(max_length=500, verbose_name='内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '评论'
        verbose_name_plural = '评论'
        indexes = [models.Index(fields=['work', 'parent', '-created_at'])]

    def __str__(self):
        return f'{self.user_id}: {self.content[:20]}'