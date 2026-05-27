from rest_framework import serializers

from apps.auth_api.models import User
from apps.base.encryption import decrypt_field, encrypt_field
from apps.farmers.models import Farmer


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

    class Meta:
        model = Farmer
        fields = [
            'first_name', 'last_name', 'email', 'id_number', 'phone_number',
            'mpesa_number', 'date_of_birth', 'county', 'sub_county',
            'ward', 'village', 'payment_method', 'bank_name',
            'bank_account', 'bank_branch', 'is_active',
            'user_id', 'user_email',
        ]

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError('User not found.')
        return value

    def validate_user_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def create(self, validated_data):
        validated_data.pop('user_id', None)
        validated_data.pop('user_email', None)
        if validated_data.get('id_number'):
            validated_data['id_number'] = encrypt_field(validated_data['id_number'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
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
