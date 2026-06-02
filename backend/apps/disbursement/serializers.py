import uuid

from rest_framework import serializers

from apps.payment_engine.models import FarmerPayment, PaymentCycle

from .models import CommandId, DisbursementBatch, DisbursementTransaction


class DisbursementTransactionSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    member_number = serializers.SerializerMethodField()
    mpesa_number = serializers.SerializerMethodField()

    class Meta:
        model = DisbursementTransaction
        fields = [
            'id', 'batch', 'farmer', 'farmer_name', 'member_number',
            'amount', 'payment_method', 'recipient_identifier',
            'recipient_name', 'mpesa_number',
            'status', 'transaction_id', 'conversation_id',
            'result_code', 'result_desc', 'failure_reason',
            'retry_count', 'withholding_tax_amount',
            'queued_at', 'sent_at', 'completed_at', 'failed_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_farmer_name(self, obj):
        return f'{obj.farmer.first_name} {obj.farmer.last_name}'

    def get_member_number(self, obj):
        return obj.farmer.member_number

    def get_mpesa_number(self, obj):
        return obj.farmer.mpesa_number


class DisbursementBatchListSerializer(serializers.ModelSerializer):
    transaction_count = serializers.SerializerMethodField()
    payment_cycle_name = serializers.SerializerMethodField()

    class Meta:
        model = DisbursementBatch
        fields = [
            'id', 'payment_cycle', 'payment_cycle_name',
            'status', 'command_id', 'total_amount',
            'total_transactions', 'successful_count', 'failed_count',
            'transaction_count',
            'approved_by', 'approved_at', 'created_by',
            'notes', 'created_at',
        ]
        read_only_fields = fields

    def get_transaction_count(self, obj):
        return obj.total_transactions

    def get_payment_cycle_name(self, obj):
        if obj.payment_cycle:
            return obj.payment_cycle.name
        return None


class DisbursementBatchDetailSerializer(serializers.ModelSerializer):
    transactions = DisbursementTransactionSerializer(many=True, read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DisbursementBatch
        fields = [
            'id', 'payment_cycle', 'status', 'command_id',
            'total_amount', 'total_transactions',
            'successful_count', 'failed_count',
            'celery_task_id',
            'approved_by', 'approved_by_name',
            'approved_at', 'created_by', 'created_by_name',
            'notes', 'transactions',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return f'{obj.approved_by.first_name} {obj.approved_by.last_name}'.strip() or obj.approved_by.email
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f'{obj.created_by.first_name} {obj.created_by.last_name}'.strip() or obj.created_by.email
        return None


class DisbursementBatchCreateSerializer(serializers.Serializer):
    payment_cycle = serializers.UUIDField()
    command_id = serializers.ChoiceField(
        choices=CommandId.choices,
        default=CommandId.SALARY_PAYMENT,
        required=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_payment_cycle(self, value):
        try:
            cycle = PaymentCycle.objects.get(id=value)
        except PaymentCycle.DoesNotExist:
            raise serializers.ValidationError('Payment cycle not found.')

        if cycle.status != 'LOCKED':
            raise serializers.ValidationError(
                'Only LOCKED payment cycles can be disbursed.'
            )

        request = self.context.get('request')
        if request:
            coop_id = getattr(request, 'cooperative_id', None)
            if coop_id and str(cycle.cooperative_id) != str(coop_id):
                raise serializers.ValidationError(
                    'Payment cycle does not belong to your cooperative.'
                )

        self._cycle = cycle
        return value

    def create(self, validated_data):
        cycle = self._cycle
        request = self.context.get('request')
        cooperative = cycle.cooperative

        batch = DisbursementBatch.objects.create(
            cooperative=cooperative,
            payment_cycle=cycle,
            command_id=validated_data.get('command_id', 'SalaryPayment'),
            notes=validated_data.get('notes', ''),
            created_by=request.user if request else None,
            status='PENDING',
        )

        farmer_payments = FarmerPayment.objects.filter(
            cycle=cycle,
            is_on_hold=False,
        ).select_related('farmer').order_by('farmer__member_number', 'id')

        txns = []
        minimum_payout = float(cooperative.minimum_payout_amount or 0)

        for fp in farmer_payments:
            net = float(fp.net_amount)
            if net <= 0:
                continue

            if net < minimum_payout:
                fp.carried_forward_amount = fp.net_amount
                fp.carry_forward_reason = 'BELOW_MINIMUM_THRESHOLD'
                fp.save(update_fields=['carried_forward_amount', 'carry_forward_reason'])
                continue

            farmer = fp.farmer
            if farmer.payment_method == 'M-PESA':
                recipient = farmer.mpesa_number
            elif farmer.payment_method == 'BANK':
                recipient = farmer.bank_account or ''
            else:
                recipient = ''

            txn = DisbursementTransaction(
                cooperative=cooperative,
                batch=batch,
                farmer_payment=fp,
                farmer=farmer,
                amount=fp.net_amount,
                payment_method=farmer.payment_method.replace('-', '_'),
                recipient_identifier=recipient,
                recipient_name=str(farmer),
                status='PENDING',
                conversation_id=str(uuid.uuid4()),
                withholding_tax_amount=fp.withholding_tax_amount,
                created_by=request.user if request else None,
            )
            txns.append(txn)

        DisbursementTransaction.objects.bulk_create(txns)

        total_amount = sum(t.amount for t in txns)
        batch.total_amount = total_amount
        batch.total_transactions = len(txns)
        batch.save(update_fields=['total_amount', 'total_transactions'])

        return batch


class ConfirmManualSerializer(serializers.Serializer):
    transaction_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True)
