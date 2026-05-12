"""
URL patterns for teams app.
"""
from django.urls import path
from . import views

app_name = 'teams'
urlpatterns = [
    path('', views.TeamListView.as_view(), name='team-list'),
    path('create/', views.TeamCreateView.as_view(), name='team-create'),
    path('users/', views.TeamUserListView.as_view(), name='team-user-list'),
    path('users/<int:user_pk>/assign/', views.TeamUserAssignView.as_view(), name='team-user-assign'),
    path('users/<int:user_pk>/remove/<slug:slug>/', views.TeamUserRemoveView.as_view(), name='team-user-remove'),
    path('<slug:slug>/', views.TeamDetailView.as_view(), name='team-detail'),
    path('<slug:slug>/edit/', views.TeamEditView.as_view(), name='team-edit'),
    path('<slug:slug>/members/add/', views.TeamMemberAddView.as_view(), name='team-member-add'),
    path('<slug:slug>/members/<int:user_id>/remove/', views.TeamMemberRemoveView.as_view(), name='team-member-remove'),
    path('<slug:slug>/members/<int:user_id>/role/', views.TeamMemberRoleView.as_view(), name='team-member-role'),
]
