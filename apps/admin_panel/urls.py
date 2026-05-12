from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.AdminDashboardView.as_view(), name='admin-dashboard'),

    # User management
    path('users/', views.AdminUserListView.as_view(), name='admin-users'),
    path('users/<int:pk>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('users/invite/', views.AdminUserInviteView.as_view(), name='admin-user-invite'),
    path('users/<int:pk>/toggle-active/', views.AdminUserToggleActiveView.as_view(), name='admin-user-toggle'),

    # Team management
    path('teams/', views.AdminTeamListView.as_view(), name='admin-teams'),
    path('teams/create/', views.AdminTeamCreateView.as_view(), name='admin-team-create'),
    path('teams/<slug:slug>/edit/', views.AdminTeamEditView.as_view(), name='admin-team-edit'),

    # AI monitoring and settings
    path('ai/', views.AdminAIMonitorView.as_view(), name='admin-ai'),
    path('ai/settings/', views.AdminAISettingsView.as_view(), name='admin-ai-settings'),

    # Mail and system status
    path('mail/', views.AdminMailStatusView.as_view(), name='admin-mail'),

    # Organisation settings
    path('settings/', views.AdminOrgSettingsView.as_view(), name='admin-settings'),

    # Audit log
    path('audit/', views.AdminAuditLogView.as_view(), name='admin-audit'),
]
