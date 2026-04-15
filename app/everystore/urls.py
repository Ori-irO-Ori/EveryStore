import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Admin URL path is set from secrets generated on first startup.
# Falls back to 'admin' if the env var is not set (e.g. during local dev).
admin_path = os.environ.get('ADMIN_URL_PATH', 'admin')

urlpatterns = [
    path(f'{admin_path}/', admin.site.urls),
    path('', include('store.urls')),
    path('cart/', include('orders.urls')),
    path('payments/', include('payments.urls')),
]

# Serve local media files during development (production uses S3 URLs directly)
if settings.DEBUG or not settings.S3_BUCKET:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
