from django.urls import path
from .views import TaskAIActionView

app_name = 'ai'
urlpatterns = [
    path('tasks/<int:task_id>/ai/<str:action>/', TaskAIActionView.as_view(), name='task-ai-action'),
]
