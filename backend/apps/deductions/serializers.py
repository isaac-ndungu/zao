from rest_framework import serializers

from .models import Deduction


class DeductionListSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    cycle_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Deduction
        fields = [
            'id', 'farmer', 'farmer_name', 'cycle', 'cycle_name',
            'deduction_type', 'amount', 'created_by_name', 'notes', 'created_at',
        ]

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'

    def get_cycle_name(self, obj):
        return obj.cycle.name

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None


class DeductionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deduction
        fields = ['farmer', 'cycle', 'amount', 'notes']

    def validate_cycle(self, value):
        if value.status == 'LOCKED':
            raise serializers.ValidationError(
                'Cannot add deductions to a locked cycle.'
            )
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0.')
        return value


class DeductionDetailSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    cycle_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Deduction
        fields = '__all__'

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'

    def get_cycle_name(self, obj):
        return obj.cycle.name

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None
