from django.urls import path
from .views import (
    ContentPageDetailView, 
    BranchListView, 
    PromotionListView, 
    VacancyListView,
    NotificationListView,
    UserNotificationListView,
    menu_items,
    mark_user_notifications_read
)

urlpatterns = [
    path('menu-items/', menu_items, name='menu-items'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('user-notifications/', UserNotificationListView.as_view(), name='user-notification-list'),
    path('user-notifications/read/', mark_user_notifications_read, name='user-notification-mark-read'),
    path('pages/<str:title>/', ContentPageDetailView.as_view(), name='content-page-detail'),
    path('branches/', BranchListView.as_view(), name='branch-list'),
    path('promotions/', PromotionListView.as_view(), name='promotion-list'),
    path('vacancies/', VacancyListView.as_view(), name='vacancy-list'),
]