from rest_framework import serializers

from apps.cooperatives.models import Cooperative
from apps.inventory.models import Inventory

from .models import Buyer, Sale, SaleInventoryLineItem


class SaleInventoryLineItemSerializer(serializers.Serializer):
    inventory = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)


class BuyerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Buyer
        fields = '__all__'
        read_only_fields = ['id', 'cooperative', 'created_at', 'updated_at']


class SaleListSerializer(serializers.ModelSerializer):
    buyer_name = serializers.SerializerMethodField()
    batch_ids = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            'id', 'buyer_name', 'batch_ids',
            'product_type', 'grade_letter', 'unit',
            'quantity', 'price_per_unit', 'total_amount',
            'status', 'sale_date', 'invoice_number',
        ]

    def get_buyer_name(self, obj):
        return obj.buyer.name

    def get_batch_ids(self, obj):
        batches = obj.all_inventory
        if not batches:
            return []
        return [str(inv.batch_id) for inv, _ in batches]


class SaleDetailSerializer(serializers.ModelSerializer):
    buyer_name = serializers.SerializerMethodField()
    batch_ids = serializers.SerializerMethodField()
    recorded_by_name = serializers.SerializerMethodField()
    line_items = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = [
            'id', 'cooperative', 'product_type', 'grade_letter', 'unit',
            'total_amount', 'created_at', 'updated_at',
        ]

    def get_buyer_name(self, obj):
        return obj.buyer.name

    def get_batch_ids(self, obj):
        batches = obj.all_inventory
        if not batches:
            return []
        return [str(inv.batch_id) for inv, _ in batches]

    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return obj.recorded_by.get_full_name() or obj.recorded_by.email
        return None

    def get_line_items(self, obj):
        items = obj.line_items.select_related('inventory').all()
        return [
            {
                'inventory_id': str(li.inventory_id),
                'batch_id': li.inventory.batch_id,
                'quantity': float(li.quantity),
            }
            for li in items
        ]


class SaleCreateSerializer(serializers.ModelSerializer):
    cooperative_id = serializers.UUIDField(required=False, write_only=True)
    stock = serializers.UUIDField(write_only=True)

    class Meta:
        model = Sale
        fields = [
            'id', 'buyer', 'stock',
            'quantity', 'price_per_unit',
            'payment_cycle', 'status', 'sale_date',
            'invoice_number', 'notes',
            'cooperative_id',
        ]
        read_only_fields = ['id']

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

    def validate_stock(self, value):
        from apps.inventory.models import Stock
        if not Stock.objects.filter(id=value).exists():
            raise serializers.ValidationError('Stock not found.')
        return value

    def validate(self, attrs):
        from decimal import Decimal
        from apps.inventory.models import Stock
        stock_id = attrs.get('stock')
        quantity = attrs.get('quantity', Decimal('0'))
        if stock_id and quantity:
            try:
                stock = Stock.objects.get(id=stock_id)
            except Stock.DoesNotExist:
                raise serializers.ValidationError({'stock': 'Stock not found.'})
            if Decimal(str(quantity)) > Decimal(str(stock.quantity_available)):
                raise serializers.ValidationError(
                    f'Insufficient stock: {stock.quantity_available} {stock.unit} available, '
                    f'{float(quantity)} {stock.unit} requested.'
                )
        return attrs

    def create(self, validated_data):
        from apps.inventory.models import Stock
        stock_id = validated_data.pop('stock')
        stock = Stock.objects.get(id=stock_id)
        validated_data['product_type'] = stock.product_type
        validated_data['grade_letter'] = stock.grade
        validated_data['unit'] = stock.unit
        validated_data['stock'] = stock
        validated_data['status'] = 'COMPLETED'
        validated_data['total_amount'] = validated_data['quantity'] * validated_data['price_per_unit']
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('stock', None)
        quantity = validated_data.get('quantity', instance.quantity)
        price_per_unit = validated_data.get('price_per_unit', instance.price_per_unit)
        validated_data['total_amount'] = quantity * price_per_unit
        return super().update(instance, validated_data)
