"""
Accounts app URL configuration.
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.StandardLoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('azure/login/', views.AzureLoginView.as_view(), name='azure-login'),
    path('azure/callback/', views.AzureCallbackView.as_view(), name='azure-callback'),
    path('profile/', views.profile_view, name='profile'),
]
