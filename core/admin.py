from django.contrib import admin

# Можно добавить здесь любые глобальные настройки админки, если нужно
# Пока оставляем файл минимальным
from django.urls import path
from django.shortcuts import render
from orders.models import Order
from telegram_users.models import TelegramUser
from menu.models import Product


class CustomAdminSite(admin.AdminSite):
    site_header = 'Администрирование Sushi Service'
    site_title = 'Панель администратора'
    index_title = 'Добро пожаловать в панель управления'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # Add custom URLs here if needed
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        # Add custom context data for the dashboard
        extra_context = extra_context or {}
        
        # Get counts for dashboard statistics
        extra_context['orders_count'] = Order.objects.count()
        extra_context['users_count'] = TelegramUser.objects.count()
        extra_context['products_count'] = Product.objects.count()
        
        return super().index(request, extra_context)


# Create an instance of our custom admin site
custom_admin_site = CustomAdminSite(name='custom_admin')

# Register your models here with the custom admin site if needed
# For now, we'll continue using the default admin site registration

# Also apply friendly defaults to the global admin site so existing
# `admin.site.register(...)` calls keep working and the UI shows our titles.
from django.contrib import admin as _admin

_admin.site.site_header = 'Администрирование Sushi Service'
_admin.site.site_title = 'Панель администратора'
_admin.site.index_title = 'Добро пожаловать в панель управления'