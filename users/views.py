from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from .models import CustomUser, Role, Page, RolePermission, UserPermission
from .serializers import UserSerializer, RoleSerializer, PageSerializer, RolePermissionSerializer, UserPermissionSerializer
from rest_framework.permissions import IsAuthenticated
from django.db.models import ProtectedError

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
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data  # ✅ Return user details on login
            })
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  # ✅ Ensures only authenticated users can log out

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()  # ✅ Blacklist the token to prevent reuse

            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

### ✅ User Management
class UserListCreateView(generics.ListCreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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

