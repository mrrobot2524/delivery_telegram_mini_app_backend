from django.urls import path
from .views import UserAddressListCreateView, UserAddressDetailView, SetDefaultAddressView

urlpatterns = [
    path("", UserAddressListCreateView.as_view(), name="address-list-create"),
    path("<int:pk>/", UserAddressDetailView.as_view(), name="address-detail"),
    path("<int:pk>/set-default/", SetDefaultAddressView.as_view(), name="address-set-default"),
]
