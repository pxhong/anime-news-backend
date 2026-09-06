import random
import string
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings


def generate_code(length=6):
    """生成6位数字验证码"""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


def generate_random_username():
    """生成随机唯一用户名：用户 + 时间戳后6位 + 2位随机字符"""
    from .models import User
    while True:
        ts = str(random.randint(0, 999999))
        chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=2))
        username = f'用户{ts}{chars}'
        if not User.objects.filter(username=username).exists():
            return username


def send_verify_email(to_email, code):
    """发送邮箱验证码"""
    subject = '【动漫新闻站】邮箱验证码'
    message = f'您的验证码是：{code}，10分钟内有效。如果不是您本人操作，请忽略本邮件。'
    html_message = f'''
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px;border:1px solid #eee;border-radius:8px;">
        <h2 style="color:#333;">动漫新闻站</h2>
        <p style="color:#666;">您的邮箱验证码是：</p>
        <div style="font-size:32px;font-weight:bold;color:#FB7299;letter-spacing:6px;padding:16px 0;text-align:center;">{code}</div>
        <p style="color:#999;font-size:13px;">验证码10分钟内有效，请勿泄露给他人。</p>
    </div>
    '''
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=False,
            html_message=html_message,
        )
        return True
    except Exception as e:
        print('发送邮件失败:', e)
        return False