from django.urls import path
from . import views

app_name = 'tasks'
urlpatterns = [
    path('create/',                          views.TaskCreateView.as_view(),         name='task-create'),
    path('<int:pk>/detail/',                 views.TaskDetailView.as_view(),          name='task-detail'),
    path('<int:pk>/',                        views.TaskDetailFullView.as_view(),      name='task-detail-full'),
    path('<int:pk>/edit/',                   views.TaskEditView.as_view(),            name='task-edit'),
    path('<int:pk>/edit-field/',             views.TaskEditFieldView.as_view(),       name='task-edit-field'),
    path('<int:pk>/delete/',                 views.TaskDeleteView.as_view(),          name='task-delete'),
    path('<int:pk>/clone/',                  views.TaskCloneView.as_view(),           name='task-clone'),
    path('<int:pk>/status/',                 views.TaskStatusView.as_view(),          name='task-status'),
    path('<int:pk>/move/',                   views.TaskStatusView.as_view(),          name='task-move'),
    path('<int:pk>/assign/',                 views.TaskAssignView.as_view(),          name='task-assign'),
    path('<int:pk>/watch/',                  views.TaskWatchView.as_view(),           name='task-watch'),
    path('<int:pk>/watchers/add/',           views.WatcherAddView.as_view(),          name='watcher-add'),
    path('<int:pk>/watchers/remove/<int:user_pk>/', views.WatcherRemoveView.as_view(), name='watcher-remove'),
    path('<int:pk>/watchers/remove-team/<int:team_pk>/', views.WatcherRemoveTeamView.as_view(), name='watcher-remove-team'),
    path('<int:pk>/comment/',                views.TaskCommentView.as_view(),         name='task-comment'),
    path('<int:pk>/subtask/',                views.SubtaskCreateView.as_view(),       name='subtask-create'),
    path('<int:pk>/subtask/<int:sub_pk>/check/',
                                             views.SubtaskCheckView.as_view(),        name='subtask-check'),
    path('comment/<int:comment_pk>/delete/', views.CommentDeleteView.as_view(),       name='comment-delete'),

    # Attachments
    path('<int:pk>/attachments/upload/',         views.AttachmentUploadView.as_view(),    name='attachment-upload'),
    path('attachments/<int:att_pk>/delete/',     views.AttachmentDeleteView.as_view(),    name='attachment-delete'),
    path('attachments/<int:att_pk>/download/',   views.AttachmentDownloadView.as_view(),  name='attachment-download'),

    # Time Entries
    path('<int:pk>/time/log/',                   views.TimeEntryLogView.as_view(),        name='time-log'),
    path('time/<int:entry_pk>/delete/',          views.TimeEntryDeleteView.as_view(),     name='time-delete'),

    # Task Close (ISSUE-53)
    path('<int:pk>/close/',                      views.TaskCloseFormView.as_view(),       name='task-close-form'),
    path('<int:pk>/close/submit/',               views.TaskCloseView.as_view(),           name='task-close'),

    # Task Assign Form (ISSUE-53)
    path('<int:pk>/assign-form/',                views.TaskAssignFormView.as_view(),      name='task-assign-form'),

    # Dependencies
    path('<int:pk>/dependencies/add/',           views.DependencyAddView.as_view(),       name='dependency-add'),
    path('<int:pk>/dependencies/<int:dep_pk>/remove/',
                                                 views.DependencyRemoveView.as_view(),    name='dependency-remove'),

    # Task Templates
    path('templates/',                           views.TemplateListView.as_view(),        name='template-list'),
    path('templates/create/',                    views.TemplateCreateView.as_view(),      name='template-create'),
    path('templates/<slug:slug>/',               views.TemplateDetailView.as_view(),      name='template-detail'),
    path('templates/<slug:slug>/edit/',          views.TemplateEditView.as_view(),        name='template-edit'),
    path('templates/<slug:slug>/use/',           views.TemplateUseView.as_view(),         name='template-use'),
    path('templates/<slug:slug>/preview/',       views.TemplatePreviewView.as_view(),     name='template-preview'),
]
