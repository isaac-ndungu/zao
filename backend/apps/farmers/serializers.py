import re

from rest_framework import serializers

from apps.auth_api.models import User
from apps.base.constants import KENYA_COUNTIES
from apps.base.encryption import decrypt_field, encrypt_field
from apps.base.utils import normalize_phone
from apps.cooperatives.models import Cooperative
from apps.farmers.models import Farmer, FarmerCooperativeMembership


KENYA_PHONE_RE = re.compile(r'^(?:\+254|0|254)?[17]\d{8}$')
KENYA_ID_RE = re.compile(r'^\d{6,8}$')


def _validate_lat(value):
    if value is None:
        return value
    f = float(value)
    if not -90.0 <= f <= 90.0:
        raise serializers.ValidationError('Latitude must be between -90 and 90.')
    return value


def _validate_lng(value):
    if value is None:
        return value
    f = float(value)
    if not -180.0 <= f <= 180.0:
        raise serializers.ValidationError('Longitude must be between -180 and 180.')
    return value


class MembershipSerializer(serializers.ModelSerializer):
    cooperative_name = serializers.CharField(source='cooperative.name', read_only=True)

    class Meta:
        model = FarmerCooperativeMembership
        fields = [
            'id', 'cooperative', 'cooperative_name', 'member_number',
            'payment_method', 'mpesa_number', 'bank_name', 'bank_account',
            'bank_branch', 'is_active', 'joined_at',
        ]
        read_only_fields = ['id', 'member_number', 'joined_at']


class MembershipCreateSerializer(serializers.ModelSerializer):
    cooperative_id = serializers.UUIDField()

    class Meta:
        model = FarmerCooperativeMembership
        fields = ['cooperative_id']

    def validate_cooperative_id(self, value):
        if not Cooperative.objects.filter(id=value).exists():
            raise serializers.ValidationError('Cooperative not found.')
        return value

    def validate(self, attrs):
        farmer = self.context.get('farmer')
        coop_id = attrs['cooperative_id']
        if FarmerCooperativeMembership.objects.filter(
            farmer=farmer, cooperative_id=coop_id
        ).exists():
            raise serializers.ValidationError(
                'Farmer already has a membership in this cooperative.'
            )
        return attrs


class FarmerListSerializer(serializers.ModelSerializer):
    member_number = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    primary_cooperative_name = serializers.CharField(
        source='cooperative.name', read_only=True
    )

    class Meta:
        model = Farmer
        fields = [
            'id', 'member_number', 'first_name', 'last_name',
            'phone_number', 'payment_method',
            'is_active', 'date_joined', 'email', 'county',
            'primary_cooperative_name', 'latitude', 'longitude',
        ]

    def get_member_number(self, obj):
        primary = obj.primary_membership
        return primary.member_number if primary else ''

    def get_payment_method(self, obj):
        primary = obj.primary_membership
        return primary.payment_method if primary else 'M-PESA'


class FarmerDetailSerializer(serializers.ModelSerializer):
    decrypted_id_number = serializers.SerializerMethodField()
    member_number = serializers.SerializerMethodField()
    memberships = MembershipSerializer(many=True, read_only=True)
    payment_method = serializers.SerializerMethodField()
    mpesa_number = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()
    bank_account = serializers.SerializerMethodField()
    bank_branch = serializers.SerializerMethodField()
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
        validators=[_validate_lat],
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
        validators=[_validate_lng],
    )

    class Meta:
        model = Farmer
        fields = '__all__'
        read_only_fields = [
            'id', 'member_number', 'cooperative', 'user',
            'date_joined', 'updated_at', 'memberships',
        ]

    def get_decrypted_id_number(self, obj) -> str | None:
        if obj.id_number:
            return decrypt_field(obj.id_number)
        return None

    def get_member_number(self, obj):
        primary = obj.primary_membership
        return primary.member_number if primary else ''

    def _get_primary_field(self, obj, field):
        primary = obj.primary_membership
        if primary:
            return getattr(primary, field, '')
        return ''

    def get_payment_method(self, obj):
        return self._get_primary_field(obj, 'payment_method')

    def get_mpesa_number(self, obj):
        return self._get_primary_field(obj, 'mpesa_number')

    def get_bank_name(self, obj):
        return self._get_primary_field(obj, 'bank_name')

    def get_bank_account(self, obj):
        return self._get_primary_field(obj, 'bank_account')

    def get_bank_branch(self, obj):
        return self._get_primary_field(obj, 'bank_branch')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop('id_number', None)
        return data


class FarmerCreateSerializer(serializers.ModelSerializer):
    cooperative_id = serializers.UUIDField(required=False, write_only=True)
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
        validators=[_validate_lat],
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
        validators=[_validate_lng],
    )

    class Meta:
        model = Farmer
        fields = [
            'first_name', 'last_name', 'email', 'id_number', 'phone_number',
            'date_of_birth', 'county', 'sub_county',
            'ward', 'village',
            'latitude', 'longitude',
            'cooperative_id',
        ]
        extra_kwargs = {
            'first_name': {'min_length': 1},
        }

    def validate_cooperative_id(self, value):
        if not Cooperative.objects.filter(id=value).exists():
            raise serializers.ValidationError('Cooperative not found.')
        return value

    def validate_phone_number(self, value):
        value = normalize_phone(value)
        if not KENYA_PHONE_RE.match(value):
            raise serializers.ValidationError(
                'Enter a valid Kenyan phone number (e.g. 0712345678 or +254712345678).'
            )
        qs = User.objects.filter(phone_number=value)
        if self.instance and self.instance.user:
            qs = qs.exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise serializers.ValidationError('A user with this phone number already exists.')
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

    def create(self, validated_data):
        if validated_data.get('id_number'):
            validated_data['id_number'] = encrypt_field(validated_data['id_number'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('cooperative_id', None)
        if 'id_number' in validated_data and validated_data['id_number']:
            validated_data['id_number'] = encrypt_field(validated_data['id_number'])
        name_fields = {k: validated_data[k] for k in ('first_name', 'last_name') if k in validated_data}
        if name_fields and instance.user:
            User.objects.filter(pk=instance.user.pk).update(**name_fields)
        return super().update(instance, validated_data)


class FarmerSelfUpdateSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
        validators=[_validate_lat],
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
        validators=[_validate_lng],
    )

    class Meta:
        model = Farmer
        fields = [
            'phone_number', 'email',
            'village', 'ward', 'sub_county',
            'latitude', 'longitude',
        ]
        extra_kwargs = {field: {'required': False} for field in fields}


class FarmerLocationPatchSerializer(serializers.Serializer):
    """Used by the FarmerViewSet.location action PATCH body."""
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
        validators=[_validate_lat],
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
        validators=[_validate_lng],
    )

    def validate(self, attrs):
        lat = attrs.get('latitude')
        lng = attrs.get('longitude')
        if (lat is None) ^ (lng is None):
            raise serializers.ValidationError(
                'Both latitude and longitude must be provided together.'
            )
        return attrs

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
