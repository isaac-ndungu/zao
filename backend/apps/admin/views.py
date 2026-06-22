import uuid
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.signing import TimestampSigner
from django.db import connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ViewSet
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from apps.auth_api.models import TwoFactorOTP
from apps.auth_api.serializers import INVITE_TOKEN_SALT
from apps.analytics.cache import get_cached_analytics, record_access, set_cached_analytics
from apps.analytics.queries.admin import (
    get_admin_dashboard,
    get_admin_disbursements,
    get_admin_farmers,
    get_admin_farmer_retention,
    get_admin_financial,
    get_admin_loans,
    get_admin_operations,
    get_admin_payment_efficiency,
    get_admin_production,
    get_admin_sales,
    get_admin_seasonal,
)
from apps.analytics.serializers import AnalyticsQuerySerializer, AnalyticsResponseSerializer
from apps.analytics.throttles import AnalyticsAdminThrottle
from apps.base.constants import UserRole, get_soft_deletable_models
from apps.base.models import AuditAction, AuditLog
from apps.base.throttles import SuperAdminSensitiveThrottle
from apps.base.utils import log_audit
from apps.cooperatives.models import Cooperative
from apps.deliveries.models import Delivery
from apps.disbursement.models import DisbursementBatch
from apps.farmers.models import Farmer
from apps.grading.models import Grade
from apps.loans.models import Loan
from apps.payment_engine.models import PaymentCycle, FarmerPayment

