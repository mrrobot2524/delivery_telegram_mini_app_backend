"""
Management command to create sample promo codes
Usage: python manage.py create_sample_promos
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from orders.models import PromoCode


class Command(BaseCommand):
    help = 'Create sample promo codes for testing'

    def handle(self, *args, **options):
        promos = [
            {
                'code': 'WELCOME10',
                'discount_type': 'percentage',
                'discount_value': 10,
                'min_order_amount': 500,
                'description': 'Скидка 10% для новых пользователей'
            },
            {
                'code': 'SUMMER2024',
                'discount_type': 'percentage',
                'discount_value': 15,
                'min_order_amount': 1000,
                'description': 'Летняя распродажа - 15%'
            },
            {
                'code': 'FIXED500',
                'discount_type': 'fixed',
                'discount_value': 500,
                'min_order_amount': 2000,
                'description': 'Скидка 500 сум при заказе от 2000'
            },
            {
                'code': 'VIP20',
                'discount_type': 'percentage',
                'discount_value': 20,
                'min_order_amount': 3000,
                'description': 'VIP скидка 20%'
            },
        ]
        
        created_count = 0
        for promo_data in promos:
            code = promo_data.pop('code')
            
            # Проверяем существует ли уже
            if PromoCode.objects.filter(code=code).exists():
                self.stdout.write(
                    self.style.WARNING(f'Promo code {code} already exists, skipping...')
                )
                continue
            
            # Создаем промокод
            promo = PromoCode.objects.create(
                code=code,
                valid_from=timezone.now(),
                valid_until=timezone.now() + timedelta(days=30),
                max_uses=1000,
                is_active=True,
                **promo_data
            )
            
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Created promo code: {code} ({promo.discount_value}{"%" if promo.discount_type == "percentage" else " сум"})')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal created: {created_count} promo codes')
        )
