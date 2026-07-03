import logging
import secrets
from datetime import timedelta

logger = logging.getLogger(__name__)

from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import TimestampSigner
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.base.constants import UserRole

from .models import TwoFactorOTP, User
from .serializers import (
    LOGIN_TOKEN_SALT,
    FARMER_LOGIN_TOKEN_SALT,
    INVITE_TOKEN_SALT,
    PASSWORD_RESET_TOKEN_SALT,
    ChangePasswordSerializer,
    FarmerRequestOTPSerializer,
    FarmerVerifyOTPSerializer,
    GoogleLoginSerializer,
    InviteRequestOTPSerializer,
    InviteVerifySerializer,
    LoginSerializer,
    PasswordConfirmationSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    RequestOTPSerializer,
    TokenResponseSerializer,
    TwoFAVerifySerializer,
    UserSerializer,
)
from apps.base.idempotency import idempotent
from .throttles import (
    FarmerRequestOTPRateThrottle,
    GoogleLoginRateThrottle,
    InviteRequestOTPRateThrottle,
    InviteVerifyRateThrottle,
    LoginRateThrottle,
    PasswordResetRateThrottle,
    PasswordResetVerifyRateThrottle,
    RequestOTPRateThrottle,
    VerifyOTPRateThrottle,
)


def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        max_age=int(timedelta(days=7).total_seconds()),
        path='/api/auth/',
    )
    return response


def _build_user_claims(user):
    claims = {
        'role': user.role or '',
    }
    return claims


def _login_response(user):
    if user.must_change_password:
        return Response(
            {'detail': 'You must change your password before continuing.', 'must_change_password': True},
            status=status.HTTP_403_FORBIDDEN,
        )
    refresh = RefreshToken.for_user(user)
    claims = _build_user_claims(user)
    for k, v in claims.items():
        refresh.access_token[k] = v
        refresh[k] = v
    data = TokenResponseSerializer({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': user,
    }).data
    response = Response(data)
    _set_refresh_cookie(response, str(refresh))
    return response


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = LoginSerializer
    throttle_classes = [LoginRateThrottle]

    @idempotent()
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        requires_2fa = user.two_fa_enabled
        if requires_2fa:
            signer = TimestampSigner(salt=LOGIN_TOKEN_SALT)
            login_token = signer.sign(user.email)
            return Response({
                'requires_2fa': True,
                'login_token': login_token,
            })

        return _login_response(user)


