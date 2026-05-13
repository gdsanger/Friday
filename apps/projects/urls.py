from django.urls import path
from . import views

app_name = 'projects'
urlpatterns = [
    path('',                              views.ProjectListView.as_view(),         name='project-list'),
    path('create/',                       views.ProjectCreateView.as_view(),        name='project-create'),
    path('calendar/',                     views.CalendarView.as_view(),             name='calendar'),
    path('calendar/data/',                views.CalendarDataView.as_view(),         name='calendar-data'),
    path('calendar/update/',              views.CalendarUpdateView.as_view(),       name='calendar-update'),
    path('<int:pk>/',                     views.ProjectDetailView.as_view(),        name='project-detail'),
    path('<int:pk>/edit/',                views.ProjectEditView.as_view(),          name='project-edit'),
    path('<int:pk>/archive/',             views.ProjectArchiveView.as_view(),       name='project-archive'),
    path('<int:pk>/members/add-user/',    views.ProjectAddUserView.as_view(),       name='project-add-user'),
    path('<int:pk>/members/add-team/',    views.ProjectAddTeamView.as_view(),       name='project-add-team'),
    path('<int:pk>/members/remove-user/<int:user_id>/',
                                          views.ProjectRemoveUserView.as_view(),    name='project-remove-user'),
    path('<int:pk>/members/remove-team/<int:team_id>/',
                                          views.ProjectRemoveTeamView.as_view(),    name='project-remove-team'),
]
