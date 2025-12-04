from django.contrib import admin
from django.utils.html import format_html
from .models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user_link", "product_link", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__first_name", "user__username", "product__name")
    raw_id_fields = ("user", "product")
    date_hierarchy = 'created_at'
    
    def user_link(self, obj):
        if obj.user:
            url = f"/admin/telegram_users/telegramuser/{obj.user.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.user)
        return "-"
    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user__first_name'
    
    def product_link(self, obj):
        if obj.product:
            url = f"/admin/menu/product/{obj.product.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.product.name)
        return "-"
    product_link.short_description = 'Товар'
    product_link.admin_order_field = 'product__name'
