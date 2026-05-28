from django.core.signing import TimestampSigner, BadSignature
from django.utils import timezone
from rest_framework import serializers

from apps.base.utils import normalize_phone
from .models import User, TwoFactorOTP


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'role', 'cooperative_id', 'two_fa_enabled',
        ]


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(label='Email or phone number')
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs['email'].strip().lower()
        password = attrs['password']

        user = User.objects.filter(email=identifier).first()
        if not user:
            user = User.objects.filter(phone_number=identifier).first()

        if not user:
            raise serializers.ValidationError('Invalid credentials.')

        if not user.check_password(password):
            raise serializers.ValidationError('Invalid credentials.')
        if not user.is_active:
            raise serializers.ValidationError('Invalid credentials.')

        attrs['user'] = user
        return attrs


class RequestOTPSerializer(serializers.Serializer):
    login_token = serializers.CharField()

    def validate(self, attrs):
        signer = TimestampSigner()
        try:
            email = signer.unsign(attrs['login_token'], max_age=180)
        except BadSignature:
            raise serializers.ValidationError('Invalid or expired login token.')

        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError('Invalid credentials.')

        attrs['user'] = user
        return attrs


class TwoFAVerifySerializer(serializers.Serializer):
    login_token = serializers.CharField()
    otp_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        signer = TimestampSigner()
        try:
            email = signer.unsign(attrs['login_token'], max_age=180)
        except BadSignature:
            raise serializers.ValidationError('Invalid or expired login token.')

        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError('Invalid credentials.')

        otp = TwoFactorOTP.objects.filter(
            user=user,
            purpose='LOGIN',
            is_used=False,
            expires_at__gt=timezone.now(),
        ).last()

        if not otp:
            raise serializers.ValidationError('Invalid or expired OTP.')

        if otp.attempts >= 5:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            raise serializers.ValidationError('Too many attempts. Request a new OTP.')

        otp.attempts += 1

        if otp.otp_code != attrs['otp_code']:
            otp.save(update_fields=['attempts'])
            raise serializers.ValidationError('Invalid or expired OTP.')

        otp.is_used = True
        otp.save(update_fields=['attempts', 'is_used'])

        attrs['user'] = user
        return attrs


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'phone_number', 'first_name', 'last_name', 'password']

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
        return User.objects.create_user(**validated_data)


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
