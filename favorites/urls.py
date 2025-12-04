from django.urls import path
from .views import ToggleFavoriteView, FavoritesListView

urlpatterns = [
    path("toggle/", ToggleFavoriteView.as_view()),
    path("", FavoritesListView.as_view()),
]