from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role, Page, RolePermission, UserPermission

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'is_active', 'password', 'role', 'first_name', 'last_name']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        role = validated_data.pop('role', None)
        user = User.objects.create_user(**validated_data)
        
        if password:
            user.set_password(password)
            user.save()
        if role:
            user.role = role
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class UserBasicSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class MeSerializer(serializers.ModelSerializer):
    """Current-user profile: readable role label; role/is_active not writable here."""

    role_name = serializers.SerializerMethodField(read_only=True)
    role = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'phone_number',
            'first_name',
            'last_name',
            'role',
            'role_name',
            'is_active',
        ]
        read_only_fields = ['id', 'role', 'role_name', 'is_active']

    def get_role_name(self, obj):
        if obj.role_id and obj.role:
            return obj.role.name
        if obj.is_superuser:
            return "Admin"
        return ""

    def validate_username(self, value):
        user = self.instance
        qs = User.objects.filter(username=value)
        if user:
            qs = qs.exclude(pk=user.pk)
        if qs.exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if not value:
            return value
        user = self.instance
        qs = User.objects.filter(email=value)
        if user:
            qs = qs.exclude(pk=user.pk)
        if qs.exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def validate_phone_number(self, value):
        if value in (None, ""):
            return None
        user = self.instance
        qs = User.objects.filter(phone_number=value)
        if user:
            qs = qs.exclude(pk=user.pk)
        if qs.exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'name_ar']

class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'name', 'name_ar', 'url']

class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = ['id', 'role', 'page', 'can_view', 'can_add', 'can_edit', 'can_delete', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class UserPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPermission
        fields = ['id', 'user', 'page', 'can_view', 'can_add', 'can_edit', 'can_delete', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
