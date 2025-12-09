# Implement Dynamic Delivery Pricing

## Backend Changes
1.  **Models (`orders/models.py`)**:
    *   Updated `RestaurantSettings` to include:
        *   `restaurant_lat`, `restaurant_lng`: Restaurant coordinates.
        *   `delivery_base_price`: Base price (default 15,000 sum).
        *   `delivery_base_km`: Base distance (default 2 km).
        *   `delivery_price_per_km`: Extra price per km (default 2,000 sum).
    *   Updated `Order` to include:
        *   `delivery_price`: Frozen delivery cost for the order.
        *   `distance_km`: Calculated distance.
        *   `final_price` property logic updated to include delivery price.

2.  **Admin (`orders/admin.py`)**:
    *   `RestaurantSettingsAdmin`: Added fields for configuring dynamic pricing.
    *   `OrderAdmin`: Added display for `delivery_price` and `distance_km`.

3.  **API (`orders/views.py` & `orders/urls.py`)**:
    *   Added `/api/orders/calculate-delivery/` endpoint that accepts `latitude` and `longitude` and returns `price` and `distance`.
    *   Updated `CheckoutView` to calculate and save delivery price/distance when creating an order.

4.  **Utils (`orders/utils.py`)**:
    *   Updated `calculate_delivery_cost` to use the new settings fields.

## Frontend Changes
1.  **CheckoutModal (`src/components/CheckoutModal.jsx`)**:
    *   Added state for `calculatedDeliveryPrice` and `calculatedDistance`.
    *   Added `useEffect` to call `calculate-delivery` API when delivery type is "delivery" and coordinates are available.
    *   Updated UI to display the calculated price and distance.
    *   Updated total price calculation to use the dynamic delivery price.

## How to test
1.  Go to Admin Panel -> Restaurant Settings.
2.  Configure Base Price, Base Distance, Price per KM, and Restaurant Coordinates.
3.  Open the Telegram Mini App (or frontend).
4.  Add items to cart and go to Checkout.
5.  Select "Delivery" and choose a location on the map.
6.  Observer the delivery price updating based on distance from the restaurant.
