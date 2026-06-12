import secrets

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.auth_api.models import User
from apps.base.constants import UserRole
from apps.base.models import AuditLog, AuditAction
from apps.cooperatives.models import Cooperative

User = get_user_model()


class CreateSuperUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('A user with this phone number already exists.')
        return value

    def create(self, validated_data):
        return User.objects.create_superuser(**validated_data)


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'role', 'cooperative', 'is_active', 'is_staff', 'is_superuser',
            'two_fa_enabled', 'must_change_password', 'date_joined', 'last_login',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'is_superuser']

    def validate_email(self, value):
        instance = self.instance
        qs = User.objects.filter(email=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_phone_number(self, value):
        instance = self.instance
        qs = User.objects.filter(phone_number=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A user with this phone number already exists.')
        return value


class AdminUserActivateSerializer(serializers.Serializer):
    pass

class AdminUserDeactivateSerializer(serializers.Serializer):
    pass

class AdminUserToggle2FASerializer(serializers.Serializer):
    pass


class AdminUserResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8, required=False, allow_blank=True)

    def create(self, validated_data):
        password = validated_data.get('new_password') or secrets.token_urlsafe(12)
        return {'new_password': password}


class AdminCooperativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cooperative
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_member_sequence', 'last_delivery_sequence']


class AdminCooperativeActivateSerializer(serializers.Serializer):
    pass


class AdminCooperativeDeactivateSerializer(serializers.Serializer):
    pass


class AdminDashboardSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    users_by_role = serializers.DictField(child=serializers.IntegerField())
    total_cooperatives = serializers.IntegerField()
    total_farmers = serializers.IntegerField()
    total_deliveries = serializers.IntegerField()
    deliveries_by_status = serializers.DictField(child=serializers.IntegerField())
    total_payment_cycles = serializers.IntegerField()
    cycles_by_status = serializers.DictField(child=serializers.IntegerField())
    total_disbursement_batches = serializers.IntegerField()
    batches_by_status = serializers.DictField(child=serializers.IntegerField())
    total_audit_logs = serializers.IntegerField()


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'


class ImpersonateSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    expires_in = serializers.IntegerField()
    is_impersonated = serializers.BooleanField()
    user_id = serializers.CharField()
    role = serializers.CharField()
    cooperative_id = serializers.CharField(allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['expires_in'] = 900
        data['is_impersonated'] = True
        return data
