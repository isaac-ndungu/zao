from rest_framework import serializers
from apps.cooperatives.models import Cooperative


class CooperativeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cooperative
        fields = [
            'id', 'name', 'registration_number', 'county',
            'produce_type', 'payment_model', 'is_active',
        ]


class CooperativeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cooperative
        fields = '__all__'
