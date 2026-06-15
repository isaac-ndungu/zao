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
        if items.exists():
            return [
                {
                    'inventory_id': str(li.inventory_id),
                    'batch_id': li.inventory.batch_id,
                    'quantity': float(li.quantity),
                }
                for li in items
            ]
        if obj.inventory:
            return [
                {
                    'inventory_id': str(obj.inventory_id),
                    'batch_id': obj.inventory.batch_id,
                    'quantity': float(obj.quantity),
                }
            ]
        return []


class SaleCreateSerializer(serializers.ModelSerializer):
    cooperative_id = serializers.UUIDField(required=False, write_only=True)
    line_items = SaleInventoryLineItemSerializer(many=True, write_only=True)

    class Meta:
        model = Sale
        fields = [
            'buyer', 'line_items',
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

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError('At least one inventory line item is required.')

        seen = set()
        product_types = set()
        grades = set()

        for item in value:
            inv_id = str(item['inventory'])
            if inv_id in seen:
                raise serializers.ValidationError(
                    f'Duplicate inventory entry: {inv_id}. Each batch can appear only once per sale.'
                )
            seen.add(inv_id)

            if item['quantity'] <= 0:
                raise serializers.ValidationError(
                    f'Quantity for inventory {inv_id} must be greater than 0.'
                )

        inventory_ids = list(seen)
        inventories = {
            str(i.id): i
            for i in Inventory.objects.filter(id__in=inventory_ids)
        }

        for inv_id in inventory_ids:
            inv = inventories.get(inv_id)
            if not inv:
                raise serializers.ValidationError(f'Inventory {inv_id} not found.')
            product_types.add(inv.product_type)
            grades.add(inv.grade)

        if len(product_types) > 1:
            raise serializers.ValidationError(
                'All line items must share the same product_type.'
            )
        if len(grades) > 1:
            raise serializers.ValidationError(
                'All line items must share the same grade.'
            )

        return value

    def validate(self, attrs):
        line_items = attrs.get('line_items', [])
        quantity = attrs.get('quantity', 0)
        total_line_qty = sum(item['quantity'] for item in line_items)

        if quantity != total_line_qty:
            raise serializers.ValidationError(
                f'Sale quantity ({float(quantity)}) must equal the sum of '
                f'line item quantities ({float(total_line_qty)}).'
            )

        inventory_ids = [str(item['inventory']) for item in line_items]
        inventories = {
            str(i.id): i
            for i in Inventory.objects.filter(id__in=inventory_ids)
        }

        for item in line_items:
            inv = inventories[str(item['inventory'])]
            available = inv.quantity_in - inv.quantity_out
            if item['quantity'] > available:
                raise serializers.ValidationError(
                    f'Insufficient inventory in batch {inv.batch_id}: '
                    f'{float(available)} {inv.unit} available, '
                    f'{float(item["quantity"])} {inv.unit} requested.'
                )

        return attrs

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items', [])

        first_inv = Inventory.objects.get(id=line_items_data[0]['inventory'])
        validated_data['product_type'] = first_inv.product_type
        validated_data['grade_letter'] = first_inv.grade
        validated_data['unit'] = first_inv.unit
        validated_data['total_amount'] = validated_data['quantity'] * validated_data['price_per_unit']

        sale = super().create(validated_data)

        line_item_objs = [
            SaleInventoryLineItem(
                sale=sale,
                inventory_id=item['inventory'],
                quantity=item['quantity'],
            )
            for item in line_items_data
        ]
        SaleInventoryLineItem.objects.bulk_create(line_item_objs)

        return sale

    def update(self, instance, validated_data):
        validated_data.pop('line_items', None)
        quantity = validated_data.get('quantity', instance.quantity)
        price_per_unit = validated_data.get('price_per_unit', instance.price_per_unit)
        validated_data['total_amount'] = quantity * price_per_unit
        return super().update(instance, validated_data)
