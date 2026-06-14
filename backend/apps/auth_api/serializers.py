from django.core.signing import TimestampSigner, BadSignature
from django.utils import timezone
from rest_framework import serializers

from apps.base.constants import UserRole
from apps.base.utils import normalize_phone
from apps.farmers.models import Farmer
from .models import User, TwoFactorOTP

LOGIN_TOKEN_SALT = 'auth-login-token'
FARMER_LOGIN_TOKEN_SALT = 'auth-farmer-login-token'
INVITE_TOKEN_SALT = 'auth-invite-token'
PASSWORD_RESET_TOKEN_SALT = 'auth-password-reset-token'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'role', 'cooperative_id', 'two_fa_enabled', 'must_change_password',
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
        signer = TimestampSigner(salt=LOGIN_TOKEN_SALT)
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
        signer = TimestampSigner(salt=LOGIN_TOKEN_SALT)
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
        ).order_by('-created_at').first()

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


class FarmerRequestOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        value = normalize_phone(value)
        # Try both normalized (2547...) and legacy (07...) formats
        alt = '0' + value[3:] if value.startswith('254') else value
        user = User.objects.filter(
            phone_number__in=[value, alt],
            role='farmer',
            is_active=True,
        ).select_related('farmer_profile').first()
        if not user:
            farmer = Farmer.objects.filter(phone_number__in=[value, alt]).first()
            if not farmer:
                raise serializers.ValidationError('No farmer account found with this phone number.')
        return value

    def validate(self, attrs):
        phone = attrs['phone_number']
        alt = '0' + phone[3:] if phone.startswith('254') else phone
        user = User.objects.filter(
            phone_number__in=[phone, alt], role='farmer', is_active=True,
        ).select_related('farmer_profile').first()
        if not user:
            farmer = Farmer.objects.filter(phone_number__in=[phone, alt]).first()
            if farmer:
                from apps.base.constants import UserRole
                from django.utils.crypto import get_random_string
                email = farmer.email or f'farmer_{farmer.id}@placeholder.local'
                user = User.objects.create_user(
                    email=email,
                    phone_number=farmer.phone_number,
                    first_name=farmer.first_name,
                    last_name=farmer.last_name,
                    password=get_random_string(length=72),
                    role=UserRole.FARMER,
                    cooperative_id=farmer.cooperative_id,
                )
                user.set_unusable_password()
                user.save(update_fields=['password'])
                farmer.user = user
                farmer.save(update_fields=['user'])
                user = User.objects.select_related('farmer_profile').get(id=user.id)
        attrs['user'] = user
        return attrs


class FarmerVerifyOTPSerializer(serializers.Serializer):
    login_token = serializers.CharField()
    otp_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        signer = TimestampSigner(salt=FARMER_LOGIN_TOKEN_SALT)
        try:
            payload = signer.unsign(attrs['login_token'], max_age=180)
        except BadSignature:
            raise serializers.ValidationError('Invalid or expired login token.')

        try:
            user_id, otp_id = payload.split(':', 1)
        except (ValueError, AttributeError):
            raise serializers.ValidationError('Invalid login token.')

        user = User.objects.filter(id=user_id, is_active=True).first()
        if not user:
            raise serializers.ValidationError('Invalid credentials.')

        otp = TwoFactorOTP.objects.filter(
            id=otp_id,
            user=user,
            purpose='FARMER_LOGIN',
            is_used=False,
            expires_at__gt=timezone.now(),
        ).first()

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


INVITE_MAX_AGE_SECONDS = 604800  # 7 days
INVITE_OTP_MAX_AGE_SECONDS = 600  # 10 minutes


class InviteRequestOTPSerializer(serializers.Serializer):
    invite_token = serializers.CharField()

    def validate(self, attrs):
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        try:
            email = signer.unsign(attrs['invite_token'], max_age=INVITE_MAX_AGE_SECONDS)
        except BadSignature:
            raise serializers.ValidationError('Invalid or expired invite token.')

        user = User.objects.filter(email=email, is_active=False, invite_revoked=False).first()
        if not user:
            raise serializers.ValidationError('Invalid or expired invite token.')

        attrs['user'] = user
        return attrs


class InviteVerifySerializer(serializers.Serializer):
    invite_token = serializers.CharField()
    otp_code = serializers.CharField(max_length=6)
    password = serializers.CharField(write_only=True, min_length=8)
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        value = normalize_phone(value)
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('A user with this phone number already exists.')
        return value

    def validate(self, attrs):
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        try:
            email = signer.unsign(attrs['invite_token'], max_age=INVITE_MAX_AGE_SECONDS)
        except BadSignature:
            raise serializers.ValidationError('Invalid or expired invite token.')

        user = User.objects.filter(email=email, is_active=False, invite_revoked=False).first()
        if not user:
            raise serializers.ValidationError('Invalid or expired invite token.')

        otp = TwoFactorOTP.objects.filter(
            user=user,
            purpose='ACTION_CONFIRM',
            is_used=False,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').first()

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


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs['email'].lower().strip()
        user = User.objects.filter(email=email, is_active=True).first()
        if not user:
            attrs['user'] = None
            return attrs
        attrs['user'] = user
        return attrs


PASSWORD_RESET_MAX_AGE_SECONDS = 600  # 10 minutes


class PasswordResetVerifySerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    otp_code = serializers.CharField(max_length=6)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        signer = TimestampSigner(salt=PASSWORD_RESET_TOKEN_SALT)
        try:
            email = signer.unsign(attrs['reset_token'], max_age=PASSWORD_RESET_MAX_AGE_SECONDS)
        except BadSignature:
            raise serializers.ValidationError('Invalid or expired reset token.')

        user = User.objects.filter(email=email, is_active=True).first()
        if not user:
            raise serializers.ValidationError('Invalid or expired reset token.')

        otp = TwoFactorOTP.objects.filter(
            user=user,
            purpose='PASSWORD_RESET',
            is_used=False,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').first()

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


class PasswordConfirmationSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Incorrect password.')
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Incorrect password.')
        return value


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
