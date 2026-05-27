from rest_framework import serializers

from apps.farmers.models import Farmer
from .models import Delivery


class DeliveryListSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            'id', 'batch_id', 'farmer_name', 'product_type',
            'quantity_kg', 'volume_litres', 'grade', 'status',
            'date_delivered', 'shift',
        ]

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'


class DeliveryDetailSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    grader_name = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = '__all__'
        read_only_fields = [
            'id', 'batch_id', 'cooperative', 'date_delivered', 'updated_at',
        ]

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'

    def get_grader_name(self, obj):
        if obj.grader:
            return obj.grader.get_full_name() or obj.grader.email
        return None


class DeliveryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = [
            'farmer', 'grader', 'product_type',
            'quantity_kg', 'volume_litres',
            'grade', 'quality_metrics', 'rejection_reason',
            'status', 'shift', 'is_synced', 'local_id',
        ]

    def validate_farmer(self, value):
        if not value.is_active:
            raise serializers.ValidationError('Farmer is not active.')
        return value

    def validate(self, attrs):
        product = attrs.get('product_type')
        if product == 'MILK' and not attrs.get('volume_litres'):
            raise serializers.ValidationError(
                {'volume_litres': 'Volume in litres is required for milk deliveries.'}
            )
        if product in ('COFFEE_CHERRIES', 'HONEY') and not attrs.get('quantity_kg'):
            raise serializers.ValidationError(
                {'quantity_kg': 'Quantity in kg is required for this product type.'}
            )
        if attrs.get('status') == 'REJECTED' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError(
                {'rejection_reason': 'Rejection reason is required when status is REJECTED.'}
            )
        return attrs


class DeliverySyncSerializer(serializers.Serializer):
    deliveries = DeliveryCreateSerializer(many=True)
