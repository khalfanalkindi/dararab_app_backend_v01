from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static

# ✅ Root API Response
def api_root(request):
    return JsonResponse({"message": "Welcome to DarArab API", "status": "success"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),  #Include all user management APIs
    path('api/inventory/', include('inventory.urls')),
    path('api/common/', include('common.urls')),
    path('', api_root, name='api-root'),
    path('api/sales/', include('sales.urls')),
]

# Serve media files in development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
