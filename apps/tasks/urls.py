from django.urls import path
from . import views

app_name = 'tasks'
urlpatterns = [
    path('create/',                          views.TaskCreateView.as_view(),         name='task-create'),
    path('<int:pk>/detail/',                 views.TaskDetailView.as_view(),          name='task-detail'),
    path('<int:pk>/edit/',                   views.TaskEditView.as_view(),            name='task-edit'),
    path('<int:pk>/delete/',                 views.TaskDeleteView.as_view(),          name='task-delete'),
    path('<int:pk>/status/',                 views.TaskStatusView.as_view(),          name='task-status'),
    path('<int:pk>/move/',                   views.TaskStatusView.as_view(),          name='task-move'),
    path('<int:pk>/assign/',                 views.TaskAssignView.as_view(),          name='task-assign'),
    path('<int:pk>/watch/',                  views.TaskWatchView.as_view(),           name='task-watch'),
    path('<int:pk>/comment/',                views.TaskCommentView.as_view(),         name='task-comment'),
    path('<int:pk>/subtask/',                views.SubtaskCreateView.as_view(),       name='subtask-create'),
    path('<int:pk>/subtask/<int:sub_pk>/check/',
                                             views.SubtaskCheckView.as_view(),        name='subtask-check'),
    path('comment/<int:comment_pk>/delete/', views.CommentDeleteView.as_view(),       name='comment-delete'),
]
