from django.urls import path
from .views import (
    RegisterView, LoginView, UserProfileView, AvatarUploadView,
    DeleteAccountView, CheckUsernameView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('avatar/', AvatarUploadView.as_view(), name='avatar-upload'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
    path('check-username/', CheckUsernameView.as_view(), name='check-username'),
]
