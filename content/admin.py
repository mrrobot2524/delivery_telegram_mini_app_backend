from django.contrib import admin
from .models import ContentPage, Branch, Promotion, Vacancy, Notification, UserNotification


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'telegram_id', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'telegram_id']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'is_active', 'created_at')
    list_filter = ('notification_type', 'is_active', 'created_at')
    search_fields = ('title', 'message')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)
    ordering = ['-created_at']


@admin.register(ContentPage)
class ContentPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('title',)
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'address', 'phone')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'is_active', 'created_at')
    list_filter = ('is_active', 'start_date', 'end_date', 'created_at')
    search_fields = ('title', 'description')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'start_date'


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('title', 'salary', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description', 'requirements')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)