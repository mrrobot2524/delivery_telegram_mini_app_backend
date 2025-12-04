from django.urls import path
from .views import (
    ContentPageDetailView, 
    BranchListView, 
    PromotionListView, 
    VacancyListView,
    NotificationListView,
    menu_items
)

urlpatterns = [
    path('menu-items/', menu_items, name='menu-items'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('pages/<str:title>/', ContentPageDetailView.as_view(), name='content-page-detail'),
    path('branches/', BranchListView.as_view(), name='branch-list'),
    path('promotions/', PromotionListView.as_view(), name='promotion-list'),
    path('vacancies/', VacancyListView.as_view(), name='vacancy-list'),
]