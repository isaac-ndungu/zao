import uuid
import secrets
from datetime import timedelta

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
from apps.base.permissions import IsAdmin
from apps.base.utils import log_audit

from .models import TwoFactorOTP, User
from .serializers import (
    LOGIN_TOKEN_SALT,
    FARMER_LOGIN_TOKEN_SALT,
    INVITE_TOKEN_SALT,
    FarmerRequestOTPSerializer,
    FarmerVerifyOTPSerializer,
    InviteAcceptSerializer,
    InviteSerializer,
    LoginSerializer,
    RequestOTPSerializer,
    TokenResponseSerializer,
    TwoFAVerifySerializer,
    UserSerializer,
)
from .throttles import (
    FarmerRequestOTPRateThrottle,
    LoginRateThrottle,
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

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        requires_2fa = (
            user.two_fa_enabled
            or user.role == UserRole.MANAGER
        )
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

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
        send_mail(
            'Your Login OTP',
            f'Your OTP is: {otp_code}\nIt expires in 5 minutes.',
            from_email,
            [user.email],
            fail_silently=False,
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

    def post(self, request):
        serializer = TwoFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        return _login_response(user)


class FarmerRequestOTPView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = FarmerRequestOTPSerializer
    throttle_classes = [FarmerRequestOTPRateThrottle]

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

    def post(self, request):
        serializer = FarmerVerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        return _login_response(user)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.Serializer

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


class InviteView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = InviteSerializer

    def post(self, request):
        serializer = InviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        placeholder_phone = f'pending-{uuid.uuid4().hex[:8]}'
        user = User.objects.create(
            email=serializer.validated_data['email'],
            phone_number=placeholder_phone,
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            role=serializer.validated_data['role'],
            cooperative_id=request.cooperative_id,
            is_active=False,
            must_change_password=True,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])

        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        token = signer.sign(user.email)

        invite_link = f'{request.scheme}://{request.get_host()}/api/auth/invite/accept/?token={token}'

        coop_name = user.cooperative.name if user.cooperative else 'your cooperative'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
        send_mail(
            'You\'ve been invited to Zao',
            (
                f'You have been invited to join {coop_name} '
                f'as a {user.get_role_display()}.\n\n'
                f'Click the link below to set up your account:\n{invite_link}\n\n'
                f'This link expires in 7 days.'
            ),
            from_email,
            [user.email],
            fail_silently=False,
        )

        log_audit(
            actor=request.user,
            resource_type='user_invite',
            resource_id=user.id,
            action='CREATE',
            new_value={'email': user.email, 'role': user.role},
            cooperative_id=request.cooperative_id,
        )

        return Response({
            'detail': 'Invite sent.',
            'email': user.email,
            'role': user.role,
            'expires_in_days': 7,
            'invite_link': invite_link,
        }, status=status.HTTP_201_CREATED)


class InviteAcceptView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = InviteAcceptSerializer

    def post(self, request):
        serializer = InviteAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        user.phone_number = serializer.validated_data['phone_number']
        user.set_password(serializer.validated_data['password'])
        user.is_active = True
        user.must_change_password = False
        user.save(update_fields=['phone_number', 'password', 'is_active', 'must_change_password'])

        return _login_response(user)


class TokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TokenRefreshSerializer

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token not found.'},
                status=status.HTTP_401_UNAUTHORIZED,
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
