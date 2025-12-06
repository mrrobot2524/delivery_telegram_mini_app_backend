from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Настройка заголовков админки
admin.site.site_header = "KYOTO SUSHI"
admin.site.site_title = "KYOTO SUSHI Admin"
admin.site.index_title = "Добро пожаловать в KYOTO SUSHI"

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/telegram/", include("telegram_users.urls")),
    path("api/menu/", include("menu.urls")),
    path("api/orders/", include("orders.urls")),
    path("api/addresses/", include("addresses.urls")),
    path("api/favorites/", include("favorites.urls")),
    path("api/content/", include("content.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)