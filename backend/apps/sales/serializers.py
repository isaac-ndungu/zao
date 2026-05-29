from rest_framework import serializers

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
    grade_letter = serializers.SerializerMethodField()
    batch_id = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            'id', 'buyer_name', 'grade_letter', 'batch_id',
            'quantity', 'price_per_unit', 'total_amount',
            'sale_date', 'invoice_number',
        ]

    def get_buyer_name(self, obj):
        return obj.buyer.name

    def get_grade_letter(self, obj):
        return obj.grade.grade_letter

    def get_batch_id(self, obj):
        return obj.grade.delivery.batch_id


class SaleDetailSerializer(serializers.ModelSerializer):
    buyer_name = serializers.SerializerMethodField()
    grade_letter = serializers.SerializerMethodField()
    batch_id = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = [
            'id', 'cooperative', 'total_amount',
            'sale_date', 'created_at', 'updated_at',
        ]

    def get_buyer_name(self, obj):
        return obj.buyer.name

    def get_grade_letter(self, obj):
        return obj.grade.grade_letter

    def get_batch_id(self, obj):
        return obj.grade.delivery.batch_id


class SaleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = [
            'buyer', 'grade', 'inventory',
            'quantity', 'price_per_unit',
            'payment_cycle', 'invoice_number', 'notes',
        ]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Quantity must be greater than 0.')
        return value

    def validate_price_per_unit(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price per unit must be greater than 0.')
        return value
