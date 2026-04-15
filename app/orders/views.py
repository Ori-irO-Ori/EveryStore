import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from store.models import Product
from .models import Cart, CartItem, Order, OrderItem


def get_or_create_cart(request):
    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


def cart_count(request):
    """HTMX partial — returns just the cart item count badge."""
    cart = get_or_create_cart(request)
    count = cart.total_items
    if count == 0:
        return HttpResponse('')
    return HttpResponse(str(count))


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    cart = get_or_create_cart(request)

    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += 1
        item.save()

    # HTMX request: return the updated count badge + trigger toast
    if request.headers.get('HX-Request'):
        count = cart.total_items
        response = HttpResponse(str(count) if count > 0 else '')
        response['HX-Trigger'] = json.dumps({
            'cartUpdated': None,
            'showToast': {'message': f'"{product.name}" added to cart!', 'type': 'success'}
        })
        return response

    return redirect('cart_detail')


@require_POST
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__session_key=request.session.session_key)
    qty = int(request.POST.get('quantity', 1))

    if qty < 1:
        item.delete()
    else:
        item.quantity = qty
        item.save()

    if request.headers.get('HX-Request'):
        cart = get_or_create_cart(request)
        return render(request, 'orders/partials/cart_items.html', {'cart': cart})

    return redirect('cart_detail')


@require_POST
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__session_key=request.session.session_key)
    item.delete()

    if request.headers.get('HX-Request'):
        cart = get_or_create_cart(request)
        return render(request, 'orders/partials/cart_items.html', {'cart': cart})

    return redirect('cart_detail')


def cart_detail(request):
    cart = get_or_create_cart(request)
    return render(request, 'orders/cart.html', {'cart': cart})


def checkout(request):
    cart = get_or_create_cart(request)
    if cart.total_items == 0:
        return redirect('cart_detail')

    return render(request, 'orders/checkout.html', {
        'cart': cart,
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
        'payment_mode': settings.PAYMENT_MODE,
    })


def order_success(request):
    order_number = request.GET.get('order')
    order = None
    if order_number:
        try:
            order = Order.objects.prefetch_related('items').get(order_number=order_number)
        except Order.DoesNotExist:
            pass

    # Clear the cart once the user reaches the success page
    if request.session.session_key:
        Cart.objects.filter(session_key=request.session.session_key).delete()

    return render(request, 'orders/success.html', {'order': order})
