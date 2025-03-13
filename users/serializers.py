from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role, Page, RolePermission, UserPermission

User = get_user_model()

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'is_active', 'password', 'role']

    def create(self, validated_data):
        role = validated_data.pop('role', None)  # Extract role if provided
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            phone_number=validated_data.get('phone_number', ''),
            is_active=validated_data.get('is_active', True),
            password=validated_data['password']
        )
        if role:
            user.role = role  # Assign role if provided
            user.save()
        return user


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name']

class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'name', 'url']

class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = ['id', 'role', 'page', 'can_view', 'can_add', 'can_edit', 'can_delete']

class UserPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPermission
        fields = ['id', 'user', 'page', 'can_view', 'can_add', 'can_edit', 'can_delete']