from .mixins import ModelAdminMixin
from .pagination import AdminPagination
from .permissions import IsSuperUser
from apps.base.idempotency import idempotent
from .serializers import (
    AdminBinSummarySerializer,
    AdminCooperativeActivateSerializer,
    AdminCooperativeDeactivateSerializer,
    AdminCooperativeSerializer,
    AdminInviteListSerializer,
    AdminInviteResendSerializer,
    AdminInviteRevokeSerializer,
    AdminInviteSerializer,
    AdminDashboardSerializer,
    AdminDeliverySerializer,
    AdminDeliveryAssignGradeSerializer,
    AdminDisbursementBatchSerializer,
    AdminFarmerPaymentHoldSerializer,
    AdminFarmerPaymentSerializer,
    AdminFarmerSerializer,
    AdminForceDeliveryStatusSerializer,
    AdminLoanSerializer,
    AdminOTPTokenSerializer,
    AdminPaymentCycleSerializer,
    AdminPurgeConfirmSerializer,
    AdminRestoreConfirmSerializer,
    AdminSoftDeleteConfirmSerializer,
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

    @idempotent()
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
    search_fields = ['email', 'phone_number', 'first_name', 'last_name']

    @idempotent()
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        include_trashed = self.request.query_params.get('include_trashed', '').lower() == 'true'
        qs = User.objects.all_with_trashed().select_related('cooperative').order_by('-date_joined') if include_trashed else self.queryset
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        cooperative = self.request.query_params.get('cooperative')
        if cooperative:
            qs = qs.filter(cooperative_id=cooperative)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs

    def perform_destroy(self, instance):
        if instance.is_superuser:
            raise PermissionDenied('Cannot delete a superuser.')
        super().perform_destroy(instance)


class AdminUserActivateView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminUserActivateSerializer

    @idempotent()
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
        return Response({'detail': 'User activated.', 'is_active': True})


class AdminUserDeactivateView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminUserDeactivateSerializer

    @idempotent()
    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user.is_active:
            return Response({'detail': 'User is already inactive.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_superuser:
            return Response({'detail': 'Cannot deactivate a superuser.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = AdminUserDeactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notify = serializer.validated_data.get('notify', True)
        user.is_active = False
        user.save(update_fields=['is_active'])
        if notify:
            try:
                send_mail(
                    'Account Deactivated',
                    f'Your account ({user.email}) has been deactivated by an administrator.\n\n'
                    f'If you believe this is an error, please contact support@zao.app.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
            except Exception:
                pass
        log_audit(
            actor=request.user, resource_type='user', resource_id=user.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'is_active': False, 'notify': notify},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'User deactivated.', 'is_active': False, 'notify': notify})


class AdminUserResetPasswordView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminUserResetPasswordSerializer

    @idempotent()
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

    @idempotent()
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

    @idempotent()
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


class AdminBinSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminBinSummarySerializer

    def get(self, request):
        data = {}
        for model_cls in get_soft_deletable_models():
            mgr = model_cls.objects
            if hasattr(mgr, 'trashed_only'):
                qs = mgr.trashed_only()
            else:
                qs = mgr.filter(deleted_at__isnull=False)
            label = model_cls.__name__.lower()
            data[label] = qs.count()
        return Response(data)


class AdminUserBinView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminUserSerializer

    def get(self, request):
        qs = User.objects.trashed_only().select_related('cooperative').order_by('-deleted_at')
        role = request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return Response(AdminUserSerializer(qs[:200], many=True).data)


class AdminUserDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminSoftDeleteConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        serializer = AdminSoftDeleteConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.all_with_trashed().get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if user.deleted_at:
            return Response({'detail': 'User is already deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_superuser:
            return Response({'detail': 'Cannot delete a superuser.'}, status=status.HTTP_400_BAD_REQUEST)
        user.soft_delete()
        log_audit(
            actor=request.user, resource_type='user', resource_id=user.pk,
            action=AuditAction.ADMIN_DELETE,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'User soft-deleted.', 'deleted_at': user.deleted_at})


class AdminUserRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminRestoreConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        serializer = AdminRestoreConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.all_with_trashed().get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user.deleted_at:
            return Response({'detail': 'User is not deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        user.restore()
        log_audit(
            actor=request.user, resource_type='user', resource_id=user.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'restored': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'User restored.', 'restored_at': user.restored_at})


class AdminUserPurgeView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    throttle_classes = [SuperAdminSensitiveThrottle]
    serializer_class = AdminPurgeConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        try:
            user = User.objects.all_with_trashed().get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user.deleted_at:
            return Response({'detail': 'User is not deleted. Soft-delete first.'}, status=status.HTTP_400_BAD_REQUEST)
        user.hard_delete()
        log_audit(
            actor=request.user, resource_type='user', resource_id=pk,
            action=AuditAction.ADMIN_PURGE,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'User permanently purged.'})


class ImpersonateView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    throttle_classes = [SuperAdminSensitiveThrottle]
    serializer_class = ImpersonateSerializer

    @idempotent()
    def post(self, request, user_id):
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not target.is_active:
            return Response({'detail': 'Cannot impersonate an inactive user.'}, status=status.HTTP_400_BAD_REQUEST)
        if target.is_superuser:
            return Response({'detail': 'Cannot impersonate a superuser.'}, status=status.HTTP_403_FORBIDDEN)
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
    search_fields = ['name', 'registration_number', 'county']

    @idempotent()
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        include_trashed = self.request.query_params.get('include_trashed', '').lower() == 'true'
        qs = Cooperative.objects.all_with_trashed().order_by('name') if include_trashed else self.queryset
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        county = self.request.query_params.get('county')
        if county:
            qs = qs.filter(county__icontains=county)
        return qs


class AdminCooperativeActivateView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminCooperativeActivateSerializer

    @idempotent()
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
        return Response({'detail': 'Cooperative activated.', 'is_active': True})


class AdminCooperativeDeactivateView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminCooperativeDeactivateSerializer

    @idempotent()
    def post(self, request, pk):
        try:
            coop = Cooperative.objects.get(pk=pk)
        except Cooperative.DoesNotExist:
            return Response({'detail': 'Cooperative not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not coop.is_active:
            return Response({'detail': 'Cooperative is already inactive.'}, status=status.HTTP_400_BAD_REQUEST)
        deactivate_users = request.query_params.get('deactivate_users', '').lower() == 'true'
        with transaction.atomic():
            coop.is_active = False
            coop.save(update_fields=['is_active'])
            deactivated_count = 0
            if deactivate_users:
                users = User.objects.filter(cooperative=coop, is_superuser=False, is_active=True)
                deactivated_count = users.count()
                users.update(is_active=False)
            log_audit(
                actor=request.user, resource_type='cooperative', resource_id=coop.pk,
                action=AuditAction.ADMIN_ACTION,
                new_value={'is_active': False, 'deactivated_users': deactivated_count},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        return Response({
            'detail': 'Cooperative deactivated.',
            'is_active': False,
            'deactivated_users': deactivated_count,
        })


class AdminCooperativeBinView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminCooperativeSerializer

    def get(self, request):
        qs = Cooperative.objects.trashed_only().order_by('-deleted_at')
        return Response(AdminCooperativeSerializer(qs[:200], many=True).data)


class AdminCooperativeDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminSoftDeleteConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        serializer = AdminSoftDeleteConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            coop = Cooperative.objects.all_with_trashed().get(pk=pk)
        except Cooperative.DoesNotExist:
            return Response({'detail': 'Cooperative not found.'}, status=status.HTTP_404_NOT_FOUND)
        if coop.deleted_at:
            return Response({'detail': 'Cooperative is already deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        coop.delete()
        log_audit(
            actor=request.user, resource_type='cooperative', resource_id=coop.pk,
            action=AuditAction.ADMIN_DELETE,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Cooperative soft-deleted.', 'deleted_at': coop.deleted_at})


class AdminCooperativeRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminRestoreConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        serializer = AdminRestoreConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            coop = Cooperative.objects.all_with_trashed().get(pk=pk)
        except Cooperative.DoesNotExist:
            return Response({'detail': 'Cooperative not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not coop.deleted_at:
            return Response({'detail': 'Cooperative is not deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        coop.restore()
        log_audit(
            actor=request.user, resource_type='cooperative', resource_id=coop.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'restored': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Cooperative restored.', 'restored_at': coop.restored_at})


class AdminCooperativePurgeView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    throttle_classes = [SuperAdminSensitiveThrottle]
    serializer_class = AdminPurgeConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        try:
            coop = Cooperative.objects.all_with_trashed().get(pk=pk)
        except Cooperative.DoesNotExist:
            return Response({'detail': 'Cooperative not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not coop.deleted_at:
            return Response({'detail': 'Cooperative is not deleted. Soft-delete first.'}, status=status.HTTP_400_BAD_REQUEST)
        coop.hard_delete()
        log_audit(
            actor=request.user, resource_type='cooperative', resource_id=pk,
            action=AuditAction.ADMIN_PURGE,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Cooperative permanently purged.'})


class AdminFarmerBinView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminFarmerSerializer

    def get(self, request):
        qs = Farmer.objects.trashed_only().select_related('cooperative').order_by('-deleted_at')
        return Response(AdminFarmerSerializer(qs[:200], many=True).data)


class AdminFarmerRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminRestoreConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        serializer = AdminRestoreConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            farmer = Farmer.objects.all_with_trashed().get(pk=pk)
        except Farmer.DoesNotExist:
            return Response({'detail': 'Farmer not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not farmer.deleted_at:
            return Response({'detail': 'Farmer is not deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        farmer.restore()
        log_audit(
            actor=request.user, resource_type='farmer', resource_id=farmer.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'restored': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Farmer restored.', 'restored_at': farmer.restored_at})


class AdminDeliveryBinView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminDeliverySerializer

    def get(self, request):
        qs = Delivery.objects.trashed_only().select_related(
            'cooperative', 'farmer', 'grader',
        ).order_by('-deleted_at')
        return Response(AdminDeliverySerializer(qs[:200], many=True).data)


class AdminDeliveryRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminRestoreConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        serializer = AdminRestoreConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            delivery = Delivery.objects.all_with_trashed().get(pk=pk)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Delivery not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not delivery.deleted_at:
            return Response({'detail': 'Delivery is not deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        delivery.restore()
        log_audit(
            actor=request.user, resource_type='delivery', resource_id=delivery.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'restored': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Delivery restored.', 'restored_at': delivery.restored_at})


class AdminDeliveryPurgeView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    throttle_classes = [SuperAdminSensitiveThrottle]
    serializer_class = AdminPurgeConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        try:
            delivery = Delivery.objects.all_with_trashed().get(pk=pk)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Delivery not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not delivery.deleted_at:
            return Response({'detail': 'Delivery is not deleted. Soft-delete first.'}, status=status.HTTP_400_BAD_REQUEST)
        if hasattr(delivery, 'grade_record') and delivery.grade_record is not None:
            return Response(
                {'detail': 'Cannot purge a graded delivery. Delete the grade record first.'},
                status=status.HTTP_409_CONFLICT,
            )
        delivery.hard_delete()
        log_audit(
            actor=request.user, resource_type='delivery', resource_id=pk,
            action=AuditAction.ADMIN_PURGE,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Delivery permanently purged.'})


class AdminLoanBinView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminLoanSerializer

    def get(self, request):
        qs = Loan.objects.trashed_only().select_related(
            'cooperative', 'farmer',
        ).order_by('-deleted_at')
        return Response(AdminLoanSerializer(qs[:200], many=True).data)


class AdminLoanRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminRestoreConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        serializer = AdminRestoreConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            loan = Loan.objects.all_with_trashed().get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not loan.deleted_at:
            return Response({'detail': 'Loan is not deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.restore()
        log_audit(
            actor=request.user, resource_type='loan', resource_id=loan.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'restored': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Loan restored.', 'restored_at': loan.restored_at})


class AdminLoanPurgeView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    throttle_classes = [SuperAdminSensitiveThrottle]
    serializer_class = AdminPurgeConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        try:
            loan = Loan.objects.all_with_trashed().get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not loan.deleted_at:
            return Response({'detail': 'Loan is not deleted. Soft-delete first.'}, status=status.HTTP_400_BAD_REQUEST)
        if loan.disbursed_at is not None or loan.repayments.exists():
            return Response(
                {'detail': 'Cannot purge a disbursed or repaid loan. It has associated financial records.'},
                status=status.HTTP_409_CONFLICT,
            )
        loan.hard_delete()
        log_audit(
            actor=request.user, resource_type='loan', resource_id=pk,
            action=AuditAction.ADMIN_PURGE,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Loan permanently purged.'})


class AdminPaymentCycleBinView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminPaymentCycleSerializer

    def get(self, request):
        qs = PaymentCycle.objects.trashed_only().select_related('cooperative').order_by('-deleted_at')
        return Response(AdminPaymentCycleSerializer(qs[:200], many=True).data)


class AdminPaymentCycleRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminRestoreConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        serializer = AdminRestoreConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cycle = PaymentCycle.objects.all_with_trashed().get(pk=pk)
        except PaymentCycle.DoesNotExist:
            return Response({'detail': 'Payment cycle not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not cycle.deleted_at:
            return Response({'detail': 'Payment cycle is not deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        cycle.restore()
        log_audit(
            actor=request.user, resource_type='payment_cycle', resource_id=cycle.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'restored': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Payment cycle restored.', 'restored_at': cycle.restored_at})


class AdminPaymentCyclePurgeView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    throttle_classes = [SuperAdminSensitiveThrottle]
    serializer_class = AdminPurgeConfirmSerializer

    @idempotent()
    def post(self, request, pk):
        try:
            cycle = PaymentCycle.objects.all_with_trashed().get(pk=pk)
        except PaymentCycle.DoesNotExist:
            return Response({'detail': 'Payment cycle not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not cycle.deleted_at:
            return Response({'detail': 'Payment cycle is not deleted. Soft-delete first.'}, status=status.HTTP_400_BAD_REQUEST)
        if cycle.farmer_payments.exists():
            return Response(
                {'detail': 'Cannot purge a payment cycle that has farmer payments. Delete farmer payments first.'},
                status=status.HTTP_409_CONFLICT,
            )
        cycle.hard_delete()
        log_audit(
            actor=request.user, resource_type='payment_cycle', resource_id=pk,
            action=AuditAction.ADMIN_PURGE,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Payment cycle permanently purged.'})


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminDashboardSerializer

    def get(self, request):
        period = request.query_params.get('period', '')

        def date_filter(days):
            return timezone.now() - timedelta(days=days)

        def count_with_period(qs, period_days=None):
            if period_days and period:
                cutoff = date_filter(period_days)
                return qs.filter(created_at__gte=cutoff).count()
            return qs.count()

        def status_counts(qs, statuses, period_days=None):
            result = {}
            for s in statuses:
                if period_days and period:
                    cutoff = date_filter(period_days)
                    result[s] = qs.filter(status=s, created_at__gte=cutoff).count()
                else:
                    result[s] = qs.filter(status=s).count()
            return result

        period_days = None
        prev_period_days = None
        if period:
            try:
                if period.endswith('d'):
                    period_days = int(period[:-1])
                elif period.endswith('h'):
                    period_days = int(period[:-1]) / 24
                prev_period_days = period_days * 2 if period_days else None
            except (ValueError, TypeError):
                pass

        now = timezone.now()
        prev_cutoff = date_filter(prev_period_days) if prev_period_days else None
        cur_cutoff = date_filter(period_days) if period_days else None

        def period_changes(current_qs, prev_qs):
            cur = current_qs.count()
            prv = prev_qs.count()
            return {
                'current': cur,
                'previous': prv,
                'change_pct': round(((cur - prv) / prv * 100), 1) if prv else None,
            }

        total_users_qs = User.objects.all()
        total_farmers_qs = Farmer.objects.all()
        total_cooperatives_qs = Cooperative.objects.all()
        total_deliveries_qs = Delivery.objects.all()
        total_cycles_qs = PaymentCycle.objects.all()
        total_batches_qs = DisbursementBatch.objects.all()

        cur_users = total_users_qs
        prv_users = User.objects.all()
        if cur_cutoff:
            cur_users = total_users_qs.filter(date_joined__gte=cur_cutoff)
        if prev_cutoff:
            prv_users = User.objects.filter(date_joined__gte=prev_cutoff, date_joined__lt=cur_cutoff)
        elif cur_cutoff:
            prv_users = User.objects.filter(date_joined__lt=cur_cutoff)

        cur_farmers = total_farmers_qs
        prv_farmers = Farmer.objects.all()
        if cur_cutoff:
            cur_farmers = total_farmers_qs.filter(date_joined__gte=cur_cutoff)
        if prev_cutoff:
            prv_farmers = Farmer.objects.filter(date_joined__gte=prev_cutoff, date_joined__lt=cur_cutoff)
        elif cur_cutoff:
            prv_farmers = Farmer.objects.filter(date_joined__lt=cur_cutoff)

        cur_deliveries = total_deliveries_qs
        prv_deliveries = Delivery.objects.all()
        if cur_cutoff:
            cur_deliveries = total_deliveries_qs.filter(date_delivered__gte=cur_cutoff)
        if prev_cutoff:
            prv_deliveries = Delivery.objects.filter(date_delivered__gte=prev_cutoff, date_delivered__lt=cur_cutoff)
        elif cur_cutoff:
            prv_deliveries = Delivery.objects.filter(date_delivered__lt=cur_cutoff)

        users_by_role = {}
        for role_choice in UserRole.values:
            users_by_role[role_choice] = cur_users.filter(role=role_choice).count()

        deliveries_by_status = {}
        for status_choice in ['PENDING', 'GRADED', 'ACCEPTED', 'REJECTED', 'PAID']:
            deliveries_by_status[status_choice] = cur_deliveries.filter(status=status_choice).count()

        cur_cycles = total_cycles_qs
        if cur_cutoff:
            cur_cycles = total_cycles_qs.filter(created_at__gte=cur_cutoff)
        cycles_by_status = {}
        for status_choice in ['DRAFT', 'COMPUTING', 'COMPUTED', 'LOCKED', 'DISBURSED']:
            cycles_by_status[status_choice] = cur_cycles.filter(status=status_choice).count()

        cur_batches = total_batches_qs
        if cur_cutoff:
            cur_batches = total_batches_qs.filter(created_at__gte=cur_cutoff)
        batches_by_status = {}
        for status_choice in ['PENDING', 'PROCESSING', 'COMPLETED', 'PARTIALLY_COMPLETED', 'FAILED']:
            batches_by_status[status_choice] = cur_batches.filter(status=status_choice).count()



        data = {
            'total_users': cur_users.count(),
            'users_by_role': users_by_role,
            'total_cooperatives': total_cooperatives_qs.count(),
            'total_farmers': cur_farmers.count(),
            'total_deliveries': cur_deliveries.count(),
            'deliveries_by_status': deliveries_by_status,
            'total_payment_cycles': total_cycles_qs.count(),
            'cycles_by_status': cycles_by_status,
            'total_disbursement_batches': total_batches_qs.count(),
            'batches_by_status': batches_by_status,
            'total_audit_logs': AuditLog.objects.count(),
            'period': period,
            'changes': {
                'users': period_changes(cur_users, prv_users),
                'farmers': period_changes(cur_farmers, prv_farmers),
                'deliveries': period_changes(cur_deliveries, prv_deliveries),
            } if period else {},
            'trash': {
                'users': User.objects.trashed_only().count(),
                'cooperatives': Cooperative.objects.trashed_only().count(),
                'farmers': Farmer.objects.trashed_only().count(),
                'deliveries': Delivery.objects.trashed_only().count(),
                'grades': Grade.objects.trashed_only().count(),
                'loans': Loan.objects.trashed_only().count(),
                'paymentcycles': PaymentCycle.objects.trashed_only().count(),
                'farmerpayments': FarmerPayment.objects.trashed_only().count(),
                'disbursementbatches': DisbursementBatch.objects.trashed_only().count(),
            },
        }
        return Response(data)


class AdminAuditLogView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AuditLogSerializer

    def get(self, request):
        qs = AuditLog.objects.select_related('actor').order_by('-created_at')
        resource_type = request.query_params.get('resource_type')
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        resource_id = request.query_params.get('resource_id')
        if resource_id:
            qs = qs.filter(resource_id=resource_id)
        action = request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)
        actor = request.query_params.get('actor')
        if actor:
            qs = qs.filter(actor_id=actor)
        limit = request.query_params.get('limit', '200')
        try:
            limit = int(limit)
        except ValueError:
            limit = 200
        return Response(AuditLogSerializer(qs[:limit], many=True).data)


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
                for t in tasks:
                    result['active'].append({
                        'task_name': t.get('name'),
                        'task_id': t.get('id'),
                        'args': str(t.get('args', '')),
                        'kwargs': str(t.get('kwargs', '')),
                        'worker': worker,
                        'started': t.get('time_start'),
                    })
            for worker, tasks in reserved.items():
                for t in tasks:
                    result['reserved'].append({
                        'task_name': t.get('name'),
                        'task_id': t.get('id'),
                        'args': str(t.get('args', '')),
                        'kwargs': str(t.get('kwargs', '')),
                        'worker': worker,
                    })
            for worker, tasks in scheduled.items():
                for t in tasks:
                    result['scheduled'].append({
                        'task_name': t.get('name'),
                        'task_id': t.get('id'),
                        'args': str(t.get('args', '')),
                        'kwargs': str(t.get('kwargs', '')),
                        'worker': worker,
                        'eta': t.get('eta'),
                    })
        except Exception:
            pass
        return Response({
            'active_count': len(result['active']),
            'reserved_count': len(result['reserved']),
            'scheduled_count': len(result['scheduled']),
            'tasks': result,
        })


class RevokeAllSessionsView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request):
        tokens = OutstandingToken.objects.filter(user=request.user)
        count = 0
        for token in tokens:
            _, created = BlacklistedToken.objects.get_or_create(token=token)
            if created:
                count += 1
        return Response({
            'detail': f'{count} sessions revoked.',
            'tokens_blacklisted': count,
        })


class AdminFarmerViewSet(ModelAdminMixin, ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Farmer.objects.all().select_related('cooperative').order_by('-date_joined')
    serializer_class = AdminFarmerSerializer
    search_fields = ['first_name', 'last_name', 'id_number', 'phone_number', 'email']

    @idempotent()
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        include_trashed = self.request.query_params.get('include_trashed', '').lower() == 'true'
        qs = Farmer.objects.all_with_trashed().select_related('cooperative').order_by('-date_joined') if include_trashed else self.queryset
        coop = self.request.query_params.get('cooperative')
        if coop:
            qs = qs.filter(cooperative_id=coop)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs


class AdminDeliveryViewSet(ModelAdminMixin, ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    queryset = Delivery.objects.all().select_related('farmer', 'grader', 'cooperative').order_by('-date_delivered')
    search_fields = ['batch_id', 'farmer__first_name', 'farmer__last_name', 'farmer__phone_number']

    def get_serializer_class(self):
        if self.action == 'create':
            from .serializers import AdminDeliveryCreateSerializer
            return AdminDeliveryCreateSerializer
        return AdminDeliverySerializer

    def get_queryset(self):
        include_trashed = self.request.query_params.get('include_trashed', '').lower() == 'true'
        qs = Delivery.objects.all_with_trashed().select_related('farmer', 'grader', 'cooperative').order_by('-date_delivered') if include_trashed else self.queryset
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        coop = self.request.query_params.get('cooperative')
        if coop:
            qs = qs.filter(cooperative_id=coop)
        product_type = self.request.query_params.get('product_type')
        if product_type:
            qs = qs.filter(product_type=product_type)
        return qs

    def perform_create(self, serializer):
        serializer.save(cooperative=serializer.validated_data['farmer'].cooperative)


class AdminDeliveryForceStatusView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminForceDeliveryStatusSerializer

    @idempotent()
    def post(self, request, pk):
        try:
            delivery = Delivery.objects.get(pk=pk)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Delivery not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminForceDeliveryStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        old_status = delivery.status
        delivery.status = new_status
        delivery.save(update_fields=['status'])
        log_audit(
            actor=request.user, resource_type='delivery', resource_id=delivery.pk,
            action=AuditAction.FORCE_STATUS,
            previous_value={'status': old_status},
            new_value={'status': new_status},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Delivery status updated.', 'status': new_status})


class AdminDeliveryAssignGradeView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminDeliveryAssignGradeSerializer

    @idempotent()
    def post(self, request, pk):
        from django.utils import timezone
        from apps.grading.models import Grade
        from apps.grading.views import update_delivery_from_grade
        from apps.grading.tasks import update_inventory_on_grade

        try:
            delivery = Delivery.objects.select_related('cooperative').get(pk=pk)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Delivery not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminDeliveryAssignGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        grade, created = Grade.objects.get_or_create(
            delivery=delivery,
            defaults={'cooperative': delivery.cooperative},
        )

        was_rejected = bool(grade.rejection_reason)

        grade.grade_letter = serializer.validated_data.get('grade_letter', grade.grade_letter)
        grade.price_per_unit = serializer.validated_data.get('price_per_unit', grade.price_per_unit)
        grade.rejection_reason = serializer.validated_data.get('rejection_reason', grade.rejection_reason)
        grade.is_overridden = True
        grade.overridden_by = request.user
        grade.overridden_at = timezone.now()
        grade.override_reason = serializer.validated_data.get('override_reason', '')
        grade.is_inventory_updated = False
        grade.save()

        if not created and was_rejected != bool(grade.rejection_reason):
            from apps.grading.views import _reverse_inventory_contribution
            _reverse_inventory_contribution(delivery, was_rejected)

        update_delivery_from_grade(grade)
        update_inventory_on_grade.delay(str(grade.id))

        log_audit(
            actor=request.user, resource_type='delivery', resource_id=delivery.pk,
            action='ASSIGN_GRADE',
            previous_value={'status': delivery.status, 'grade': delivery.grade},
            new_value={
                'grade_letter': grade.grade_letter,
                'price_per_unit': str(grade.price_per_unit),
                'rejection_reason': grade.rejection_reason,
                'is_override': True,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Grade assigned.', 'grade_id': str(grade.id), 'created': created})


class AdminPaymentCycleViewSet(ModelAdminMixin, ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    queryset = PaymentCycle.objects.all().select_related('cooperative', 'locked_by').order_by('-end_date')
    serializer_class = AdminPaymentCycleSerializer
    search_fields = ['name']

    @idempotent()
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        include_trashed = self.request.query_params.get('include_trashed', '').lower() == 'true'
        qs = PaymentCycle.objects.all_with_trashed().select_related('cooperative', 'locked_by').order_by('-end_date') if include_trashed else self.queryset
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        coop = self.request.query_params.get('cooperative')
        if coop:
            qs = qs.filter(cooperative_id=coop)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(status='DRAFT')
        log_audit(
            actor=self.request.user, resource_type='payment_cycle', resource_id=instance.pk,
            action=AuditAction.ADMIN_CREATE,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class AdminPaymentCycleLockView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request, pk):
        try:
            cycle = PaymentCycle.objects.get(pk=pk)
        except PaymentCycle.DoesNotExist:
            return Response({'detail': 'Payment cycle not found.'}, status=status.HTTP_404_NOT_FOUND)
        if cycle.status != 'COMPUTED':
            return Response({'detail': 'Only COMPUTED cycles can be locked.'}, status=status.HTTP_400_BAD_REQUEST)
        cycle.status = 'LOCKED'
        cycle.locked_by = request.user
        cycle.locked_at = timezone.now()
        cycle.save(update_fields=['status', 'locked_by', 'locked_at'])
        log_audit(
            actor=request.user, resource_type='payment_cycle', resource_id=cycle.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'status': 'LOCKED'},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Payment cycle locked.'})


class AdminPaymentCycleUnlockView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request, pk):
        try:
            cycle = PaymentCycle.objects.get(pk=pk)
        except PaymentCycle.DoesNotExist:
            return Response({'detail': 'Payment cycle not found.'}, status=status.HTTP_404_NOT_FOUND)
        if cycle.status != 'LOCKED':
            return Response({'detail': 'Only LOCKED cycles can be unlocked.'}, status=status.HTTP_400_BAD_REQUEST)
        cycle.status = 'COMPUTED'
        cycle.locked_by = None
        cycle.locked_at = None
        cycle.save(update_fields=['status', 'locked_by', 'locked_at'])
        log_audit(
            actor=request.user, resource_type='payment_cycle', resource_id=cycle.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'status': 'COMPUTED'},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Payment cycle unlocked.'})


class AdminDisbursementBatchViewSet(ModelAdminMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = DisbursementBatch.objects.all().select_related('cooperative', 'payment_cycle').order_by('-created_at')
    serializer_class = AdminDisbursementBatchSerializer
    search_fields = ['id', 'cooperative__name']

    def get_queryset(self):
        include_trashed = self.request.query_params.get('include_trashed', '').lower() == 'true'
        qs = DisbursementBatch.objects.all_with_trashed().select_related('cooperative', 'payment_cycle').order_by('-created_at') if include_trashed else self.queryset
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        coop = self.request.query_params.get('cooperative')
        if coop:
            qs = qs.filter(cooperative_id=coop)
        return qs


class AdminDisbursementBatchApproveView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request, pk):
        try:
            batch = DisbursementBatch.objects.get(pk=pk)
        except DisbursementBatch.DoesNotExist:
            return Response({'detail': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)
        if batch.status != 'PENDING':
            return Response({'detail': 'Only PENDING batches can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        batch.status = 'PROCESSING'
        batch.approved_by = request.user
        batch.approved_at = timezone.now()
        batch.save(update_fields=['status', 'approved_by', 'approved_at'])
        log_audit(
            actor=request.user, resource_type='disbursement_batch', resource_id=batch.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'status': 'PROCESSING'},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Batch approved.'})


class AdminDisbursementBatchRejectView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request, pk):
        try:
            batch = DisbursementBatch.objects.get(pk=pk)
        except DisbursementBatch.DoesNotExist:
            return Response({'detail': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)
        if batch.status != 'PENDING':
            return Response({'detail': 'Only PENDING batches can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)
        batch.status = 'FAILED'
        batch.save(update_fields=['status'])
        log_audit(
            actor=request.user, resource_type='disbursement_batch', resource_id=batch.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'status': 'FAILED'},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Batch rejected.'})


class AdminFarmerPaymentViewSet(ModelAdminMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = FarmerPayment.objects.all().select_related('farmer', 'cycle').order_by('-created_at')
    serializer_class = AdminFarmerPaymentSerializer
    search_fields = ['farmer__first_name', 'farmer__last_name', 'farmer__phone_number']

    def get_queryset(self):
        include_trashed = self.request.query_params.get('include_trashed', '').lower() == 'true'
        qs = FarmerPayment.objects.all_with_trashed().select_related('farmer', 'cycle').order_by('-created_at') if include_trashed else self.queryset
        cycle = self.request.query_params.get('cycle')
        if cycle:
            qs = qs.filter(cycle_id=cycle)
        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            qs = qs.filter(payment_status=payment_status)
        is_on_hold = self.request.query_params.get('is_on_hold')
        if is_on_hold is not None:
            qs = qs.filter(is_on_hold=is_on_hold.lower() == 'true')
        return qs


class AdminFarmerPaymentHoldView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminFarmerPaymentHoldSerializer

    @idempotent()
    def post(self, request, pk):
        try:
            payment = FarmerPayment.objects.get(pk=pk)
        except FarmerPayment.DoesNotExist:
            return Response({'detail': 'Payment not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminFarmerPaymentHoldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment.is_on_hold = serializer.validated_data['hold']
        payment.hold_reason = serializer.validated_data.get('reason', '')
        payment.save(update_fields=['is_on_hold', 'hold_reason'])
        log_audit(
            actor=request.user, resource_type='farmer_payment', resource_id=payment.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'is_on_hold': payment.is_on_hold},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Payment hold toggled.', 'is_on_hold': payment.is_on_hold})


class AdminLoanViewSet(ModelAdminMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Loan.objects.all().select_related('farmer', 'approved_by', 'cooperative').order_by('-created_at')
    serializer_class = AdminLoanSerializer
    search_fields = ['farmer__first_name', 'farmer__last_name']

    def get_queryset(self):
        include_trashed = self.request.query_params.get('include_trashed', '').lower() == 'true'
        qs = Loan.objects.all_with_trashed().select_related('farmer', 'approved_by', 'cooperative').order_by('-created_at') if include_trashed else self.queryset
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        farmer = self.request.query_params.get('farmer')
        if farmer:
            qs = qs.filter(farmer_id=farmer)
        return qs


class AdminLoanApproveView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request, pk):
        try:
            loan = Loan.objects.get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=status.HTTP_404_NOT_FOUND)
        if loan.status != 'PENDING':
            return Response({'detail': 'Only PENDING loans can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.status = 'ACTIVE'
        loan.approved_by = request.user
        loan.approved_at = timezone.now()
        loan.save(update_fields=['status', 'approved_by', 'approved_at'])
        log_audit(
            actor=request.user, resource_type='loan', resource_id=loan.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'status': 'ACTIVE'},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Loan approved.', 'status': 'ACTIVE'})


class AdminLoanRejectView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request, pk):
        try:
            loan = Loan.objects.get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=status.HTTP_404_NOT_FOUND)
        if loan.status != 'PENDING':
            return Response({'detail': 'Only PENDING loans can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.status = 'COMPLETED'
        loan.save(update_fields=['status'])
        log_audit(
            actor=request.user, resource_type='loan', resource_id=loan.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'status': 'COMPLETED'},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Loan rejected.', 'status': 'COMPLETED'})


class AdminLoanMarkDefaultedView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request, pk):
        try:
            loan = Loan.objects.get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=status.HTTP_404_NOT_FOUND)
        if loan.status != 'ACTIVE':
            return Response({'detail': 'Only ACTIVE loans can be marked defaulted.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.status = 'DEFAULTED'
        loan.save(update_fields=['status'])
        log_audit(
            actor=request.user, resource_type='loan', resource_id=loan.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'status': 'DEFAULTED'},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Loan marked as defaulted.', 'status': 'DEFAULTED'})


class AdminLoanMarkCompletedView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request, pk):
        try:
            loan = Loan.objects.get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=status.HTTP_404_NOT_FOUND)
        if loan.status not in ('ACTIVE', 'DEFAULTED'):
            return Response({'detail': 'Only ACTIVE or DEFAULTED loans can be marked completed.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.status = 'COMPLETED'
        loan.save(update_fields=['status'])
        log_audit(
            actor=request.user, resource_type='loan', resource_id=loan.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'status': 'COMPLETED'},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Loan marked as completed.', 'status': 'COMPLETED'})


class AdminInviteView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminInviteSerializer

    @idempotent()
    def post(self, request):
        serializer = AdminInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        placeholder_phone = f'pending-{uuid.uuid4().hex[:8]}'
        user = User.objects.create(
            email=serializer.validated_data['email'],
            phone_number=placeholder_phone,
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            role=UserRole.MANAGER,
            is_active=False,
            must_change_password=True,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])

        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        try:
            host = request.get_host()
        except Exception:
            host = 'localhost'
        invite_link = f'{request.scheme}://{host}/api/auth/invite/verify/'

        otp_code = f'{secrets.randbelow(1_000_000):06d}'
        expires_at = timezone.now() + timedelta(minutes=10)

        TwoFactorOTP.objects.create(
            user=user,
            otp_code=otp_code,
            purpose='ACTION_CONFIRM',
            expires_at=expires_at,
        )

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
        send_mail(
            'You\'ve been invited to Zao',
            (
                'You have been invited to join as a Manager.\n\n'
                f'Your invite code is: {otp_code}\n'
                f'It expires in 10 minutes.\n\n'
                f'Or click the link below:\n{invite_link}\n\n'
                f'This invite expires in 7 days.'
            ),
            from_email,
            [user.email],
            fail_silently=False,
        )

        log_audit(
            actor=request.user,
            resource_type='user_invite',
            resource_id=user.id,
            action=AuditAction.ADMIN_CREATE,
            new_value={'email': user.email, 'role': user.role},
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return Response({
            'detail': 'Invite sent.',
            'email': user.email,
            'role': user.role,
            'invite_token': invite_token,
            'expires_in_days': 7,
        }, status=status.HTTP_201_CREATED)


class AdminInviteRevokeView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminInviteRevokeSerializer

    @idempotent()
    def post(self, request, pk):
        serializer = AdminInviteRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.is_active:
            return Response(
                {'detail': 'Cannot revoke an accepted invite.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.invite_revoked:
            user.invite_revoked = True
            user.save(update_fields=['invite_revoked'])

        TwoFactorOTP.objects.filter(
            user=user,
            purpose='ACTION_CONFIRM',
            is_used=False,
        ).delete()

        log_audit(
            actor=request.user,
            resource_type='user_invite',
            resource_id=user.id,
            action=AuditAction.ADMIN_ACTION,
            new_value={'invite_revoked': True, 'otps_cleared': True},
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return Response({'detail': 'Invite revoked.'})


class AdminInviteListView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminInviteListSerializer

    def get(self, request):
        qs = User.objects.filter(phone_number__startswith='pending-').order_by('-date_joined')

        status_filter = request.query_params.get('status')
        if status_filter:
            if status_filter == 'PENDING':
                qs = qs.filter(is_active=False, invite_revoked=False)
            elif status_filter == 'ACCEPTED':
                qs = qs.filter(is_active=True)
            elif status_filter == 'REVOKED':
                qs = qs.filter(invite_revoked=True)

        role = request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)

        email = request.query_params.get('email')
        if email:
            qs = qs.filter(email__icontains=email)

        paginator = AdminPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = AdminInviteListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AdminInviteListSerializer(qs[:200], many=True)
        return Response(serializer.data)


class AdminInviteDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminInviteListSerializer

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk, phone_number__startswith='pending-')
        except User.DoesNotExist:
            return Response({'detail': 'Invite not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(AdminInviteListSerializer(user).data)


class AdminInviteResendView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminInviteResendSerializer

    @idempotent()
    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk, is_active=False)
        except User.DoesNotExist:
            return Response({'detail': 'Invite not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.invite_revoked:
            return Response(
                {'detail': 'Cannot resend a revoked invite.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_code = f'{secrets.randbelow(1_000_000):06d}'
        expires_at = timezone.now() + timedelta(minutes=10)

        TwoFactorOTP.objects.create(
            user=user,
            otp_code=otp_code,
            purpose='ACTION_CONFIRM',
            expires_at=expires_at,
        )

        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        try:
            host = request.get_host()
        except Exception:
            host = 'localhost'
        invite_link = f'{request.scheme}://{host}/api/auth/invite/verify/'

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
        send_mail(
            'You\'ve been invited to Zao',
            (
                'You have been invited to join as a Manager.\n\n'
                f'Your invite code is: {otp_code}\n'
                f'It expires in 10 minutes.\n\n'
                f'Or click the link below:\n{invite_link}\n\n'
                f'This invite expires in 7 days.'
            ),
            from_email,
            [user.email],
            fail_silently=False,
        )

        log_audit(
            actor=request.user,
            resource_type='user_invite',
            resource_id=user.id,
            action=AuditAction.ADMIN_ACTION,
            new_value={'resend': True, 'email': user.email},
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return Response({'detail': 'Invite resent.', 'invite_token': invite_token})


class AdminOTPTokenView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminOTPTokenSerializer

    def get(self, request):
        qs = TwoFactorOTP.objects.all().select_related('user').order_by('-created_at')
        user_id = request.query_params.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)
        purpose = request.query_params.get('purpose')
        if purpose:
            qs = qs.filter(purpose=purpose)
        is_used = request.query_params.get('is_used')
        if is_used is not None:
            qs = qs.filter(is_used=is_used.lower() == 'true')
        return Response(AdminOTPTokenSerializer(qs[:100], many=True).data)


class AdminOTPTokenInvalidateAllView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        count = TwoFactorOTP.objects.filter(user=user, is_used=False).update(is_used=True)
        log_audit(
            actor=request.user, resource_type='user', resource_id=user.pk,
            action=AuditAction.ADMIN_ACTION,
            new_value={'otp_invalidated': count},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': f'{count} pending OTPs invalidated.', 'invalidated_count': count})


class AdminMigrationHealthView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    def get(self, request):
        executor = MigrationExecutor(connections['default'])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        return Response({
            'unapplied_migrations': [
                f'{migration.app_label}.{migration.name}'
                for migration, _ in plan
            ],
            'count': len(plan),
            'up_to_date': len(plan) == 0,
        })


class AdminUserBulkActionView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request):
        action = request.data.get('action')
        ids = request.data.get('ids', [])
        if action not in ('activate', 'deactivate'):
            return Response({'detail': 'Invalid action. Use activate or deactivate.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ids:
            return Response({'detail': 'No IDs provided.'}, status=status.HTTP_400_BAD_REQUEST)
        users = User.objects.filter(id__in=ids)
        if action == 'activate':
            users = users.exclude(is_active=True)
            count = users.count()
            users.update(is_active=True)
        else:
            users = users.filter(is_superuser=False).exclude(is_active=False)
            count = users.count()
            users.update(is_active=False)
        log_audit(
            actor=request.user, resource_type='user', resource_id=None,
            action=AuditAction.ADMIN_ACTION,
            new_value={'action': action, 'count': count},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': f'{count} users {action}d.', 'count': count})


class AdminCooperativeBulkActionView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request):
        action = request.data.get('action')
        ids = request.data.get('ids', [])
        if action not in ('activate', 'deactivate'):
            return Response({'detail': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ids:
            return Response({'detail': 'No IDs provided.'}, status=status.HTTP_400_BAD_REQUEST)
        coops = Cooperative.objects.filter(id__in=ids)
        if action == 'activate':
            coops = coops.exclude(is_active=True)
            count = coops.count()
            coops.update(is_active=True)
        else:
            coops = coops.exclude(is_active=False)
            count = coops.count()
            coops.update(is_active=False)
        log_audit(
            actor=request.user, resource_type='cooperative', resource_id=None,
            action=AuditAction.ADMIN_ACTION,
            new_value={'action': action, 'count': count},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': f'{count} cooperatives {action}d.', 'count': count})


class AdminFarmerBulkActionView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = serializers.Serializer

    @idempotent()
    def post(self, request):
        action = request.data.get('action')
        ids = request.data.get('ids', [])
        if action not in ('activate', 'deactivate'):
            return Response({'detail': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ids:
            return Response({'detail': 'No IDs provided.'}, status=status.HTTP_400_BAD_REQUEST)
        farmers = Farmer.objects.filter(id__in=ids)
        if action == 'activate':
            farmers = farmers.exclude(is_active=True)
            count = farmers.count()
            farmers.update(is_active=True)
        else:
            farmers = farmers.exclude(is_active=False)
            count = farmers.count()
            farmers.update(is_active=False)
        log_audit(
            actor=request.user, resource_type='farmer', resource_id=None,
            action=AuditAction.ADMIN_ACTION,
            new_value={'action': action, 'count': count},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': f'{count} farmers {action}d.', 'count': count})


class AdminAnalyticsViewSet(ViewSet):
    """Cross-cooperative analytics for superusers."""

    permission_classes = [IsAuthenticated, IsSuperUser]
    throttle_classes = [AnalyticsAdminThrottle]

    def _parse_params(self):
        serializer = AnalyticsQuerySerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        from apps.analytics.queries.common import parse_period
        start, end = parse_period(
            params.get('start_date'), params.get('end_date'), params.get('period'),
        )
        return {
            'start_date': start,
            'end_date': end,
            'compare_to': params.get('compare_to'),
        }

    def _cached_response(self, action_name, params, compute_fn):
        record_access(None)
        data, cache_key = get_cached_analytics(
            scope_type='global',
            cooperative_id=None,
            farmer_id=None,
            action=action_name,
            params=params,
        )
        if data is not None:
            return Response(data)
        result = compute_fn(params)
        set_cached_analytics(cache_key, result)
        return Response(result)

    def _action(self, fn):
        params = self._parse_params()
        def compute(p):
            return fn(
                start_date=p['start_date'],
                end_date=p['end_date'],
                compare_to=p.get('compare_to'),
            )
        return self._cached_response(fn.__name__.replace('get_admin_', ''), params, compute)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        return self._action(get_admin_dashboard)

    @action(detail=False, methods=['get'])
    def production(self, request):
        return self._action(get_admin_production)

    @action(detail=False, methods=['get'])
    def financial(self, request):
        return self._action(get_admin_financial)

    @action(detail=False, methods=['get'])
    def farmers(self, request):
        return self._action(get_admin_farmers)

    @action(detail=False, methods=['get'])
    def sales(self, request):
        return self._action(get_admin_sales)

    @action(detail=False, methods=['get'])
    def loans(self, request):
        return self._action(get_admin_loans)

    @action(detail=False, methods=['get'])
    def operations(self, request):
        return self._action(get_admin_operations)

    @action(detail=False, methods=['get'])
    def disbursements(self, request):
        return self._action(get_admin_disbursements)

    @action(detail=False, methods=['get'])
    def seasonal(self, request):
        return self._action(get_admin_seasonal)

    @action(detail=False, methods=['get'])
    def payment_efficiency(self, request):
        return self._action(get_admin_payment_efficiency)

    @action(detail=False, methods=['get'])
    def farmer_retention(self, request):
        return self._action(get_admin_farmer_retention)

    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """Global leaderboard (cross-cooperative)."""
        from apps.analytics.serializers import LeaderboardQuerySerializer
        from apps.analytics.queries.common import parse_period, coalesce_sum
        from apps.deliveries.models import Delivery
        from apps.payment_engine.models import FarmerPayment
        from apps.sales.models import Sale
        from django.db.models import Sum
        from django.core.cache import cache

        serializer = LeaderboardQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        _type = params.get('type', 'top_farmers_by_volume')
        limit = params.get('limit', 10)
        period = params.get('period', '30d')
        start, end = parse_period(period=period)

        redis_key = f'leaderboard:{_type}:global:{period}'
        raw = cache.zrevrange(redis_key, 0, limit - 1, withscores=True)
        if raw:
            items = [{'id': m, 'score': round(float(s), 2)} for m, s in raw]
            return Response({'type': _type, 'limit': limit, 'period': period, 'data': items, 'cached': True})

        if _type == 'top_farmers_by_volume':
            agg = list(
                Delivery.objects.filter(date_delivered__gte=start, date_delivered__lt=end)
                .values('farmer_id')
                .annotate(score=coalesce_sum(Sum('quantity_kg')))
                .order_by('-score')[:limit]
                .values_list('farmer_id', 'score')
            )
        elif _type == 'top_farmers_by_payout':
            agg = list(
                FarmerPayment.objects.filter(cycle__end_date__gte=start, cycle__start_date__lt=end)
                .values('farmer_id')
                .annotate(score=coalesce_sum(Sum('net_amount')))
                .order_by('-score')[:limit]
                .values_list('farmer_id', 'score')
            )
        elif _type == 'top_buyers':
            agg = list(
                Sale.objects.filter(status='COMPLETED', sale_date__gte=start, sale_date__lt=end)
                .values('buyer__name')
                .annotate(score=coalesce_sum(Sum('total_amount')))
                .order_by('-score')[:limit]
                .values_list('buyer__name', 'score')
            )
        else:
            return Response({'detail': 'Invalid leaderboard type.'}, status=400)

        items = [{'id': str(m) if not isinstance(m, str) else m, 'score': round(float(s), 2)} for m, s in agg]
        mapping = {item['id']: item['score'] for item in items}
        if mapping:
            cache.zadd(redis_key, mapping)
            cache.expire(redis_key, 7200)

        return Response({'type': _type, 'limit': limit, 'period': period, 'data': items})
