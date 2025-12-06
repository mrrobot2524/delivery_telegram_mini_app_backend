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


class PaymentProcessor:
    """Main processor for handling payment operations."""
    
    def __init__(self, request=None):
        self.click_service = ClickPaymentService(request=request)
    
    def create_payment_session(self, order):
        """Create a new payment session for an order."""
        from .models import ClickTransaction
        
        logger.info(f"[PaymentProcessor] Starting payment session for order {order.id}")
        logger.info(f"[PaymentProcessor] Order status: {order.status}")
        logger.info(f"[PaymentProcessor] Order total_price: {order.total_price}")
        logger.info(f"[PaymentProcessor] Order final_price: {order.final_price}")
        logger.info(f"[PaymentProcessor] Order items count: {order.items.count()}")
        
        # Prepare payment with Click
        logger.info(f"[PaymentProcessor] Preparing payment with Click service...")
        payment_data = self.click_service.prepare_payment(order)
        logger.info(f"[PaymentProcessor] Payment data received: {payment_data}")
        
        if payment_data.get('status') != 'success':
            logger.error(f"[PaymentProcessor] Payment preparation failed: {payment_data}")
            return {
                'success': False,
                'error': payment_data.get('message', 'Failed to prepare payment'),
            }
        
        # Create transaction record
        logger.info(f"[PaymentProcessor] Creating ClickTransaction for order {order.id}")
        transaction = ClickTransaction.objects.create(
            order=order,
            # click_trans_id будет установлена в callback, оставляем null
            merchant_trans_id=str(order.id),
            amount=order.final_price,
            status='pending',
        )
        logger.info(f"[PaymentProcessor] Transaction created: {transaction.id}")
        
        response = {
            'success': True,
            'payment_url': payment_data.get('payment_url'),
            'transaction_id': transaction.id,
            'merchant_trans_id': str(order.id),
        }
        logger.info(f"[PaymentProcessor] Returning payment response: {response}")
        return response
    
    def handle_payment_callback(self, click_trans_id: int, merchant_trans_id: str, amount: Decimal, status: str):
        """
        Handle payment callback from Click.
        Called after user completes payment.
        """
        from .models import ClickTransaction, Order
        
        try:
            order = Order.objects.get(id=int(merchant_trans_id))
        except Order.DoesNotExist:
            logger.error(f"Order not found: {merchant_trans_id}")
            return {
                'success': False,
                'error': 'Order not found',
            }
        
        # Check if transaction already exists
        transaction = ClickTransaction.objects.filter(
            click_trans_id=click_trans_id
        ).first()
        
        if not transaction:
            # Create new transaction
            transaction = ClickTransaction.objects.create(
                order=order,
                click_trans_id=click_trans_id,
                merchant_trans_id=str(order.id),
                amount=amount,
                status='pending',
            )
        
        # Update transaction status
        if status == 'completed':
            transaction.status = 'confirmed'
            transaction.complete_time = timezone.now()
            transaction.save()
            
            # Update order payment status
            order.payment_status = 'paid'
            order.paid_at = timezone.now()
            order.save()
            
            logger.info(f"Payment confirmed for order {order.id}")
            
            # Запускаем фоновую задачу Celery для уведомлений и доп. действий
            from .tasks import process_successful_payment
            process_successful_payment.delay(order.id, float(amount))
            
            return {
                'success': True,
                'message': 'Payment processed successfully',
            }
        else:
            transaction.status = 'error'
            transaction.error_note = f'Payment failed or cancelled: {status}'
            transaction.save()
            
            logger.warning(f"Payment failed for order {order.id}: {status}")
            
            return {
                'success': False,
                'error': 'Payment failed or was cancelled',
            }
