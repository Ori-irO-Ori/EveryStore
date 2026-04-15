from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from .models import Product, Category, SiteSettings


def index(request):
    site = SiteSettings.get()

    # If a custom homepage HTML has been uploaded, serve it directly
    if site.custom_homepage:
        try:
            html = default_storage.open(site.custom_homepage.name).read().decode('utf-8')
            return HttpResponse(html, content_type='text/html; charset=utf-8')
        except Exception:
            pass  # Fall through to default template if file is missing/broken

    featured = Product.objects.filter(is_available=True, is_featured=True).prefetch_related('images')[:8]
    latest = Product.objects.filter(is_available=True).prefetch_related('images')[:12]
    categories = Category.objects.all()[:6]
    return render(request, 'store/index.html', {
        'featured_products': featured,
        'latest_products': latest,
        'categories': categories,
    })


def product_list(request):
    products = Product.objects.filter(is_available=True).prefetch_related('images')
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()
    selected_category = None

    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)

    if search_query:
        products = products.filter(name__icontains=search_query)

    paginator = Paginator(products, 12)
    page = paginator.get_page(request.GET.get('page'))
    categories = Category.objects.all()

    return render(request, 'store/product_list.html', {
        'page_obj': page,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
    })


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.prefetch_related('images'),
        slug=slug,
        is_available=True
    )
    related = Product.objects.filter(
        category=product.category, is_available=True
    ).exclude(pk=product.pk).prefetch_related('images')[:4]

    return render(request, 'store/product_detail.html', {
        'product': product,
        'related_products': related,
    })