class RequestOTPView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RequestOTPSerializer
    throttle_classes = [RequestOTPRateThrottle]

    @idempotent()
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        otp_code = f'{secrets.randbelow(1_000_000):06d}'
        expires_at = timezone.now() + timedelta(minutes=5)

        TwoFactorOTP.objects.create(
            user=user,
            otp_code=otp_code,
            purpose='LOGIN',
            expires_at=expires_at,
        )

        from_email = settings.DEFAULT_FROM_EMAIL
        try:
            send_mail(
                'Your Login OTP',
                f'Your OTP is: {otp_code}\nIt expires in 5 minutes.',
                from_email,
                [user.email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.exception(
                'Failed to send 2FA login OTP email to %s: %s', user.email, exc,
            )
            return Response(
                {'detail': 'Failed to send email. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = {'detail': 'OTP sent to your email.'}
        if settings.DEBUG:
            data['otp_code'] = otp_code
        return Response(data)


class VerifyOTPView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TwoFAVerifySerializer
    throttle_classes = [VerifyOTPRateThrottle]

    @idempotent()
    def post(self, request):
        serializer = TwoFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        return _login_response(user)


class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PasswordResetRequestSerializer
    throttle_classes = [PasswordResetRateThrottle]

    @idempotent()
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if user is None:
            signer = TimestampSigner(salt=PASSWORD_RESET_TOKEN_SALT)
            reset_token = signer.sign('unknown@placeholder.local')
            return Response({
                'reset_token': reset_token,
                'detail': 'OTP sent to your email.',
            })

        otp_code = f'{secrets.randbelow(1_000_000):06d}'
        expires_at = timezone.now() + timedelta(minutes=10)

        TwoFactorOTP.objects.create(
            user=user,
            otp_code=otp_code,
            purpose='PASSWORD_RESET',
            expires_at=expires_at,
        )

        signer = TimestampSigner(salt=PASSWORD_RESET_TOKEN_SALT)
        reset_token = signer.sign(user.email)

        from_email = settings.DEFAULT_FROM_EMAIL
        try:
            send_mail(
                'Reset Your Zao Password',
                f'Your OTP is: {otp_code}\nIt expires in 10 minutes.',
                from_email,
                [user.email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.exception(
                'Failed to send password reset OTP email to %s: %s', user.email, exc,
            )
            return Response(
                {'detail': 'Failed to send email. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = {
            'reset_token': reset_token,
            'detail': 'OTP sent to your email.',
        }
        if settings.DEBUG:
            data['otp_code'] = otp_code
        return Response(data)


class PasswordResetVerifyView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PasswordResetVerifySerializer
    throttle_classes = [PasswordResetVerifyRateThrottle]

    @idempotent()
    def post(self, request):
        serializer = PasswordResetVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        user.set_password(serializer.validated_data['password'])
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])

        # Invalidate all existing refresh tokens for this user
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        OutstandingToken.objects.filter(user=user).delete()

        return Response({'detail': 'Password reset successful.'})


class FarmerRequestOTPView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = FarmerRequestOTPSerializer
    throttle_classes = [FarmerRequestOTPRateThrottle]

    @idempotent()
    def post(self, request):
        from apps.notifications.utils import send_sms
        serializer = FarmerRequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        otp_code = f'{secrets.randbelow(1_000_000):06d}'
        expires_at = timezone.now() + timedelta(minutes=5)

        otp = TwoFactorOTP.objects.create(
            user=user,
            otp_code=otp_code,
            purpose='FARMER_LOGIN',
            expires_at=expires_at,
        )

        signer = TimestampSigner(salt=FARMER_LOGIN_TOKEN_SALT)
        login_token = signer.sign(f'{user.id}:{otp.id}')

        msg = f'Your OTP is: {otp_code}. It expires in 5 minutes.'
        send_sms(user.phone_number, msg)

        data = {
            'login_token': login_token,
            'detail': 'OTP sent to your phone.',
        }
        if settings.DEBUG:
            data['otp_code'] = otp_code
        return Response(data)


class FarmerVerifyOTPView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = FarmerVerifyOTPSerializer
    throttle_classes = [VerifyOTPRateThrottle]

    @idempotent()
    def post(self, request):
        serializer = FarmerVerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        return _login_response(user)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except (TokenError, AttributeError):
                pass
        response = Response({'detail': 'Logged out.'})
        response.delete_cookie('refresh_token', path='/api/auth/')
        return response


class InviteRequestOTPView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = InviteRequestOTPSerializer
    throttle_classes = [InviteRequestOTPRateThrottle]

    @idempotent()
    def post(self, request):
        serializer = InviteRequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        otp_code = f'{secrets.randbelow(1_000_000):06d}'
        expires_at = timezone.now() + timedelta(minutes=10)

        TwoFactorOTP.objects.create(
            user=user,
            otp_code=otp_code,
            purpose='ACTION_CONFIRM',
            expires_at=expires_at,
        )

        from_email = settings.DEFAULT_FROM_EMAIL
        try:
            send_mail(
                'Your Zao Invite Code',
                f'Your invite code is: {otp_code}\nIt expires in 10 minutes.',
                from_email,
                [user.email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.exception(
                'Failed to send invite OTP email to %s: %s', user.email, exc,
            )
            return Response(
                {'detail': 'Failed to send email. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = {'detail': 'OTP sent to your email.'}
        if settings.DEBUG:
            data['otp_code'] = otp_code
        return Response(data)


class InviteVerifyView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = InviteVerifySerializer
    throttle_classes = [InviteVerifyRateThrottle]

    @idempotent()
    def post(self, request):
        serializer = InviteVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        user.phone_number = serializer.validated_data['phone_number']
        user.set_password(serializer.validated_data['password'])
        user.is_active = True
        user.must_change_password = False
        user.save(update_fields=['phone_number', 'password', 'is_active', 'must_change_password'])

        return _login_response(user)


class GoogleLoginView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GoogleLoginSerializer
    throttle_classes = [GoogleLoginRateThrottle]

    @idempotent()
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        return _login_response(user)


class Enable2FAView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordConfirmationSerializer

    @idempotent()
    def post(self, request):
        serializer = PasswordConfirmationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        if user.two_fa_enabled:
            return Response({'detail': '2FA is already enabled.'}, status=status.HTTP_400_BAD_REQUEST)

        user.two_fa_enabled = True
        user.save(update_fields=['two_fa_enabled'])

        return Response({'detail': 'Two-factor authentication enabled.'})


class Disable2FAView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordConfirmationSerializer

    @idempotent()
    def post(self, request):
        serializer = PasswordConfirmationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.two_fa_enabled:
            return Response({'detail': '2FA is not enabled.'}, status=status.HTTP_400_BAD_REQUEST)

        if user.role in (UserRole.MANAGER, UserRole.ACCOUNTANT, UserRole.AUDITOR, UserRole.EXTERNAL_AUDITOR):
            return Response(
                {'detail': '2FA cannot be disabled for your role.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.two_fa_enabled = False
        user.save(update_fields=['two_fa_enabled'])

        return Response({'detail': 'Two-factor authentication disabled.'})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    @idempotent()
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])

        return _login_response(user)


class TokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TokenRefreshSerializer

    @idempotent()
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response(
                {'detail': 'Not authenticated.', 'authenticated': False},
                status=status.HTTP_200_OK,
            )

        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {'detail': 'Invalid or expired refresh token.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = serializer.validated_data
        response = Response(data)

        if jwt_settings.ROTATE_REFRESH_TOKENS and 'refresh' in data:
            _set_refresh_cookie(response, data['refresh'])

        return response
