from django.core.signing import TimestampSigner, BadSignature
from django.utils import timezone
from rest_framework import serializers

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
            otp_code=attrs['otp_code'],
            purpose='LOGIN',
            is_used=False,
            expires_at__gt=timezone.now(),
        ).last()

        if not otp:
            raise serializers.ValidationError('Invalid or expired OTP.')

        if otp.attempts >= 5:
            raise serializers.ValidationError('Too many attempts. Request a new OTP.')

        otp.attempts += 1
        otp.is_used = True
        otp.save(update_fields=['attempts', 'is_used'])

        attrs['user'] = user
        return attrs


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
