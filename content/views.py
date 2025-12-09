from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import ContentPage, Branch, Promotion, Vacancy, Notification, UserNotification
from .serializers import (
    ContentPageSerializer, 
    BranchSerializer, 
    PromotionSerializer, 
    VacancySerializer,
    NotificationSerializer,
    UserNotificationSerializer
)


class NotificationListView(ListAPIView):
    """Получение списка активных уведомлений"""
    queryset = Notification.objects.filter(is_active=True)
    serializer_class = NotificationSerializer


class UserNotificationListView(ListAPIView):
    """API для получения персональных уведомлений пользователя"""
    serializer_class = UserNotificationSerializer
    
    def get_queryset(self):
        # Получаем telegram_id из query params или body (для POST запросов, если нужно)
        # Обычно GET запросы используют query params
        telegram_id = self.request.query_params.get('telegram_id')
        
        # Если используем initData, можно попробовать достать оттуда, но проще передать telegram_id явно
        if not telegram_id:
            # Попробуем достать из body для совместимости, если вдруг POST запрос (хотя это ListAPIView -> GET)
            # Или может быть initData парсится где-то в middleware и user auth
            pass

        if not telegram_id:
            return UserNotification.objects.none()
        
        return UserNotification.objects.filter(
            telegram_id=telegram_id
        ).select_related('order')[:50]  # Последние 50 уведомлений


@api_view(['POST'])
def mark_user_notifications_read(request):
    """Пометить все уведомления пользователя как прочитанные"""
    telegram_id = request.data.get('telegram_id')
    if not telegram_id:
        return Response({'error': 'telegram_id is required'}, status=400)
        
    UserNotification.objects.filter(
        telegram_id=telegram_id,
        is_read=False
    ).update(is_read=True)
    
    return Response({'status': 'ok'})


class ContentPageDetailView(RetrieveAPIView):
    """Получение контентной страницы по slug"""
    queryset = ContentPage.objects.filter(is_active=True)
    serializer_class = ContentPageSerializer
    lookup_field = 'title'


class BranchListView(ListAPIView):
    """Получение списка филиалов"""
    queryset = Branch.objects.filter(is_active=True)
    serializer_class = BranchSerializer


class PromotionListView(ListAPIView):
    """Получение списка активных акций"""
    queryset = Promotion.objects.filter(is_active=True)
    serializer_class = PromotionSerializer


class VacancyListView(ListAPIView):
    """Получение списка активных вакансий"""
    queryset = Vacancy.objects.filter(is_active=True)
    serializer_class = VacancySerializer


@api_view(['GET'])
def menu_items(request):
    """Получение всех пунктов меню с их данными"""
    # Получаем контентные страницы
    content_pages = ContentPage.objects.filter(is_active=True)
    content_data = {}
    for page in content_pages:
        content_data[page.title] = {
            'id': page.id,
            'title': dict(ContentPage.TITLE_CHOICES)[page.title],
            'has_content': bool(page.content.strip())
        }
    
    # Получаем количество филиалов
    branches_count = Branch.objects.filter(is_active=True).count()
    
    # Получаем количество акций
    promotions_count = Promotion.objects.filter(is_active=True).count()
    
    # Получаем количество вакансий
    vacancies_count = Vacancy.objects.filter(is_active=True).count()
    
    data = {
        'content_pages': content_data,
        'branches_count': branches_count,
        'promotions_count': promotions_count,
        'vacancies_count': vacancies_count
    }
    
    return Response(data)