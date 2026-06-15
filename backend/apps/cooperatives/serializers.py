from rest_framework import serializers
from apps.cooperatives.models import Cooperative


class CooperativeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cooperative
        fields = [
            'id', 'name', 'registration_number', 'county',
            'produce_type', 'payment_model', 'is_active',
            'is_verified', 'member_count', 'logo',
        ]


class CooperativeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cooperative
        fields = '__all__'

    def validate_levy_percentage(self, value):
        if value > 100:
            raise serializers.ValidationError(
                'Levy percentage must not exceed 100.'
            )
        return value

    def validate_registration_number(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                'Registration number is required.'
            )

        qs = Cooperative.objects.filter(registration_number__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'Cooperative with this registration number already exists.'
            )
        return value

    def validate_prefix(self, value):
        if not value:
            return value
        qs = Cooperative.objects.filter(prefix__iexact=value.strip())
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError(
                f'The prefix "{value}" is already in use by another cooperative.'
            )
        return value
