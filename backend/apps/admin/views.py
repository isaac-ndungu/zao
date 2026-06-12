from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from apps.base.models import AuditAction, AuditLog
from apps.base.throttles import SuperAdminSensitiveThrottle
from apps.base.constants import UserRole
from apps.base.utils import log_audit
from apps.cooperatives.models import Cooperative
from apps.deliveries.models import Delivery
from apps.disbursement.models import DisbursementBatch
from apps.farmers.models import Farmer
from apps.payment_engine.models import PaymentCycle

from .mixins import ModelAdminMixin
from .permissions import IsSuperUser
from .serializers import (
    AdminCooperativeActivateSerializer,
    AdminCooperativeDeactivateSerializer,
    AdminCooperativeSerializer,
    AdminDashboardSerializer,
    AdminUserActivateSerializer,
    AdminUserDeactivateSerializer,
    AdminUserResetPasswordSerializer,
    AdminUserSerializer,
    AdminUserToggle2FASerializer,
    AuditLogSerializer,
    CreateSuperUserSerializer,
    ImpersonateSerializer,
)

User = get_user_model()


class CreateSuperUserView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    throttle_classes = [SuperAdminSensitiveThrottle]
    serializer_class = CreateSuperUserSerializer

    def post(self, request):
        serializer = CreateSuperUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_audit(
            actor=request.user,
            resource_type='user',
            resource_id=user.pk,
            action=AuditAction.ADMIN_CREATE,
            new_value={'email': user.email, 'role': 'admin', 'is_superuser': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(
            AdminUserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class AdminUserViewSet(ModelAdminMixin, CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = User.objects.all().select_related('cooperative').order_by('-date_joined')
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        return self.queryset


class AdminUserActivateView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminUserActivateSerializer

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if user.is_active:
            return Response({'detail': 'User is already active.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = True
        user.save(update_fields=['is_active'])
        log_audit(
            actor=request.user, resource_type='user', resource_id=user.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'is_active': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'User activated.'})


class AdminUserDeactivateView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminUserDeactivateSerializer

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user.is_active:
            return Response({'detail': 'User is already inactive.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_superuser:
            return Response({'detail': 'Cannot deactivate a superuser.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=['is_active'])
        log_audit(
            actor=request.user, resource_type='user', resource_id=user.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'is_active': False},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'User deactivated.'})


class AdminUserResetPasswordView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminUserResetPasswordSerializer

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUserResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        new_password = result['new_password']
        user.set_password(new_password)
        user.must_change_password = True
        user.save(update_fields=['password', 'must_change_password'])
        email_sent = False
        try:
            send_mail(
                'Password Reset',
                f'Your password has been reset by an administrator.\n\n'
                f'New password: {new_password}\n\n'
                f'Please change your password after logging in.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
            email_sent = True
        except Exception:
            pass
        log_audit(
            actor=request.user, resource_type='user', resource_id=user.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'password_reset': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({
            'detail': 'Password reset.',
            'email_sent': email_sent,
            'temp_password': new_password if not email_sent else None,
        })


class AdminUserToggle2FAView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminUserToggle2FASerializer

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        user.two_fa_enabled = not user.two_fa_enabled
        user.save(update_fields=['two_fa_enabled'])
        log_audit(
            actor=request.user, resource_type='user', resource_id=user.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'two_fa_enabled': user.two_fa_enabled},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': '2FA toggled.', 'two_fa_enabled': user.two_fa_enabled})


class AdminUserForceLogoutView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        tokens = OutstandingToken.objects.filter(user=user)
        count = 0
        for token in tokens:
            _, created = BlacklistedToken.objects.get_or_create(token=token)
            if created:
                count += 1
        log_audit(
            actor=request.user, resource_type='user', resource_id=user.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'tokens_blacklisted': count},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': f'{count} tokens blacklisted.', 'tokens_blacklisted': count})


class ImpersonateView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    throttle_classes = [SuperAdminSensitiveThrottle]
    serializer_class = ImpersonateSerializer

    def post(self, request, user_id):
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not target.is_active:
            return Response({'detail': 'Cannot impersonate an inactive user.'}, status=status.HTTP_400_BAD_REQUEST)
        refresh = RefreshToken.for_user(target)
        access = refresh.access_token
        access['exp'] = int((timezone.now() + timedelta(minutes=15)).timestamp())
        access['is_impersonated'] = True
        access['impersonated_by'] = str(request.user.id)
        log_audit(
            actor=request.user, resource_type='user', resource_id=target.pk,
            action=AuditAction.IMPERSONATE,
            new_value={'impersonated_user': target.email, 'role': target.role},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({
            'access_token': str(access),
            'expires_in': 900,
            'is_impersonated': True,
            'user_id': str(target.pk),
            'role': target.role or '',
            'cooperative_id': str(target.cooperative_id) if target.cooperative_id else None,
        })


class AdminCooperativeViewSet(ModelAdminMixin, CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Cooperative.objects.all().order_by('name')
    serializer_class = AdminCooperativeSerializer

    def get_queryset(self):
        return self.queryset


class AdminCooperativeActivateView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminCooperativeActivateSerializer

    def post(self, request, pk):
        try:
            coop = Cooperative.objects.get(pk=pk)
        except Cooperative.DoesNotExist:
            return Response({'detail': 'Cooperative not found.'}, status=status.HTTP_404_NOT_FOUND)
        if coop.is_active:
            return Response({'detail': 'Cooperative is already active.'}, status=status.HTTP_400_BAD_REQUEST)
        coop.is_active = True
        coop.save(update_fields=['is_active'])
        log_audit(
            actor=request.user, resource_type='cooperative', resource_id=coop.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'is_active': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Cooperative activated.'})


class AdminCooperativeDeactivateView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminCooperativeDeactivateSerializer

    def post(self, request, pk):
        try:
            coop = Cooperative.objects.get(pk=pk)
        except Cooperative.DoesNotExist:
            return Response({'detail': 'Cooperative not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not coop.is_active:
            return Response({'detail': 'Cooperative is already inactive.'}, status=status.HTTP_400_BAD_REQUEST)
        coop.is_active = False
        coop.save(update_fields=['is_active'])
        log_audit(
            actor=request.user, resource_type='cooperative', resource_id=coop.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'is_active': False},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Cooperative deactivated.'})


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminDashboardSerializer

    def get(self, request):
        users = User.objects.all()
        users_by_role = {}
        for role_choice in UserRole.values:
            users_by_role[role_choice] = users.filter(role=role_choice).count()

        deliveries = Delivery.objects.all()
        deliveries_by_status = {}
        for status_choice in ['PENDING', 'GRADED', 'ACCEPTED', 'REJECTED', 'PAID']:
            deliveries_by_status[status_choice] = deliveries.filter(status=status_choice).count()

        cycles = PaymentCycle.objects.all()
        cycles_by_status = {}
        for status_choice in ['DRAFT', 'COMPUTING', 'COMPUTED', 'LOCKED', 'DISBURSED']:
            cycles_by_status[status_choice] = cycles.filter(status=status_choice).count()

        batches = DisbursementBatch.objects.all()
        batches_by_status = {}
        for status_choice in ['PENDING', 'PROCESSING', 'COMPLETED', 'PARTIALLY_COMPLETED', 'FAILED']:
            batches_by_status[status_choice] = batches.filter(status=status_choice).count()

        data = {
            'total_users': users.count(),
            'users_by_role': users_by_role,
            'total_cooperatives': Cooperative.objects.count(),
            'total_farmers': Farmer.objects.count(),
            'total_deliveries': deliveries.count(),
            'deliveries_by_status': deliveries_by_status,
            'total_payment_cycles': cycles.count(),
            'cycles_by_status': cycles_by_status,
            'total_disbursement_batches': batches.count(),
            'batches_by_status': batches_by_status,
            'total_audit_logs': AuditLog.objects.count(),
        }
        return Response(data)


class AdminAuditLogView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AuditLogSerializer

    def get(self, request):
        logs = AuditLog.objects.select_related('actor').order_by('-created_at')[:200]
        return Response(AuditLogSerializer(logs, many=True).data)


class AdminHealthView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    def get(self, request):
        db_ok = False
        redis_ok = False
        try:
            Cooperative.objects.exists()
            db_ok = True
        except Exception:
            pass
        try:
            from django.core.cache import cache
            cache.set('admin_health', 'ok', 1)
            redis_ok = cache.get('admin_health') == 'ok'
        except Exception:
            pass
        celery_ok = False
        worker_count = 0
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats() or {}
            worker_count = len(stats)
            celery_ok = worker_count > 0
        except Exception:
            pass
        return Response({
            'db': db_ok,
            'redis': redis_ok,
            'celery': celery_ok,
            'worker_count': worker_count,
        })


class AdminCeleryTasksView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    def get(self, request):
        result = {'active': [], 'reserved': [], 'scheduled': [], 'failed': []}
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            scheduled = inspect.scheduled() or {}
            for worker, tasks in active.items():
                result['active'].extend(tasks)
            for worker, tasks in reserved.items():
                result['reserved'].extend(tasks)
            for worker, tasks in scheduled.items():
                result['scheduled'].extend(tasks)
        except Exception:
            pass
        return Response({
            'active_count': len(result['active']),
            'reserved_count': len(result['reserved']),
            'scheduled_count': len(result['scheduled']),
        })
