from django.contrib import admin
from django.utils.html import format_html
from .models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "username", "first_name", "phone_number", "is_admin", "avatar_thumb", "created_at")
    list_filter = ("is_admin",)
    search_fields = ("telegram_id", "username", "first_name", "phone_number")
    readonly_fields = ("avatar_thumb",)

    def avatar_thumb(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="64" height="64" style="object-fit: cover; border-radius: 50%;" />',
                obj.photo.url,
            )
        return "—"

    avatar_thumb.short_description = "Аватар"
