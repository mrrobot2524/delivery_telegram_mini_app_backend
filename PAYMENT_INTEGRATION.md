# Online Payment Integration (Click) - Documentation

## Overview

This integration adds online payment (Click) support to the KY SUSHI ordering system. For local development, it uses **mock mode** to simulate payments without real transactions.

## API Endpoints

### 1. Initiate Payment
**Endpoint:** `POST /api/orders/initiate-payment/`

**Purpose:** Create a payment session and get a payment URL for the user.

**Request:**
```json
{
    "order_id": 123
}
```

**Headers:**
```
X-Telegram-Init-Data: {telegram_init_data}
Content-Type: application/json
```

**Response (Success - 200):**
```json
{
    "success": true,
    "payment_url": "http://localhost:8000/api/orders/payment/mock-callback/?order_id=123&amount=150000",
    "transaction_id": 45,
    "merchant_trans_id": "123"
}
```

**Response (Error):**
```json
{
    "success": false,
    "error": "Cart is empty"
}
```

**Possible Errors:**
- `"Invalid Telegram authentication"` - Missing or invalid X-Telegram-Init-Data header
- `"order_id is required"` - order_id not provided
- `"Order not found or not in cart status"` - Order doesn't exist or is not in cart
- `"Cart is empty"` - Order has no items
- `"Delivery information is incomplete"` - Missing delivery_type or address_text

---

### 2. Payment Callback (Webhook)
**Endpoint:** `POST /api/orders/payment-callback/`

**Purpose:** Handle payment status updates from Click provider (or test callback).

**Request Body:**
```json
{
    "click_trans_id": "1234567890",
    "merchant_trans_id": "123",
    "amount": "150000",
    "status": "2"
}
```

**Status Codes:**
- `0` = Payment error/cancelled
- `1` = Payment preparing
- `2` = Payment confirmed (success)

**Response:**
```json
{
    "success": true,
    "message": "Payment processed successfully"
}
```

---

### 3. Check Payment Status
**Endpoint:** `GET /api/orders/payment-status/<order_id>/`

**Purpose:** Check the current payment status of an order.

**Request:**
```
GET /api/orders/payment-status/123/
X-Telegram-Init-Data: {telegram_init_data}
```

**Response:**
```json
{
    "order_id": 123,
    "payment_method": "online",
    "payment_status": "paid",
    "paid_at": "2024-12-06T15:30:45.123456Z",
    "amount": "150000",
    "transaction": {
        "id": 45,
        "status": "confirmed",
        "click_trans_id": 999999
    }
}
```

---

## Frontend Integration (React)

### Example Flow

```javascript
// 1. Prepare order and get payment URL
const initiatePayment = async (orderId) => {
    try {
        const response = await fetch('http://localhost:8000/api/orders/initiate-payment/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-Init-Data': initData,  // From TMA
            },
            body: JSON.stringify({ order_id: orderId }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Redirect to payment URL
            window.open(data.payment_url, '_blank');
            
            // Poll for payment status
            checkPaymentStatus(orderId);
        } else {
            console.error('Payment initiation failed:', data.error);
        }
    } catch (error) {
        console.error('Error:', error);
    }
};

// 2. Check payment status (poll every 2 seconds)
const checkPaymentStatus = async (orderId) => {
    const maxAttempts = 30;  // 1 minute max
    let attempts = 0;
    
    const poll = setInterval(async () => {
        attempts++;
        
        try {
            const response = await fetch(
                `http://localhost:8000/api/orders/payment-status/${orderId}/`,
                {
                    headers: {
                        'X-Telegram-Init-Data': initData,
                    },
                }
            );
            
            const data = await response.json();
            
            if (data.payment_status === 'paid') {
                clearInterval(poll);
                console.log('Payment successful!');
                // Redirect to success page or order details
                // navigate(`/orders/${orderId}`);
            }
        } catch (error) {
            console.error('Error checking payment status:', error);
        }
        
        if (attempts >= maxAttempts) {
            clearInterval(poll);
            console.log('Payment check timed out');
        }
    }, 2000);
};

// Usage
async function handleCheckout() {
    const cartOrder = await getCartOrder();
    if (cartOrder) {
        initiatePayment(cartOrder.id);
    }
}
```

---

## Local Testing (Mock Mode)

### Test Flow

1. **Add items to cart:**
   ```javascript
   POST /api/orders/cart/
   {
       "product_id": 1,
       "quantity": 2
   }
   ```

2. **Update delivery info:**
   ```javascript
   PATCH /api/orders/cart/
   {
       "delivery_type": "delivery",
       "address_text": "123 Main St, Apartment 5"
   }
   ```

3. **Initiate payment:**
   ```javascript
   POST /api/orders/initiate-payment/
   {
       "order_id": {cart_order_id}
   }
   ```
   Response will include a mock payment URL like:
   ```
   http://localhost:8000/api/orders/payment/mock-callback/?order_id=123&amount=150000
   ```

4. **Simulate payment:**
   - Click the URL or make a GET request to it
   - This will simulate a successful payment callback
   - Order status will change from "cart" to "new"
   - Payment status will change to "paid"

---

## Order States During Payment

| State | Description | Payment Status |
|-------|-------------|-----------------|
| `cart` | Order in cart, not yet submitted | `pending` |
| `new` | Order submitted and ready for preparation | `pending` or `paid` |
| `preparing` | Kitchen is preparing the order | `paid` |
| `delivering` | Order is on the way | `paid` |
| `done` | Order delivered | `paid` |
| `canceled` | Order was cancelled | `pending` or `paid` |

---

## Environment Variables

For local development (`.env`):
```
CLICK_IS_MOCK=True
CLICK_MERCHANT_ID=12345
CLICK_MERCHANT_KEY=mock_key_for_local_dev
```

For production, update with real credentials from Click:
```
CLICK_IS_MOCK=False
CLICK_MERCHANT_ID=your_real_merchant_id
CLICK_MERCHANT_KEY=your_real_merchant_key
CLICK_API_URL=https://api.click.uz/v2/merchant
```

---

## Production Deployment

When deploying to production:

1. **Get real credentials** from [Click Merchant Portal](https://merchant.click.uz)
2. **Update environment variables** in production `.env`
3. **Implement proper signature verification** in `PaymentCallbackView` (currently mocked)
4. **Set up SSL certificate** for HTTPS (required by Click)
5. **Configure webhook URL** in Click dashboard to point to: `https://yourdomain.com/api/orders/payment-callback/`
6. **Test with real transactions** in Click sandbox environment

---

## Database Migrations

To create the necessary tables, run:
```bash
python manage.py makemigrations
python manage.py migrate
```

The `ClickTransaction` model is already defined in `orders/models.py`.

---

## Error Handling

### Common Issues

**"Cart is empty"**
- Solution: Add items to cart first

**"Delivery information is incomplete"**
- Solution: Update cart with `delivery_type` and `address_text`

**Payment status not updating**
- Check if webhook URL is correct
- Verify X-Telegram-Init-Data header in requests
- Check Django logs for errors

**Payment URL not opening (Mock mode)**
- For mock testing, manually visit the payment URL or make a GET request
- Real Click integration requires user interaction on Click's payment page

---

## Support

For issues or questions, check the payment service implementation in:
- `/orders/payment_service.py` - Payment logic
- `/orders/views.py` - API endpoints (InitiatePaymentView, PaymentCallbackView, CheckPaymentStatusView)
- `/orders/models.py` - ClickTransaction model
