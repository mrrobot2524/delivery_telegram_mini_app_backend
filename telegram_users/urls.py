from django.urls import path
from .views import MiniAppAuthView, UserProfileView

urlpatterns = [
    path("auth/mini-app/", MiniAppAuthView.as_view()),
    path("profile/", UserProfileView.as_view()),
]
