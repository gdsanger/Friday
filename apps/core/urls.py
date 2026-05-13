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
    # Capacity Budget URLs
    path('clients/<slug:slug>/budgets/',
         views.BudgetListView.as_view(), name='budget-list'),
    path('clients/<slug:slug>/budgets/add/',
         views.BudgetAddView.as_view(), name='budget-add'),
    path('clients/<slug:slug>/budgets/<int:pk>/edit/',
         views.BudgetEditView.as_view(), name='budget-edit'),
    path('clients/<slug:slug>/budgets/<int:pk>/delete/',
         views.BudgetDeleteView.as_view(), name='budget-delete'),
]
