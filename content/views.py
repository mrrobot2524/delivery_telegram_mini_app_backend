from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import ContentPage, Branch, Promotion, Vacancy, Notification
from .serializers import (
    ContentPageSerializer, 
    BranchSerializer, 
    PromotionSerializer, 
    VacancySerializer,
    NotificationSerializer
)


class NotificationListView(ListAPIView):
    """Получение списка активных уведомлений"""
    queryset = Notification.objects.filter(is_active=True)
    serializer_class = NotificationSerializer


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