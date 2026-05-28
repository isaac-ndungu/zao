import re

from rest_framework import serializers

from apps.auth_api.models import User
from apps.base.constants import KENYA_COUNTIES
from apps.base.encryption import decrypt_field, encrypt_field
from apps.base.utils import normalize_phone
from apps.cooperatives.models import Cooperative
from apps.farmers.models import Farmer


KENYA_PHONE_RE = re.compile(r'^(?:\+254|0|254)?7\d{8}$')
KENYA_ID_RE = re.compile(r'^\d{6,8}$')


class FarmerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farmer
        fields = [
            'id', 'member_number', 'first_name', 'last_name',
            'phone_number', 'mpesa_number', 'payment_method',
            'is_active', 'date_joined', 'email',
        ]


class FarmerDetailSerializer(serializers.ModelSerializer):
    decrypted_id_number = serializers.SerializerMethodField()

    class Meta:
        model = Farmer
        fields = '__all__'
        read_only_fields = [
            'id', 'member_number', 'cooperative', 'user',
            'date_joined', 'updated_at',
        ]

    def get_decrypted_id_number(self, obj) -> str | None:
        if obj.id_number:
            return decrypt_field(obj.id_number)
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop('id_number', None)
        return data


class FarmerCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(required=False, write_only=True)
    user_email = serializers.EmailField(required=False, write_only=True)
    cooperative_id = serializers.UUIDField(required=False, write_only=True)

    class Meta:
        model = Farmer
        fields = [
            'first_name', 'last_name', 'email', 'id_number', 'phone_number',
            'mpesa_number', 'date_of_birth', 'county', 'sub_county',
            'ward', 'village', 'payment_method', 'bank_name',
            'bank_account', 'bank_branch', 'is_active',
            'user_id', 'user_email', 'cooperative_id',
        ]
        extra_kwargs = {
            'first_name': {'min_length': 1},
            'last_name': {'min_length': 1},
        }

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError('User not found.')
        return value

    def validate_cooperative_id(self, value):
        if not Cooperative.objects.filter(id=value).exists():
            raise serializers.ValidationError('Cooperative not found.')
        return value

    def validate_user_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_phone_number(self, value):
        value = normalize_phone(value)
        if not KENYA_PHONE_RE.match(value):
            raise serializers.ValidationError(
                'Enter a valid Kenyan phone number (e.g. 0712345678 or +254712345678).'
            )
        return value

    def validate_mpesa_number(self, value):
        if value:
            value = normalize_phone(value)
            if not KENYA_PHONE_RE.match(value):
                raise serializers.ValidationError(
                    'Enter a valid Kenyan phone number (e.g. 0712345678 or +254712345678).'
                )
        return value

    def validate_id_number(self, value):
        if value and not KENYA_ID_RE.match(value):
            raise serializers.ValidationError(
                'Enter a valid Kenyan ID number (6-8 digits).'
            )
        return value

    def validate_county(self, value):
        if value not in KENYA_COUNTIES:
            raise serializers.ValidationError(
                f'{value} is not a valid Kenyan county. '
                f'Choose from: {", ".join(KENYA_COUNTIES)}.'
            )
        return value

    def validate(self, attrs):
        if attrs.get('payment_method') == 'BANK':
            if not attrs.get('bank_name'):
                raise serializers.ValidationError(
                    {'bank_name': 'Bank name is required when payment method is BANK.'}
                )
            if not attrs.get('bank_account'):
                raise serializers.ValidationError(
                    {'bank_account': 'Bank account is required when payment method is BANK.'}
                )
        return attrs

    def create(self, validated_data):
        validated_data.pop('user_id', None)
        validated_data.pop('user_email', None)
        if validated_data.get('id_number'):
            validated_data['id_number'] = encrypt_field(validated_data['id_number'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('cooperative_id', None)
        validated_data.pop('user_id', None)
        validated_data.pop('user_email', None)
        if 'id_number' in validated_data and validated_data['id_number']:
            validated_data['id_number'] = encrypt_field(validated_data['id_number'])
        return super().update(instance, validated_data)


class FarmerSelfUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farmer
        fields = [
            'phone_number', 'mpesa_number', 'email', 'bank_name',
            'bank_account', 'bank_branch', 'village',
            'ward', 'sub_county',
        ]
        extra_kwargs = {field: {'required': False} for field in fields}

    def validate_phone_number(self, value):
        if value:
            value = normalize_phone(value)
            if not KENYA_PHONE_RE.match(value):
                raise serializers.ValidationError(
                    'Enter a valid Kenyan phone number (e.g. 0712345678 or +254712345678).'
                )
        return value

    def validate_mpesa_number(self, value):
        if value:
            value = normalize_phone(value)
            if not KENYA_PHONE_RE.match(value):
                raise serializers.ValidationError(
                    'Enter a valid Kenyan phone number (e.g. 0712345678 or +254712345678).'
                )
        return value
