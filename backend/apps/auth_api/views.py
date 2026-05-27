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

from .models import TwoFactorOTP
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    RequestOTPSerializer,
    TokenResponseSerializer,
    TwoFAVerifySerializer,
    UserSerializer,
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


def _login_response(user):
    refresh = RefreshToken.for_user(user)
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

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if user.role in (UserRole.MANAGER, UserRole.ACCOUNTANT, UserRole.AUDITOR):
            signer = TimestampSigner()
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

    def post(self, request):
        serializer = TwoFAVerifySerializer(data=request.data)
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


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
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
