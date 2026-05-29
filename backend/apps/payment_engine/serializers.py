from rest_framework import serializers

from apps.cooperatives.models import Cooperative

from .models import FarmerPayment, PaymentCycle


class FarmerPaymentPreviewSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    member_number = serializers.SerializerMethodField()

    class Meta:
        model = FarmerPayment
        fields = [
            'id', 'farmer', 'farmer_name', 'member_number',
            'total_quantity', 'grade_breakdown', 'gross_amount',
            'deductions', 'net_amount', 'computation_log',
        ]
        read_only_fields = fields

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'

    def get_member_number(self, obj):
        return obj.farmer.member_number


class CyclePreviewSerializer(serializers.ModelSerializer):
    farmer_payments = FarmerPaymentPreviewSerializer(many=True, read_only=True)
    total_gross = serializers.SerializerMethodField()
    total_net = serializers.SerializerMethodField()

    class Meta:
        model = PaymentCycle
        fields = [
            'id', 'name', 'status', 'totals',
            'total_gross', 'total_net',
            'farmer_payments', 'computed_at', 'locked_at',
        ]
        read_only_fields = fields

    def get_total_gross(self, obj):
        return obj.totals.get('total_gross', 0) if obj.totals else 0

    def get_total_net(self, obj):
        return obj.totals.get('total_net', 0) if obj.totals else 0


class PaymentCycleSerializer(serializers.ModelSerializer):
    cooperative_id = serializers.UUIDField(required=False, write_only=True)

    class Meta:
        model = PaymentCycle
        fields = [
            'id', 'name', 'start_date', 'end_date',
            'status', 'totals',
            'locked_by', 'locked_at', 'computed_at',
            'cooperative', 'cooperative_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'cooperative', 'locked_by', 'locked_at',
            'computed_at', 'created_at', 'updated_at',
            'status', 'totals',
        ]

    def validate_cooperative_id(self, value):
        if not Cooperative.objects.filter(id=value).exists():
            raise serializers.ValidationError('Cooperative not found.')
        return value

    def validate_dates(self, start_date, end_date):
        if start_date > end_date:
            raise serializers.ValidationError(
                'Start date must be before or equal to end date.'
            )
        return start_date, end_date

    def validate(self, attrs):
        if 'start_date' in attrs and 'end_date' in attrs:
            self.validate_dates(attrs['start_date'], attrs['end_date'])
        return attrs


class PaymentCycleStatusSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    computed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    locked_at = serializers.DateTimeField(read_only=True, allow_null=True)
    locked_by = serializers.SerializerMethodField()
    totals = serializers.JSONField(read_only=True)

    def get_locked_by(self, obj):
        if obj.locked_by:
            return obj.locked_by.get_full_name() or obj.locked_by.email
        return None
