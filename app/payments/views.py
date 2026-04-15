import json
import base64
import requests as http
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from orders.models import Cart, Order, OrderItem


def _paypal_base_url():
    if settings.PAYMENT_MODE == 'live':
        return 'https://api-m.paypal.com'
    return 'https://api-m.sandbox.paypal.com'


def _get_access_token():
    """Exchange client credentials for a short-lived access token."""
    credentials = base64.b64encode(
        f'{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}'.encode()
    ).decode()
    resp = http.post(
        f'{_paypal_base_url()}/v1/oauth2/token',
        headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        data='grant_type=client_credentials',
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()['access_token']


@require_POST
def create_paypal_order(request):
    """
    1. Validate cart
    2. Save shipping/contact info from form
    3. Create a PayPal order via Orders API v2
    4. Return the PayPal order ID to the frontend
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not request.session.session_key:
        return JsonResponse({'error': 'No active session'}, status=400)

    try:
        cart = Cart.objects.prefetch_related('items__product').get(
            session_key=request.session.session_key
        )
    except Cart.DoesNotExist:
        return JsonResponse({'error': 'Cart not found'}, status=400)

    if cart.total_items == 0:
        return JsonResponse({'error': 'Cart is empty'}, status=400)

    currency = settings.STORE_CURRENCY.upper()
    amount = f'{cart.subtotal:.2f}'

    # Create Order in pending state
    order = Order.objects.create(
        email=data.get('email', ''),
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        address_line1=data.get('address_line1', ''),
        address_line2=data.get('address_line2', ''),
        city=data.get('city', ''),
        state=data.get('state', ''),
        country=data.get('country', ''),
        postal_code=data.get('postal_code', ''),
        note=data.get('note', ''),
        total_amount=cart.subtotal,
        status='pending',
    )
    for cart_item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            product_name=cart_item.product.name,
            product_price=cart_item.product.price,
            quantity=cart_item.quantity,
        )

    # Call PayPal
    try:
        token = _get_access_token()
        resp = http.post(
            f'{_paypal_base_url()}/v2/checkout/orders',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            json={
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'custom_id': order.order_number,
                    'description': settings.STORE_NAME,
                    'amount': {
                        'currency_code': currency,
                        'value': amount,
                    },
                }],
                'payment_source': {
                    'paypal': {
                        'experience_context': {
                            'return_url': request.build_absolute_uri('/payments/return/'),
                            'cancel_url': request.build_absolute_uri('/cart/checkout/'),
                            'user_action': 'PAY_NOW',
                            'shipping_preference': 'NO_SHIPPING',
                        }
                    }
                },
            },
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        order.delete()
        return JsonResponse({'error': f'PayPal error: {e}'}, status=502)

    result = resp.json()
    paypal_order_id = result['id']
    order.paypal_order_id = paypal_order_id
    order.save()

    # Find the approval URL to redirect the buyer to PayPal
    approval_url = next(
        (link['href'] for link in result.get('links', []) if link['rel'] == 'payer-action'),
        None
    )
    if not approval_url:
        order.delete()
        return JsonResponse({'error': 'PayPal did not return an approval URL.'}, status=502)

    return JsonResponse({
        'approval_url': approval_url,
        'order_number': order.order_number,
    })


def paypal_return(request):
    """
    PayPal redirects here after the buyer approves payment.
    The SDK picks up ?token= automatically and fires onApprove.
    This view just renders the checkout page in "returning" state.
    """
    from django.shortcuts import render
    from orders.models import Cart
    cart = Cart.objects.filter(
        session_key=request.session.session_key
    ).first() if request.session.session_key else None
    return render(request, 'orders/paypal_return.html', {
        'cart': cart,
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
    })


@require_POST
def capture_paypal_order(request):
    """
    Called after the buyer approves in PayPal's UI.
    Captures the payment and marks the order as paid.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    paypal_order_id = data.get('paypal_order_id', '')
    if not paypal_order_id:
        return JsonResponse({'error': 'Missing paypal_order_id'}, status=400)

    try:
        order = Order.objects.get(paypal_order_id=paypal_order_id, status='pending')
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

    # Capture the payment
    try:
        token = _get_access_token()
        resp = http.post(
            f'{_paypal_base_url()}/v2/checkout/orders/{paypal_order_id}/capture',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        return JsonResponse({'error': f'Capture failed: {e}'}, status=502)

    capture_status = result.get('status', '')
    if capture_status == 'COMPLETED':
        order.status = 'paid'
        order.save()
        # Clear the cart
        Cart.objects.filter(session_key=request.session.session_key).delete()
        # Send confirmation email (non-blocking — errors are logged, not raised)
        from .emails import send_order_confirmation
        send_order_confirmation(order)
        return JsonResponse({'success': True, 'order_number': order.order_number})

    return JsonResponse({'error': f'Payment not completed: {capture_status}'}, status=400)
