#!/usr/bin/env python
"""
Test script to verify payment flow
"""
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.test import Client
from telegram_users.models import TelegramUser
from orders.models import Order, OrderItem
from menu.models import Product, Category
import json

def test_payment_flow():
    """Test the complete payment flow"""
    
    client = Client()
    headers = {"X-Telegram-Init-Data": "dev_mode"}
    
    # Get or create test user
    tg_user, _ = TelegramUser.objects.get_or_create(
        telegram_id=999999999,
        defaults={
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
        }
    )
    print(f"✓ Test user created: {tg_user}")
    
    # Get or create category
    category, _ = Category.objects.get_or_create(
        name="Test Category",
        defaults={
            "slug": "test-category",
            "is_active": True
        }
    )
    print(f"✓ Category created/found: {category}")
    
    # Create or get a product
    product, _ = Product.objects.get_or_create(
        name="Test Pizza",
        category=category,
        defaults={
            "description": "A test pizza",
            "price": 50000,
            "is_active": True,
        }
    )
    print(f"✓ Product created/found: {product}")
    
    # Create cart
    cart, _ = Order.objects.get_or_create(
        user=tg_user,
        status="cart",
        defaults={
            "delivery_type": "pickup",
            "payment_method": "cash",
        }
    )
    print(f"✓ Cart created: {cart}")
    
    # Add item to cart
    item, _ = OrderItem.objects.get_or_create(
        order=cart,
        product=product,
        defaults={
            "quantity": 1,
            "price": product.price
        }
    )
    print(f"✓ Item added to cart: {item}")
    
    # Checkout with online payment
    print("\n=== TESTING CHECKOUT ===")
    response = client.post(
        "/api/orders/checkout/",
        data=json.dumps({
            "delivery_type": "pickup",
            "address_text": "Test Address",
            "payment_method": "online",
        }),
        content_type="application/json",
        **{"HTTP_X_TELEGRAM_INIT_DATA": "dev_mode"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    checkout_data = response.json()
    
    # Get order ID from active_orders
    if checkout_data.get("active_orders"):
        order_id = checkout_data["active_orders"][0]["id"]
        print(f"\n✓ Order ID from checkout: {order_id}")
        
        # Try to initiate payment
        print("\n=== TESTING PAYMENT INITIATION ===")
        payment_response = client.post(
            "/api/orders/initiate-payment/",
            data=json.dumps({"order_id": order_id}),
            content_type="application/json",
            **{"HTTP_X_TELEGRAM_INIT_DATA": "dev_mode"}
        )
        
        print(f"Status: {payment_response.status_code}")
        payment_data = payment_response.json()
        print(f"Response: {payment_data}")
        
        if payment_data.get("success"):
            print(f"\n✓ Payment URL: {payment_data.get('payment_url')}")
        else:
            print(f"\n✗ Payment error: {payment_data.get('error')}")
    else:
        print("✗ No active_orders in checkout response")

if __name__ == "__main__":
    test_payment_flow()
