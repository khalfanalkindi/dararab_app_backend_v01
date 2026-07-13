from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    MyPermissionsView,
    MeView,
    ChangePasswordView,
    PageDeleteView,
    PageUpdateView,
    RoleDeleteView,
    RolePermissionDeleteView,
    RolePermissionUpdateView,
    RoleUpdateView,
    UserDeleteView,
    UserListCreateView,
    UserPermissionDeleteView,
    UserPermissionUpdateView,
    UserRetrieveUpdateDestroyView,
    RoleListCreateView,
    PageListCreateView,
    RolePermissionListCreateView,
    UserPermissionListCreateView,
    TokenRefreshView,
)

urlpatterns = [
    # ✅ Authentication
    path('auth/login/', LoginView.as_view(), name='login'),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh_alias"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/my-permissions/", MyPermissionsView.as_view(), name="my-permissions"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),

    # ✅ User Management
    path('users/', UserListCreateView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', UserRetrieveUpdateDestroyView.as_view(), name='user-detail'),
    path('users/<int:pk>/delete/', UserDeleteView.as_view(), name='user-delete'),

    # ✅ Roles Management
    path("roles/", RoleListCreateView.as_view(), name="roles"),
    path("roles/<int:pk>/", RoleUpdateView.as_view(), name="role-update"),
    path("roles/<int:pk>/delete/", RoleDeleteView.as_view(), name="role-delete"),


    # ✅ Page Management URLs
    path("pages/", PageListCreateView.as_view(), name="page-list-create"),
    path("pages/<int:pk>/", PageUpdateView.as_view(), name="page-update"),
    path("pages/<int:pk>/delete/", PageDeleteView.as_view(), name="page-delete"),
    
 # ✅ Role-Based Permissions Management
    path("permissions/roles/", RolePermissionListCreateView.as_view(), name="role-permission-list-create"),
    path("permissions/roles/<int:pk>/", RolePermissionUpdateView.as_view(), name="role-permission-update"),
    path("permissions/roles/<int:pk>/delete/", RolePermissionDeleteView.as_view(), name="role-permission-delete"),

    # ✅ User-Specific Permissions Management
    path("permissions/users/", UserPermissionListCreateView.as_view(), name="user-permission-list-create"),
    path("permissions/users/<int:pk>/", UserPermissionUpdateView.as_view(), name="user-permission-update"),
    path("permissions/users/<int:pk>/delete/", UserPermissionDeleteView.as_view(), name="user-permission-delete"),

]
