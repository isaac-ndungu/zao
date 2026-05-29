from rest_framework import serializers

from apps.cooperatives.models import Cooperative

from .models import ComputationWarning, FarmerPayment, PaymentCycle


class FarmerPaymentPreviewSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    member_number = serializers.SerializerMethodField()

    class Meta:
        model = FarmerPayment
        fields = [
            'id', 'farmer', 'farmer_name', 'member_number',
            'total_quantity', 'grade_breakdown', 'gross_amount',
            'deductions', 'net_amount', 'payment_status', 'computation_log',
        ]
        read_only_fields = fields

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'

    def get_member_number(self, obj):
        return obj.farmer.member_number


class CyclePreviewSerializer(serializers.ModelSerializer):
    farmer_payments = FarmerPaymentPreviewSerializer(many=True, read_only=True)
    warnings = serializers.JSONField(read_only=True, source='warnings.values')

    class Meta:
        model = PaymentCycle
        fields = [
            'id', 'name', 'status', 'totals',
            'total_levy', 'total_cooperative_fee', 'total_loan_repayments',
            'has_warnings', 'warnings',
            'farmer_payments', 'computed_at', 'locked_at',
        ]
        read_only_fields = fields


class PaymentCycleSerializer(serializers.ModelSerializer):
    cooperative_id = serializers.UUIDField(required=False, write_only=True)

    class Meta:
        model = PaymentCycle
        fields = [
            'id', 'name', 'start_date', 'end_date',
            'status', 'totals',
            'total_levy', 'total_cooperative_fee', 'total_loan_repayments',
            'has_warnings', 'celery_task_id',
            'locked_by', 'locked_at', 'computed_at',
            'cooperative', 'cooperative_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'cooperative', 'locked_by', 'locked_at',
            'computed_at', 'created_at', 'updated_at',
            'status', 'totals',
            'total_levy', 'total_cooperative_fee', 'total_loan_repayments',
            'has_warnings', 'celery_task_id',
        ]

    def validate_cooperative_id(self, value):
        if not Cooperative.objects.filter(id=value).exists():
            raise serializers.ValidationError('Cooperative not found.')
        return value

    def validate(self, attrs):
        start = attrs.get('start_date')
        end = attrs.get('end_date')

        if start and end:
            if start > end:
                raise serializers.ValidationError(
                    'Start date must be before or equal to end date.'
                )

            request = self.context.get('request')
            if request:
                coop_id = getattr(request, 'cooperative_id', None)
                if coop_id:
                    overlapping = PaymentCycle.objects.filter(
                        cooperative_id=coop_id,
                        start_date__lte=end,
                        end_date__gte=start,
                    )
                    if self.instance:
                        overlapping = overlapping.exclude(id=self.instance.id)

                    if overlapping.exists():
                        names = list(
                            overlapping.values_list('name', flat=True)[:5]
                        )
                        raise serializers.ValidationError(
                            f'Date range overlaps with existing cycle(s): '
                            f'{", ".join(names)}.'
                        )

        return attrs


class PaymentCycleStatusSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    computed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    locked_at = serializers.DateTimeField(read_only=True, allow_null=True)
    locked_by = serializers.SerializerMethodField()
    totals = serializers.JSONField(read_only=True)
    total_levy = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_cooperative_fee = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_loan_repayments = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    has_warnings = serializers.BooleanField(read_only=True)
    celery_task_id = serializers.CharField(read_only=True)

    def get_locked_by(self, obj):
        if obj.locked_by:
            return obj.locked_by.get_full_name() or obj.locked_by.email
        return None


class ComputationWarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComputationWarning
        fields = ['id', 'severity', 'message', 'delivery_id', 'farmer_id', 'created_at']
