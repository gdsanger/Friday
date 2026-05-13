"""Portal URL configuration."""
from django.urls import path
from apps.portal import views

urlpatterns = [
    path('', views.PortalHomeView.as_view(), name='portal-home'),
    path('tickets/', views.PortalTicketListView.as_view(), name='portal-tickets'),
    path('tickets/new/', views.PortalTemplateSelectView.as_view(), name='portal-template-select'),
    path('tickets/new/<slug:template_slug>/', views.PortalTicketCreateView.as_view(), name='portal-ticket-create'),
    path('tickets/<int:pk>/', views.PortalTicketDetailView.as_view(), name='portal-ticket-detail'),
    path('tickets/<int:pk>/comment/', views.PortalTicketCommentView.as_view(), name='portal-ticket-comment'),
    path('tickets/<int:pk>/attachment/', views.PortalTicketAttachmentView.as_view(), name='portal-ticket-attachment'),
]
