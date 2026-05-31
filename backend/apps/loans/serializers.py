from rest_framework import serializers

from .models import Loan, LoanRepayment


class LoanListSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    farmer_member_number = serializers.SerializerMethodField()
    remaining_installments = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'farmer', 'farmer_name', 'farmer_member_number',
            'amount_principal', 'interest_rate', 'total_repayable',
            'installment_amount', 'number_of_installments',
            'installments_paid', 'remaining_installments', 'status',
            'approved_at', 'disbursed_at', 'created_at',
        ]

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'

    def get_farmer_member_number(self, obj):
        return obj.farmer.member_number

    def get_remaining_installments(self, obj):
        return max(0, obj.number_of_installments - obj.installments_paid)


class LoanRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRepayment
        fields = ['id', 'amount', 'created_at']


class LoanDetailSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    farmer_member_number = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    repayments = LoanRepaymentSerializer(many=True, read_only=True)
    remaining_installments = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = '__all__'

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'

    def get_farmer_member_number(self, obj):
        return obj.farmer.member_number

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return f'{obj.approved_by.first_name} {obj.approved_by.last_name}'.strip() or obj.approved_by.email
        return None

    def get_remaining_installments(self, obj):
        return max(0, obj.number_of_installments - obj.installments_paid)


class LoanApproveSerializer(serializers.Serializer):
    def validate(self, attrs):
        loan = self.context['view'].get_object()
        if loan.status != 'PENDING':
            raise serializers.ValidationError('Only PENDING loans can be approved.')
        return attrs


class LoanCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = [
            'farmer', 'amount_principal', 'interest_rate',
            'number_of_installments', 'notes',
        ]

    def validate_amount_principal(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Principal amount must be greater than 0.'
            )
        return value

    def validate_interest_rate(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'Interest rate cannot be negative.'
            )
        return value

    def validate_number_of_installments(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Must have at least 1 installment.'
            )
        return value

    def validate_farmer(self, value):
        user = self.context['request'].user
        if user.role == 'FARMER':
            if not hasattr(user, 'farmer_profile') or user.farmer_profile != value:
                raise serializers.ValidationError(
                    'You can only create a loan for yourself.'
                )
        return value
