from django.contrib import admin
from .models import UserAddress


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "title",
        "address_text",
        "is_default",
        "created_at",
    )
    list_filter = ("is_default", "created_at")
    search_fields = ("user__username", "user__first_name", "title", "address_text")
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        ("Основная информация", {
            "fields": ("user", "title", "is_default")
        }),
        ("Адрес", {
            "fields": ("address_text", "latitude", "longitude")
        }),
        ("Детали", {
            "fields": ("entrance", "floor", "apartment", "intercom", "comment")
        }),
        ("Системная информация", {
            "fields": ("created_at", "updated_at")
        }),
    )
