# QR Menu Implementation Guide

## Overview
A complete QR ordering system has been implemented for "Dine-in" scenarios.
Tables can be managed in Admin, QR codes are generated automatically, and users can order via a specific web interface without Telegram.

## Backend Changes (`orders` app)
1.  **Models**:
    *   `Table`: Configured with Number, UUID, and auto-generated QR Code.
    *   `Order`: Added `table` field and `dine_in` delivery type.
2.  **Admin**:
    *   Manage Tables unique QR codes.
    *   Orders now show Table number.
3.  **API**:
    *   `CheckoutView` supports `delivery_type: "dine_in"`. It requires `table_uuid` and skips address validation.
    *   `MiniAppUserMixin` supports `X-Guest-ID` header for guest users (outside Telegram).

## Frontend Changes (`src/pages/QR`)
1.  **Routes**:
    *   `/menu/:tableUuid` - Landing Page (Logo, "CLICK TO ORDER").
    *   `/menu/:tableUuid/catalog` - Menu Page (Categories, Products).
2.  **Components**:
    *   `QRLandingPage.jsx`: Visual entry point matching design.
    *   `QRMenuPage.jsx`: Main catalog with category filtering.
    *   `QRProductCard.jsx`: Product display card.
    *   `QRCheckoutModal.jsx`: Simplified checkout for sending orders to kitchen.
    *   `QRCartButton.jsx`: Floating cart summary.

## How to Use
1.  **Create Tables**:
    *   Go to Admin -> Orders -> Столики.
    *   Create "Table 1".
    *   Save. The QR code image will be generated automatically.
2.  **Print QR Codes**:
    *   Open the Table in admin.
    *   Click on the QR code preview to see/download the image.
    *   The QR code points to `http://localhost:5173/menu/<uuid>`. **Note: Change domain in `orders/models.py` for production.**
3.  **User Flow**:
    *   User scans QR.
    *   Opens Landing Page.
    *   kliks "MENU".
    *   Selects items -> Adds to Cart.
    *   Clicks "Order" -> "Confirm".
    *   Order appears in Admin as "Dine-in" with Table info.
