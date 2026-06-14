import secrets

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import serializers

from apps.auth_api.models import User
from apps.base.utils import KENYA_PHONE_RE, normalize_phone
from apps.cooperatives.models import Cooperative


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'role', 'cooperative_id', 'is_active', 'two_fa_enabled',
            'must_change_password', 'date_joined', 'avatar',
        ]
        read_only_fields = ['id', 'cooperative_id', 'date_joined', 'two_fa_enabled', 'must_change_password', 'avatar']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'email', 'phone_number', 'first_name', 'last_name',
            'role', 'password', 'is_active',
        ]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_phone_number(self, value):
        value = normalize_phone(value)
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('A user with this phone number already exists.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None) or secrets.token_urlsafe(8)
        user = User(**validated_data)
        user.set_password(password)
        role = validated_data.get('role')
        if role and role not in ('admin', 'farmer'):
            user.must_change_password = True
        user.save()

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
        send_mail(
            'Your Zao Account Credentials',
            f'Your account has been created.\n\n'
            f'Email: {user.email}\n'
            f'Temporary password: {password}\n\n'
            f'Please log in and change your password on first use.',
            from_email,
            [user.email],
            fail_silently=False,
        )

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    cooperative_id = serializers.UUIDField(required=False, write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'phone_number', 'first_name', 'last_name',
            'role', 'password', 'is_active', 'cooperative_id',
        ]
        extra_kwargs = {field: {'required': False} for field in fields if field not in ('password', 'cooperative_id')}

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_phone_number(self, value):
        value = normalize_phone(value)
        if User.objects.filter(phone_number=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('A user with this phone number already exists.')
        return value

    def validate_cooperative_id(self, value):
        if not Cooperative.objects.filter(id=value).exists():
            raise serializers.ValidationError('Cooperative not found.')
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
            instance.must_change_password = False
        instance.save()
        return instance


class UserSelfUpdateSerializer(serializers.ModelSerializer):
    current_password = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'email', 'current_password', 'password', 'avatar']
        read_only_fields = ['email', 'avatar']
        extra_kwargs = {field: {'required': False} for field in fields if field not in ('email', 'avatar', 'current_password')}

    def validate_phone_number(self, value):
        value = normalize_phone(value)
        if not KENYA_PHONE_RE.match(value):
            raise serializers.ValidationError('Invalid phone number format.')
        if User.objects.filter(phone_number=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('A user with this phone number already exists.')
        return value

    def validate(self, attrs):
        if attrs.get('password') and not attrs.get('current_password'):
            raise serializers.ValidationError(
                {'current_password': 'Current password is required to set a new password.'}
            )
        if attrs.get('current_password'):
            if not self.instance.check_password(attrs['current_password']):
                raise serializers.ValidationError(
                    {'current_password': 'Current password is incorrect.'}
                )
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop('current_password', None)
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
            instance.must_change_password = False
        instance.save()
        return instance


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField(
        allow_empty_file=False,
    )

    def validate_avatar(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Image size must not exceed 5MB.')
        if value.content_type not in ('image/jpeg', 'image/png'):
            raise serializers.ValidationError('Only JPEG and PNG images are allowed.')
        return value
