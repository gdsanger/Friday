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

    # Task Move to Another Project (ISSUE-61)
    path('<int:pk>/move-project/form/',          views.TaskMoveProjectFormView.as_view(), name='task-move-project-form'),
    path('<int:pk>/move-project/',               views.TaskMoveProjectView.as_view(),     name='task-move-project'),

    # Dependencies
    path('<int:pk>/dependencies/add/',           views.DependencyAddView.as_view(),       name='dependency-add'),
    path('<int:pk>/dependencies/<int:dep_pk>/remove/',
                                                 views.DependencyRemoveView.as_view(),    name='dependency-remove'),

    # Labels (ISSUE-62)
    path('labels/',                              views.LabelListView.as_view(),           name='label-list'),
    path('labels/create/',                       views.LabelCreateView.as_view(),         name='label-create'),
    path('labels/<int:pk>/edit/',                views.LabelEditView.as_view(),           name='label-edit'),
    path('labels/<int:pk>/delete/',              views.LabelDeleteView.as_view(),         name='label-delete'),
    path('labels/<int:pk>/tasks/',               views.LabelTasksView.as_view(),          name='label-tasks'),
    path('<int:pk>/labels/add/',                 views.TaskLabelAddView.as_view(),        name='task-label-add'),
    path('<int:pk>/labels/<int:label_pk>/remove/',
                                                 views.TaskLabelRemoveView.as_view(),     name='task-label-remove'),

    # Checklisten-Items (ISSUE-63)
    path('<int:pk>/checklist/add/',
         views.ChecklistItemAddView.as_view(),                                            name='checklist-item-add'),
    path('<int:pk>/checklist/<int:item_pk>/toggle/',
         views.ChecklistItemToggleView.as_view(),                                         name='checklist-item-toggle'),
    path('<int:pk>/checklist/<int:item_pk>/delete/',
         views.ChecklistItemDeleteView.as_view(),                                         name='checklist-item-delete'),
    path('<int:pk>/checklist/<int:item_pk>/convert/',
         views.ChecklistItemConvertView.as_view(),                                        name='checklist-item-convert'),
    path('<int:pk>/checklist/apply-template/',
         views.ChecklistApplyTemplateView.as_view(),                                      name='checklist-apply-template'),

    # Checklisten-Vorlagen (ISSUE-63)
    path('checklists/',
         views.ChecklistTemplateListView.as_view(),                                       name='checklist-template-list'),
    path('checklists/create/',
         views.ChecklistTemplateCreateView.as_view(),                                     name='checklist-template-create'),
    path('checklists/<int:pk>/edit/',
         views.ChecklistTemplateEditView.as_view(),                                       name='checklist-template-edit'),
    path('checklists/<int:pk>/delete/',
         views.ChecklistTemplateDeleteView.as_view(),                                     name='checklist-template-delete'),

    # Task Templates
    path('templates/',                           views.TemplateListView.as_view(),        name='template-list'),
    path('templates/create/',                    views.TemplateCreateView.as_view(),      name='template-create'),
    path('templates/<slug:slug>/',               views.TemplateDetailView.as_view(),      name='template-detail'),
    path('templates/<slug:slug>/edit/',          views.TemplateEditView.as_view(),        name='template-edit'),
    path('templates/<slug:slug>/use/',           views.TemplateUseView.as_view(),         name='template-use'),
    path('templates/<slug:slug>/preview/',       views.TemplatePreviewView.as_view(),     name='template-preview'),
]
