from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import CustomUser, Role, Page, RolePermission, UserPermission
from .serializers import UserSerializer, RoleSerializer, PageSerializer, RolePermissionSerializer, UserPermissionSerializer

### ✅ Login View
class LoginView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            })
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

### ✅ User Management
class UserListCreateView(generics.ListCreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserUpdateView(generics.RetrieveUpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

### ✅ Role Management
class RoleListCreateView(generics.ListCreateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]

### ✅ Page Management
class PageListCreateView(generics.ListCreateAPIView):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [permissions.IsAuthenticated]

### ✅ Role-Based Permissions Management
class RolePermissionListCreateView(generics.ListCreateAPIView):
    queryset = RolePermission.objects.all()
    serializer_class = RolePermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

### ✅ User-Specific Permissions Management (Overrides Role-Based Permissions)
class UserPermissionListCreateView(generics.ListCreateAPIView):
    queryset = UserPermission.objects.all()
    serializer_class = UserPermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

### ✅ Page Access Control (Checks Role & User Permissions)
class PageAccessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, page_url):
        try:
            page = Page.objects.get(url=page_url)
        except Page.DoesNotExist:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get role-based permissions
        role_permissions = RolePermission.objects.filter(role=request.user.role, page=page).first()

        # Get user-specific permissions (if any)
        user_permissions = UserPermission.objects.filter(user=request.user, page=page).first()

        if user_permissions:
            return Response({
                "can_view": user_permissions.can_view or (role_permissions and role_permissions.can_view),
                "can_add": user_permissions.can_add or (role_permissions and role_permissions.can_add),
                "can_edit": user_permissions.can_edit or (role_permissions and role_permissions.can_edit),
                "can_delete": user_permissions.can_delete or (role_permissions and role_permissions.can_delete),
            }, status=status.HTTP_200_OK)
        elif role_permissions:
            return Response({
                "can_view": role_permissions.can_view,
                "can_add": role_permissions.can_add,
                "can_edit": role_permissions.can_edit,
                "can_delete": role_permissions.can_delete,
            }, status=status.HTTP_200_OK)

        return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)
