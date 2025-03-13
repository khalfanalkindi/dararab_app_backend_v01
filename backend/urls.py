from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

# ✅ Root API Response
def api_root(request):
    return JsonResponse({"message": "Welcome to DarArab API", "status": "success"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),  # ✅ Include all user management APIs
    path('', api_root, name='api-root'),  # ✅ Root endpoint
]
