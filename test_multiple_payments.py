#!/usr/bin/env python
"""
Test multiple payments to ensure no unique constraint errors
"""
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.test import Client
from telegram_users.models import TelegramUser
from orders.models import Order, OrderItem, ClickTransaction
from menu.models import Product, Category
import json

def test_multiple_payments():
    """Test multiple payment initiations"""
    
    client = Client()
    
    # Get or create test user
    tg_user, _ = TelegramUser.objects.get_or_create(
        telegram_id=999999999,
        defaults={
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
        }
    )
    
    # Get or create category and product
    category, _ = Category.objects.get_or_create(
        name="Test Category",
        defaults={
            "slug": "test-category",
            "is_active": True
        }
    )
    
    product, _ = Product.objects.get_or_create(
        name="Test Pizza",
        category=category,
        defaults={
            "description": "A test pizza",
            "price": 50000,
            "is_active": True,
        }
    )
    
    print("=== TESTING MULTIPLE PAYMENTS ===\n")
    
    for i in range(1, 4):
        print(f"Payment attempt #{i}:")
        
        # Create cart
        cart, _ = Order.objects.get_or_create(
            user=tg_user,
            status="cart",
            defaults={
                "delivery_type": "pickup",
                "payment_method": "cash",
            }
        )
        
        # Add item to cart
        item, _ = OrderItem.objects.get_or_create(
            order=cart,
            product=product,
            defaults={
                "quantity": 1,
                "price": product.price
            }
        )
        
        # Checkout
        response = client.post(
            "/api/orders/checkout/",
            data=json.dumps({
                "delivery_type": "pickup",
                "address_text": f"Test Address {i}",
                "payment_method": "online",
            }),
            content_type="application/json",
            **{"HTTP_X_TELEGRAM_INIT_DATA": "dev_mode"}
        )
        
        if response.status_code != 200:
            print(f"  ✗ Checkout failed: {response.status_code}")
            continue
        
        checkout_data = response.json()
        order_id = checkout_data["active_orders"][0]["id"]
        print(f"  ✓ Order created: {order_id}")
        
        # Initiate payment
        payment_response = client.post(
            "/api/orders/initiate-payment/",
            data=json.dumps({"order_id": order_id}),
            content_type="application/json",
            **{"HTTP_X_TELEGRAM_INIT_DATA": "dev_mode"}
        )
        
        if payment_response.status_code != 200:
            print(f"  ✗ Payment initiation failed: {payment_response.status_code}")
            print(f"     Error: {payment_response.json().get('error')}")
        else:
            payment_data = payment_response.json()
            print(f"  ✓ Payment initiated: Transaction ID {payment_data.get('transaction_id')}")
            print(f"  ✓ Payment URL: {payment_data.get('payment_url')[:60]}...")
        
        print()
    
    # Count transactions
    transaction_count = ClickTransaction.objects.all().count()
    print(f"Total transactions in DB: {transaction_count}")
    
    # List all transactions
    print("\nAll transactions:")
    for trans in ClickTransaction.objects.all().order_by('-id')[:5]:
        print(f"  - Transaction #{trans.id}: Order #{trans.order_id}, Status: {trans.status}, Click ID: {trans.click_trans_id}")

if __name__ == "__main__":
    test_multiple_payments()
