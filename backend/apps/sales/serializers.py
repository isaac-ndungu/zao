from rest_framework import serializers

from apps.cooperatives.models import Cooperative

from .models import Buyer, PaymentCycle, Sale


class BuyerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Buyer
        fields = '__all__'
        read_only_fields = ['id', 'cooperative', 'created_at', 'updated_at']


class PaymentCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentCycle
        fields = '__all__'
        read_only_fields = ['id', 'cooperative', 'created_at', 'updated_at']


class SaleListSerializer(serializers.ModelSerializer):
    buyer_name = serializers.SerializerMethodField()
    batch_id = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            'id', 'buyer_name', 'batch_id',
            'product_type', 'grade_letter', 'unit',
            'quantity', 'price_per_unit', 'total_amount',
            'status', 'sale_date', 'invoice_number',
        ]

    def get_buyer_name(self, obj):
        return obj.buyer.name

    def get_batch_id(self, obj):
        return obj.inventory.batch_id


class SaleDetailSerializer(serializers.ModelSerializer):
    buyer_name = serializers.SerializerMethodField()
    batch_id = serializers.SerializerMethodField()
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = [
            'id', 'cooperative', 'product_type', 'grade_letter', 'unit',
            'total_amount', 'created_at', 'updated_at',
        ]

    def get_buyer_name(self, obj):
        return obj.buyer.name

    def get_batch_id(self, obj):
        return obj.inventory.batch_id

    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return obj.recorded_by.get_full_name() or obj.recorded_by.email
        return None


class SaleCreateSerializer(serializers.ModelSerializer):
    cooperative_id = serializers.UUIDField(required=False, write_only=True)

    class Meta:
        model = Sale
        fields = [
            'buyer', 'inventory',
            'quantity', 'price_per_unit',
            'payment_cycle', 'status', 'sale_date',
            'invoice_number', 'notes',
            'cooperative_id',
        ]

    def validate_cooperative_id(self, value):
        if not Cooperative.objects.filter(id=value).exists():
            raise serializers.ValidationError('Cooperative not found.')
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Quantity must be greater than 0.')
        return value

    def validate_price_per_unit(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price per unit must be greater than 0.')
        return value

    def validate(self, attrs):
        inventory = attrs.get('inventory')
        quantity = attrs.get('quantity')
        if inventory and quantity:
            available = inventory.quantity_in - inventory.quantity_out
            if quantity > available:
                raise serializers.ValidationError(
                    f'Insufficient inventory: {float(available)} {inventory.unit} available, '
                    f'{float(quantity)} {inventory.unit} requested.'
                )
        return attrs
