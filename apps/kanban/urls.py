from django.urls import path
from . import views

app_name = 'kanban'
urlpatterns = [
    path('', views.KanbanBoardView.as_view(), name='kanban-board'),
]
