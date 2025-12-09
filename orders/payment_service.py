"""
Payment service for handling online payments via Click (and other providers).
For local development, we use mock responses.
"""

import hashlib
import hmac
import logging
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


class ClickPaymentService:
    """Service for interacting with Click payment provider."""
    
    def __init__(self, request=None):
        # Get credentials from settings
        self.service_id = getattr(settings, 'CLICK_SERVICE_ID', None)
        self.merchant_id = getattr(settings, 'CLICK_MERCHANT_ID', None)
        self.secret_key = getattr(settings, 'CLICK_SECRET_KEY', None)
        self.merchant_user_id = getattr(settings, 'CLICK_MERCHANT_USER_ID', None)
        self.is_mock = getattr(settings, 'CLICK_IS_MOCK', False)
        self.api_url = getattr(settings, 'CLICK_API_URL', 'https://api.click.uz/v2/merchant')
        self.request = request
    
    def generate_sign(self, data: str) -> str:
        """Generate HMAC-SHA256 signature for Click API requests."""
        return hmac.new(
            self.merchant_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify_sign(self, data: str, sign: str) -> bool:
        """Verify signature from Click webhook."""
        expected_sign = self.generate_sign(data)
        return hmac.compare_digest(expected_sign, sign)
    
    def prepare_payment(self, order):
        """
        Prepare payment session for Click.
        Returns payment URL or mock response for local dev.
        """
        if self.is_mock:
            return self._mock_prepare_payment(order)
        
        # Для теста используем прямую ссылку на checkout
        # В продакшене лучше использовать API для генерации инвойса, но для старта это проще
        
        # Формируем URL для оплаты
        # https://my.click.uz/services/pay?service_id={service_id}&merchant_id={merchant_id}&amount={amount}&transaction_param={order_id}
        
        # Для TEST режима может быть другой URL или параметры
        # Обычно для тестов используют https://test.click.uz/services/pay...
        
        # Используем стандартный формат ссылки Click Evolution
        payment_url = (
            f"https://my.click.uz/services/pay"
            f"?service_id={self.service_id}"
            f"&merchant_id={self.merchant_id}"
            f"&amount={order.final_price}"
            f"&transaction_param={order.id}"
        )
        
        if self.merchant_user_id:
             payment_url += f"&merchant_user_id={self.merchant_user_id}"

        return {
            'status': 'success',
            'payment_url': payment_url,
            'click_trans_id': None,
            'merchant_trans_id': str(order.id),
        }
    
    def _mock_prepare_payment(self, order):
        """Generate mock payment response for local development."""
        logger.info(f"[MOCK] Preparing payment for order {order.id}, amount: {order.final_price}")
        
        # Получаем хост из request (для поддержки dev tunnel)
        base_url = 'http://localhost:8000'
        if self.request:
            # Используем X-Forwarded-Host для dev tunnel
            if 'X-Forwarded-Host' in self.request.headers:
                forwarded_host = self.request.headers.get('X-Forwarded-Host')
                forwarded_scheme = self.request.headers.get('X-Forwarded-Scheme', 'https')
                base_url = f"{forwarded_scheme}://{forwarded_host}"
            elif 'X-Original-Uri' in self.request.headers:
                # Fallback: construct from request host and scheme
                host = self.request.get_host()
                scheme = 'https' if self.request.is_secure() else 'http'
                base_url = f"{scheme}://{host}"
        
        payment_url = f'{base_url}/api/orders/payment/mock-callback/?order_id={order.id}&amount={order.final_price}'
        logger.info(f"[MOCK] Generated payment URL: {payment_url}")
        
        return {
            'status': 'success',
            'payment_url': payment_url,
            'message': '[MOCK] Use this URL to simulate payment callback',
            'merchant_trans_id': str(order.id),
        }
    
    def confirm_payment(self, click_trans_id: int, merchant_trans_id: str, amount: Decimal):
        """
        Confirm payment with Click.
        This is called after user completes payment.
        """
        if self.is_mock:
            return self._mock_confirm_payment(click_trans_id, merchant_trans_id, amount)
        
        # Real Click API confirmation would go here
        return {
            'status': 'success',
            'message': 'Payment confirmed',
        }
    
    def _mock_confirm_payment(self, click_trans_id: int, merchant_trans_id: str, amount: Decimal):
        """Mock payment confirmation."""
        logger.info(f"[MOCK] Confirming payment - Trans ID: {click_trans_id}, Merchant Trans ID: {merchant_trans_id}, Amount: {amount}")
        return {
            'status': 'success',
            'message': '[MOCK] Payment confirmed successfully',
        }



class TelegramPaymentService:
    """Service for generating Telegram Invoice Links (Payme/Click via Bot)."""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.provider_token = settings.PAYME_PROVIDER_TOKEN
        
    def create_invoice_link(self, order):
        """Generate invoice link using Telegram Bot API."""
        import requests
        import json
        
        url = f"https://api.telegram.org/bot{self.bot_token}/createInvoiceLink"
        
        # Сумма в минимальных единицах валюты. Для UZS это тийины (x100).
        amount_in_cents = int(order.final_price * 100)
        
        data = {
            "title": f"Заказ #{order.id}",
            "description": f"Оплата заказа #{order.id} в KY Sushi",
            "payload": str(order.id),
            "provider_token": self.provider_token,
            "currency": "UZS",
            "prices": json.dumps([
                {"label": "Оплата заказа", "amount": amount_in_cents}
            ]),
            # Опционально: фото
            # "photo_url": "...",
            # "need_name": True,
            # "need_phone_number": True,
        }
        
        try:
            print(f"[create_invoice_link] Token partial: {self.provider_token[:10]}...")
            print(f"[create_invoice_link] Amount cents: {amount_in_cents}")
            
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            
            if not result.get("ok"):
                print(f"[create_invoice_link] Telegram API Failed: {result}") # Вывод в консоль
                logger.error(f"Telegram createInvoiceLink failed: {result}")
                return None
                
            return result["result"] # Возвращает ссылку t.me/invoice/...
            
        except Exception as e:
            print(f"[create_invoice_link] Exception: {e}")
            logger.error(f"Error creating invoice link: {e}")
            return None


class PaymentProcessor:
    """Main processor for handling payment operations."""
    
    def __init__(self, request=None):
        self.click_service = ClickPaymentService(request=request)
        self.telegram_service = TelegramPaymentService()
    
    def create_payment_session(self, order, provider='click'):
        """Create a new payment session for an order."""
        from .models import ClickTransaction
        
        logger.info(f"[PaymentProcessor] Starting payment session for order {order.id} via {provider}")
        
        if provider == 'payme':
            # Используем Telegram Payments (Invoice)
            invoice_link = self.telegram_service.create_invoice_link(order)
            if not invoice_link:
                return {
                    'success': False,
                    'error': 'Failed to generate Payme link'
                }
            
            return {
                'success': True,
                'payment_url': invoice_link, # Это ссылка t.me/invoice/... которую фронт откроет через web_app_open_invoice
                'type': 'telegram_invoice'
            }

        # Default to Click
        # Prepare payment with Click
        payment_data = self.click_service.prepare_payment(order)
        
        if payment_data.get('status') != 'success':
            return {
                'success': False,
                'error': payment_data.get('message', 'Failed to prepare payment'),
            }
        
        # Create transaction record for Click
        ClickTransaction.objects.create(
            order=order,
            merchant_trans_id=str(order.id),
            amount=order.final_price,
            status='pending',
        )
        
        return {
            'success': True,
            'payment_url': payment_data.get('payment_url'),
            'merchant_trans_id': str(order.id),
            'type': 'redirect'
        }
    
    # ... (handle_payment_callback остается для Click)
