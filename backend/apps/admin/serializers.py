import secrets

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.auth_api.models import User, TwoFactorOTP
from apps.base.constants import UserRole
from apps.base.models import AuditLog, AuditAction
from apps.cooperatives.models import Cooperative
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.disbursement.models import DisbursementBatch
from apps.farmers.models import Farmer
from apps.loans.models import Loan
from apps.payment_engine.models import PaymentCycle, FarmerPayment

User = get_user_model()


class CreateSuperUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('A user with this phone number already exists.')
        return value

    def create(self, validated_data):
        return User.objects.create_superuser(**validated_data)


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'role', 'cooperative', 'is_active', 'is_staff', 'is_superuser',
            'two_fa_enabled', 'must_change_password', 'date_joined', 'last_login',
            'deleted_at', 'restored_at',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'is_superuser', 'deleted_at', 'restored_at']

    def validate_email(self, value):
        instance = self.instance
        qs = User.objects.filter(email=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_phone_number(self, value):
        instance = self.instance
        qs = User.objects.filter(phone_number=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A user with this phone number already exists.')
        return value


class AdminUserActivateSerializer(serializers.Serializer):
    pass

class AdminUserDeactivateSerializer(serializers.Serializer):
    notify = serializers.BooleanField(default=True)

class AdminUserToggle2FASerializer(serializers.Serializer):
    pass


class AdminUserResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8, required=False, allow_blank=True)

    def create(self, validated_data):
        password = validated_data.get('new_password') or secrets.token_urlsafe(12)
        return {'new_password': password}


class AdminCooperativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cooperative
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_member_sequence', 'last_delivery_sequence', 'deleted_at', 'restored_at']


class AdminCooperativeActivateSerializer(serializers.Serializer):
    pass


class AdminCooperativeDeactivateSerializer(serializers.Serializer):
    pass


class AdminDashboardSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    users_by_role = serializers.DictField(child=serializers.IntegerField())
    total_cooperatives = serializers.IntegerField()
    total_farmers = serializers.IntegerField()
    total_deliveries = serializers.IntegerField()
    deliveries_by_status = serializers.DictField(child=serializers.IntegerField())
    total_payment_cycles = serializers.IntegerField()
    cycles_by_status = serializers.DictField(child=serializers.IntegerField())
    total_disbursement_batches = serializers.IntegerField()
    batches_by_status = serializers.DictField(child=serializers.IntegerField())
    total_audit_logs = serializers.IntegerField()
    period = serializers.CharField(required=False, allow_blank=True)
    changes = serializers.DictField(child=serializers.FloatField(), required=False)
    trash = serializers.DictField(child=serializers.IntegerField(), required=False)


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'


class ImpersonateSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    expires_in = serializers.IntegerField()
    is_impersonated = serializers.BooleanField()
    user_id = serializers.CharField()
    role = serializers.CharField()
    cooperative_id = serializers.CharField(allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['expires_in'] = 900
        data['is_impersonated'] = True
        return data


class AdminFarmerSerializer(serializers.ModelSerializer):
    primary_membership = serializers.SerializerMethodField()

    class Meta:
        model = Farmer
        fields = [
            'id', 'user', 'first_name', 'last_name', 'email', 'id_number',
            'phone_number', 'date_of_birth', 'county', 'sub_county', 'ward',
            'village', 'is_active', 'has_active_loan', 'date_joined', 'updated_at',
            'cooperative', 'primary_membership',
        ]
        read_only_fields = ['id', 'date_joined', 'updated_at', 'primary_membership']

    def get_primary_membership(self, obj):
        pm = obj.primary_membership
        if pm:
            return {
                'id': str(pm.id),
                'cooperative_id': str(pm.cooperative_id),
                'member_number': pm.member_number,
                'payment_method': pm.payment_method,
                'is_active': pm.is_active,
            }
        return None


class AdminDeliverySerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    grader_name = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            'id', 'farmer', 'farmer_name', 'grader', 'grader_name',
            'product_type', 'batch_id', 'quantity_kg', 'volume_litres',
            'status', 'grade', 'quality_metrics', 'rejection_reason',
            'date_delivered', 'shift', 'is_synced', 'cooperative',
        ]
        read_only_fields = fields

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'

    def get_grader_name(self, obj):
        if obj.grader:
            return obj.grader.get_full_name()
        return None


class AdminForceDeliveryStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=DeliveryStatus.choices)


class AdminPaymentCycleSerializer(serializers.ModelSerializer):
    locked_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentCycle
        fields = [
            'id', 'name', 'start_date', 'end_date', 'status',
            'totals', 'total_levy', 'total_cooperative_fee',
            'total_loan_repayments', 'total_input_credits',
            'has_warnings', 'locked_by', 'locked_by_name',
            'locked_at', 'computed_at', 'created_at', 'updated_at',
            'cooperative',
        ]
        read_only_fields = [
            'id', 'status', 'totals', 'total_levy', 'total_cooperative_fee',
            'total_loan_repayments', 'total_input_credits', 'has_warnings',
            'locked_by', 'locked_by_name', 'locked_at', 'computed_at',
            'created_at', 'updated_at',
        ]

    def get_locked_by_name(self, obj):
        if obj.locked_by:
            return obj.locked_by.get_full_name()
        return None


class AdminDisbursementBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisbursementBatch
        fields = '__all__'
        read_only_fields = [
            'id', 'status', 'total_amount', 'total_transactions',
            'successful_count', 'failed_count', 'approved_by',
            'approved_at', 'created_by', 'created_at', 'updated_at',
        ]


class AdminFarmerPaymentSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()

    class Meta:
        model = FarmerPayment
        fields = '__all__'
        read_only_fields = [
            'id', 'cycle', 'farmer', 'farmer_name', 'total_quantity',
            'grade_breakdown', 'gross_amount', 'deductions', 'net_amount',
            'payment_status', 'computation_log', 'withholding_tax_amount',
            'is_subject_to_withholding_tax', 'carried_forward_amount',
            'carry_forward_reason', 'created_at',
        ]

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'


class AdminFarmerPaymentHoldSerializer(serializers.Serializer):
    hold = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True)


class AdminLoanSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = '__all__'
        read_only_fields = [
            'id', 'status', 'approved_by', 'approved_at',
            'disbursed_at', 'created_at',
        ]

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'


class AdminOTPTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TwoFactorOTP
        fields = ['id', 'user', 'purpose', 'attempts', 'expires_at', 'is_used', 'created_at']


class AdminSoftDeleteConfirmSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(required=True)

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError('You must set confirm to true to proceed.')
        return value


class AdminRestoreConfirmSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(required=True)

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError('You must set confirm to true to proceed.')
        return value


class AdminPurgeConfirmSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(required=True)

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError('You must set confirm to true to proceed.')
        return value


class AdminBinSummarySerializer(serializers.Serializer):
    pass
