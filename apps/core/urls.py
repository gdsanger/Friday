"""
URL configuration for core app (clients).
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('clients/', views.ClientListView.as_view(), name='client-list'),
    path('clients/create/', views.ClientCreateView.as_view(), name='client-create'),
    path('clients/<slug:slug>/', views.ClientDetailView.as_view(), name='client-detail'),
    path('clients/<slug:slug>/edit/', views.ClientEditView.as_view(), name='client-edit'),
]
