from rest_framework import serializers

from .models import Inventory


class InventoryListSerializer(serializers.ModelSerializer):
    running_balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
    )

    class Meta:
        model = Inventory
        fields = [
            'id', 'batch_id', 'product_type', 'grade', 'unit',
            'quantity_in', 'quantity_out', 'running_balance',
            'created_at',
        ]


class InventoryDetailSerializer(serializers.ModelSerializer):
    running_balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
    )

    class Meta:
        model = Inventory
        fields = '__all__'
        read_only_fields = [
            'id', 'batch_id', 'cooperative', 'product_type', 'grade',
            'unit', 'quantity_in', 'quantity_out', 'created_at', 'updated_at',
        ]
