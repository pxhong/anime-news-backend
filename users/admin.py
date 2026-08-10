from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('account', 'username', 'email', 'is_active', 'date_joined')
    search_fields = ('account', 'username', 'email')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('account', 'username', 'password')}),
        ('个人信息', {'fields': ('email', 'avatar', 'bio')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('account', 'username', 'email', 'password1', 'password2'),
        }),
    )