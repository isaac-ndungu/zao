import random
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

from .models import TwoFactorOTP, User
from .serializers import (
    LOGIN_TOKEN_SALT,
    FARMER_LOGIN_TOKEN_SALT,
    FarmerRequestOTPSerializer,
    FarmerVerifyOTPSerializer,
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
        'cooperative_id': str(user.cooperative_id) if user.cooperative_id else None,
        'phone_number': user.phone_number or '',
        'must_change_password': user.must_change_password,
    }
    if user.role == UserRole.FARMER:
        farmer = getattr(user, 'farmer_profile', None)
        claims['farmer_id'] = str(farmer.id) if farmer else None
        if farmer:
            claims['memberships'] = [
                {
                    'cooperative_id': str(m.cooperative_id),
                    'member_number': m.member_number,
                    'is_active': m.is_active,
                }
                for m in farmer.memberships.all()
            ]
        else:
            claims['memberships'] = []
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

        otp_code = f'{random.randint(0, 999999):06d}'
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

        return Response({'detail': 'OTP sent to your email.'})


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

        otp_code = f'{random.randint(0, 999999):06d}'
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

        return Response({
            'login_token': login_token,
            'detail': 'OTP sent to your phone.',
        })


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
