from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "is_for_app", "is_for_qr")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("is_active", "is_for_app", "is_for_qr")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_active", "is_for_app", "is_for_qr")
    list_filter = ("category", "is_active", "is_for_app", "is_for_qr")
    search_fields = ("name", "category__name")
