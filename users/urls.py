from django.urls import path
from .views import LoginView, UserListCreateView, UserUpdateView, RoleListCreateView, PageListCreateView, RolePermissionListCreateView, UserPermissionListCreateView, PageAccessView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # ✅ Authentication
    path('auth/login/', LoginView.as_view(), name='login'),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ✅ User Management
    path('users/', UserListCreateView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', UserUpdateView.as_view(), name='user-update'),

    # ✅ Roles & Pages
    path('roles/', RoleListCreateView.as_view(), name='role-list-create'),
    path('pages/', PageListCreateView.as_view(), name='page-list-create'),

    # ✅ Permissions
    path('role-permissions/', RolePermissionListCreateView.as_view(), name='role-permission-list-create'),
    path('user-permissions/', UserPermissionListCreateView.as_view(), name='user-permission-list-create'),

    # ✅ Page Access Control
    path('page-access/<str:page_url>/', PageAccessView.as_view(), name='page-access'),
]
