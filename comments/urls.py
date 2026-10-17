from django.urls import path

from . import views

urlpatterns = [
    path('works/<int:work_id>/comments/', views.WorkCommentListCreateView.as_view()),
    path('comments/<int:pk>/replies/', views.CommentRepliesView.as_view()),
    path('comments/<int:pk>/', views.CommentDeleteView.as_view()),
]