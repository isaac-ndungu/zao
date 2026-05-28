from rest_framework import serializers

from apps.cooperatives.models import Cooperative
from .models import Grade, GradePrice


def validate_delivery_scoped(value, request, instance=None):
    if value.status != 'PENDING':
        raise serializers.ValidationError(
            'Only PENDING deliveries can be graded.'
        )
    if request and value.cooperative_id != request.cooperative_id:
        raise serializers.ValidationError(
            'Delivery does not belong to your cooperative.'
        )
    if hasattr(value, 'grade_record'):
        if instance and value.grade_record.id == instance.id:
            return value
        raise serializers.ValidationError(
            'This delivery already has a grade.'
        )
    return value


class GradeListSerializer(serializers.ModelSerializer):
    batch_id = serializers.CharField(source='delivery.batch_id', read_only=True)
    farmer_name = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [
            'id', 'delivery', 'batch_id', 'farmer_name',
            'grade_letter', 'price_per_unit', 'rejection_reason',
            'is_overridden', 'overridden_at', 'override_reason',
            'created_at', 'updated_at',
        ]

    def get_farmer_name(self, obj):
        return f'{obj.delivery.farmer.first_name} {obj.delivery.farmer.last_name}'


class GradeDetailSerializer(serializers.ModelSerializer):
    batch_id = serializers.CharField(source='delivery.batch_id', read_only=True)
    farmer_name = serializers.SerializerMethodField()
    product_type = serializers.CharField(source='delivery.product_type', read_only=True)

    class Meta:
        model = Grade
        fields = '__all__'
        read_only_fields = [
            'id', 'delivery', 'is_overridden', 'overridden_by',
            'overridden_at', 'cooperative', 'created_at', 'updated_at',
        ]

    def get_farmer_name(self, obj):
        return f'{obj.delivery.farmer.first_name} {obj.delivery.farmer.last_name}'


class GradeCreateSerializer(serializers.ModelSerializer):
    cooperative_id = serializers.UUIDField(required=False, write_only=True)

    class Meta:
        model = Grade
        fields = [
            'delivery', 'grade_letter', 'price_per_unit', 'rejection_reason',
            'cooperative_id',
        ]

    def validate_cooperative_id(self, value):
        if not Cooperative.objects.filter(id=value).exists():
            raise serializers.ValidationError('Cooperative not found.')
        return value

    def validate_delivery(self, value):
        return validate_delivery_scoped(
            value, request=self.context.get('request'), instance=self.instance,
        )

    def validate(self, attrs):
        if attrs.get('grade_letter') and attrs.get('rejection_reason'):
            raise serializers.ValidationError(
                'Cannot assign a grade and a rejection reason. '
                'Use rejection_reason only for rejected deliveries.'
            )
        return attrs


class GradeOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = [
            'grade_letter', 'price_per_unit', 'rejection_reason', 'override_reason',
        ]

    def validate(self, attrs):
        if not attrs.get('override_reason'):
            raise serializers.ValidationError(
                {'override_reason': 'Override reason is required.'}
            )
        if attrs.get('grade_letter') and attrs.get('rejection_reason'):
            raise serializers.ValidationError(
                'Cannot set a grade letter and a rejection reason together.'
            )
        return attrs


class GradePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradePrice
        fields = ['id', 'grade_letter', 'price_per_unit', 'effective_from', 'created_at']
        read_only_fields = ['id', 'created_at']
