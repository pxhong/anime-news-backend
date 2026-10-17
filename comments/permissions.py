from rest_framework import permissions


class IsCommentOwnerOrWorkAuthorOrStaff(permissions.BasePermission):
    message = '只能删除自己的评论'

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or obj.user_id == user.id:
            return True
        return obj.work.author_id == user.id