"""
Dashboard URL configuration.
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Widget endpoints — each returns a partial
    path('widgets/my-tasks/', views.WidgetMyTasksView.as_view(), name='widget-my-tasks'),
    path('widgets/overdue/', views.WidgetOverdueView.as_view(), name='widget-overdue'),
    path('widgets/team-load/', views.WidgetTeamLoadView.as_view(), name='widget-team-load'),
    path('widgets/due-soon/', views.WidgetDueSoonView.as_view(), name='widget-due-soon'),
    path('widgets/project-status/', views.WidgetProjectStatusView.as_view(), name='widget-project-status'),
    path('widgets/activity/', views.WidgetActivityView.as_view(), name='widget-activity'),
    path('widgets/due-week/', views.WidgetDueWeekView.as_view(), name='widget-due-week'),
    path('widgets/my-projects/', views.WidgetMyProjectsView.as_view(), name='widget-my-projects'),
]
