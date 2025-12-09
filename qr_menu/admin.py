from django.contrib import admin
from .models import QROnlyCategory, QROnlyProduct, QRTable

@admin.register(QROnlyCategory)
class QROnlyCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name",)

@admin.register(QROnlyProduct)
class QROnlyProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "category__name")

@admin.register(QRTable)
class QRTableAdmin(admin.ModelAdmin):
    list_display = ("number", "qr_code_preview", "created_at")
    readonly_fields = ("uuid", "qr_code_preview", "created_at")
    fields = ("number", "categories", "uuid", "qr_code", "qr_code_preview")
    filter_horizontal = ("categories",)

    def qr_code_preview(self, obj):
        from django.utils.html import format_html
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="150" height="150" />',
                obj.qr_code.url
            )
        return "—"
    qr_code_preview.short_description = "QR Code"
