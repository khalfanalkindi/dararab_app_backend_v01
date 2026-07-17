from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from .models import CustomUser, Role, Page, RolePermission, UserPermission
from .serializers import (
    UserSerializer,
    RoleSerializer,
    PageSerializer,
    RolePermissionSerializer,
    UserPermissionSerializer,
    MeSerializer,
    ChangePasswordSerializer,
)
from .permissions_utils import build_permissions_payload
from users.api_permissions import IsAuthenticatedWithPagePermission as IsAuthenticated
from backend.exception_handler import error_response
from django.db.models import ProtectedError


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """
    POST /api/auth/token/refresh/  body: { "refresh": "<token>" }
    Returns { "access": "..." } and, with ROTATE_REFRESH_TOKENS, a new "refresh".
    Explicit AllowAny so DEFAULT_PERMISSION_CLASSES never blocks unauthenticated refresh.
    """

    permission_classes = [AllowAny]
    authentication_classes = []


### ✅ Login View
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
                "permissions": build_permissions_payload(user),
            })
        return error_response(
            code="INVALID_CREDENTIALS",
            detail="Invalid credentials",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class MyPermissionsView(APIView):
    """GET /api/auth/my-permissions/ — merged role + user page permissions."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_permissions_payload(request.user))


class MeView(APIView):
    """GET/PATCH /api/auth/me/ — current authenticated user profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/ — update password for current user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated successfully."})
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Accept both SimpleJWT-style "refresh" and legacy "refresh_token"
            refresh_token = request.data.get("refresh") or request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            return Response(
                {"detail": "Logged out successfully", "code": "OK", "field_errors": {}},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return error_response(
                code="LOGOUT_FAILED",
                detail=str(e) or "Logout failed.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

### ✅ User Management
class UserListCreateView(generics.ListCreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class UserRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class UserDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        user.delete()
        return Response({"message": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

### ✅ Role Management
# ✅ List & Create Roles
class RoleListCreateView(generics.ListCreateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

# ✅ Update Role
class RoleUpdateView(generics.UpdateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

# ✅ Delete Role (Handles Foreign Key Constraint)
class RoleDeleteView(generics.DestroyAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        role_id = kwargs.get("pk")
        try:
            role = Role.objects.get(id=role_id)
            role.delete()
            return Response({"message": "Role deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                {"error": "Cannot delete this role because it is assigned to users."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Role.DoesNotExist:
            return Response({"error": "Role not found."}, status=status.HTTP_404_NOT_FOUND)


### ✅ Page Management
# ✅ List & Create Pages
class PageListCreateView(generics.ListCreateAPIView):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated]


# ✅ Update Page
class PageUpdateView(generics.UpdateAPIView):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated]


# ✅ Delete Page (Handles Foreign Key Constraint)
class PageDeleteView(generics.DestroyAPIView):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        page_id = kwargs.get("pk")
        try:
            page = Page.objects.get(id=page_id)
            page.delete()
            return Response({"message": "Page deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                {"error": "Cannot delete this page because it is assigned to roles or other related data."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Page.DoesNotExist:
            return Response({"error": "Page not found."}, status=status.HTTP_404_NOT_FOUND)


### ✅ Role-Based Permissions Management
class RolePermissionListCreateView(generics.ListCreateAPIView):
    queryset = RolePermission.objects.all()
    serializer_class = RolePermissionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


### ✅ Update Role-Based Permission
class RolePermissionUpdateView(generics.UpdateAPIView):
    queryset = RolePermission.objects.all()
    serializer_class = RolePermissionSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


### ✅ Delete Role-Based Permission (Handles Foreign Key Constraint)
class RolePermissionDeleteView(generics.DestroyAPIView):
    queryset = RolePermission.objects.all()
    serializer_class = RolePermissionSerializer
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        permission_id = kwargs.get("pk")
        try:
            permission = RolePermission.objects.get(id=permission_id)
            permission.delete()
            return Response({"message": "Role-based permission deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                {"error": "Cannot delete this permission because it is assigned to a role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RolePermission.DoesNotExist:
            return Response({"error": "Permission not found."}, status=status.HTTP_404_NOT_FOUND)


### ✅ User-Specific Permissions Management (Overrides Role-Based Permissions)
class UserPermissionListCreateView(generics.ListCreateAPIView):
    queryset = UserPermission.objects.all()
    serializer_class = UserPermissionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


### ✅ Update User-Specific Permission
class UserPermissionUpdateView(generics.UpdateAPIView):
    queryset = UserPermission.objects.all()
    serializer_class = UserPermissionSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


### ✅ Delete User-Specific Permission (Handles Foreign Key Constraint)
class UserPermissionDeleteView(generics.DestroyAPIView):
    queryset = UserPermission.objects.all()
    serializer_class = UserPermissionSerializer
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        permission_id = kwargs.get("pk")
        try:
            permission = UserPermission.objects.get(id=permission_id)
            permission.delete()
            return Response({"message": "User-specific permission deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                {"error": "Cannot delete this permission because it is assigned to a user."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except UserPermission.DoesNotExist:
            return Response({"error": "Permission not found."}, status=status.HTTP_404_NOT_FOUND)

