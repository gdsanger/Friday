from django.urls import path
from . import views

app_name = 'mail'
urlpatterns = [
    path('webhook/', views.graph_webhook, name='graph-webhook'),
]
