# Quick Start: Online Payment Integration

## What's Implemented

✅ **Payment Model & Database** - `ClickTransaction` model to track payments
✅ **API Endpoints** - 3 new endpoints for payment flow
✅ **Mock Payment Service** - Local testing without real transactions
✅ **Payment Settings** - Environment-based configuration
✅ **Test Interface** - HTML file for testing (`payment_test.html`)

## Quick Setup

### 1. Database Migrations
```bash
cd /Users/mac/Documents/NextJs_projects/ky_sushi
python manage.py migrate
```

### 2. Run Server
```bash
python manage.py runserver
```

### 3. Test Payment Flow

**Option A: Use Test Interface**
```
Open in browser: http://localhost:8000/payment_test.html
```

**Option B: Manual API Testing (curl)**

1. Get/Create cart:
```bash
curl -X GET http://localhost:8000/api/orders/cart/ \
  -H "X-Telegram-Init-Data: dev_mode"
```

2. Add product to cart:
```bash
curl -X POST http://localhost:8000/api/orders/cart/ \
  -H "X-Telegram-Init-Data: dev_mode" \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 2}'
```

3. Update delivery info:
```bash
curl -X PATCH http://localhost:8000/api/orders/cart/ \
  -H "X-Telegram-Init-Data: dev_mode" \
  -H "Content-Type: application/json" \
  -d '{"delivery_type": "delivery", "address_text": "123 Main St"}'
```

4. Initiate payment:
```bash
curl -X POST http://localhost:8000/api/orders/initiate-payment/ \
  -H "X-Telegram-Init-Data: dev_mode" \
  -H "Content-Type: application/json" \
  -d '{"order_id": 1}'
```

5. Simulate payment callback:
```bash
curl -X GET "http://localhost:8000/api/orders/payment-callback/?order_id=1&amount=150000" \
  -H "X-Telegram-Init-Data: dev_mode"
```

6. Check payment status:
```bash
curl -X GET http://localhost:8000/api/orders/payment-status/1/ \
  -H "X-Telegram-Init-Data: dev_mode"
```

## Frontend Integration (React)

Example for `ky_sushi_front`:

```javascript
// utils/paymentService.js
const API_URL = 'http://localhost:8000';

export const initiatePayment = async (orderId, initData) => {
  const response = await fetch(`${API_URL}/api/orders/initiate-payment/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData,
    },
    body: JSON.stringify({ order_id: orderId }),
  });
  return response.json();
};

export const checkPaymentStatus = async (orderId, initData) => {
  const response = await fetch(
    `${API_URL}/api/orders/payment-status/${orderId}/`,
    {
      headers: {
        'X-Telegram-Init-Data': initData,
      },
    }
  );
  return response.json();
};

// Usage in React component
import { initiatePayment, checkPaymentStatus } from './utils/paymentService';

export function CheckoutPage() {
  const initData = window.Telegram?.WebApp?.initData || 'dev_mode';
  
  const handlePayment = async () => {
    const cartOrder = await getCartOrder();
    const result = await initiatePayment(cartOrder.id, initData);
    
    if (result.success) {
      // For mock: use result.payment_url
      // For real Click: would redirect to Click payment page
      window.open(result.payment_url, '_blank');
      
      // Poll payment status
      const pollInterval = setInterval(async () => {
        const status = await checkPaymentStatus(cartOrder.id, initData);
        if (status.payment_status === 'paid') {
          clearInterval(pollInterval);
          // Redirect to order details
          navigate(`/orders/${cartOrder.id}`);
        }
      }, 2000);
    }
  };
  
  return (
    <button onClick={handlePayment}>
      Pay Online via Click
    </button>
  );
}
```

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/orders/initiate-payment/` | POST | Start payment session |
| `/api/orders/payment-callback/` | POST/GET | Handle payment result |
| `/api/orders/payment-status/<id>/` | GET | Check payment status |

## Environment Variables

Default (local development):
```
CLICK_IS_MOCK=True
CLICK_MERCHANT_ID=12345
CLICK_MERCHANT_KEY=mock_key_for_local_dev
```

## Files Modified/Created

- ✅ `orders/models.py` - Added "online" payment method
- ✅ `orders/views.py` - Added 3 API endpoints
- ✅ `orders/urls.py` - Added URL routes
- ✅ `orders/payment_service.py` - Payment logic (NEW)
- ✅ `core/settings.py` - Payment settings
- ✅ `payment_test.html` - Test interface (NEW)
- ✅ `PAYMENT_INTEGRATION.md` - Full documentation (NEW)

## Next Steps

1. Test locally with `payment_test.html`
2. Integrate with React frontend
3. For production: Get real Click API credentials
4. Update settings with production credentials
5. Deploy and test with real transactions

## Troubleshooting

**"Invalid Telegram authentication"**
- Use `X-Telegram-Init-Data: dev_mode` for local testing
- For real app, pass actual Telegram init data

**"Cart is empty"**
- Add products to cart first

**"Delivery information is incomplete"**
- Set delivery_type and address_text

**Payment status not updating**
- Check API logs for errors
- Verify order exists in database

## Documentation

- Full API docs: `PAYMENT_INTEGRATION.md`
- Payment service: `orders/payment_service.py`
- API views: `orders/views.py` (InitiatePaymentView, PaymentCallbackView, CheckPaymentStatusView)

Questions? Check the docs or examine the code comments in `payment_service.py` and `views.py`.
