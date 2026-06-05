from rest_framework import serializers

from .models import CollectionRoute, DayOfWeekChoices, RouteStop


class RouteStopSerializer(serializers.Serializer):
    farmer_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False,
    )
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    stop_order = serializers.IntegerField(min_value=1)
    estimated_minutes = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class RouteStopDetailSerializer(serializers.ModelSerializer):
    farmer_ids = serializers.SerializerMethodField()

    class Meta:
        model = RouteStop
        fields = ['id', 'latitude', 'longitude', 'stop_order', 'estimated_minutes', 'farmer_ids']

    def get_farmer_ids(self, obj):
        return list(obj.farmers.values_list('id', flat=True))


class RouteListSerializer(serializers.ModelSerializer):
    farmer_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CollectionRoute
        fields = [
            'id', 'name', 'farmer_count', 'estimated_distance_km',
            'is_active', 'day_of_week', 'created_at',
        ]


class RouteDetailSerializer(serializers.ModelSerializer):
    stops = RouteStopDetailSerializer(many=True, read_only=True)

    class Meta:
        model = CollectionRoute
        fields = '__all__'
        read_only_fields = ['id', 'cooperative', 'created_at', 'updated_at']


class RouteWriteSerializer(serializers.ModelSerializer):
    day_of_week = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = CollectionRoute
        fields = [
            'name', 'description', 'path', 'is_active',
            'estimated_distance_km', 'day_of_week',
        ]

    def validate_path(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Path must be a JSON object.')
        if value.get('type') != 'LineString':
            raise serializers.ValidationError('Path must be a GeoJSON LineString.')
        coords = value.get('coordinates', [])
        if len(coords) < 2:
            raise serializers.ValidationError('Path must have at least 2 coordinates.')
        for coord in coords:
            if not isinstance(coord, (list, tuple)) or len(coord) != 2:
                raise serializers.ValidationError('Each coordinate must be [lng, lat].')
        return value

    def validate_day_of_week(self, value):
        if not value:
            return value
        try:
            return DayOfWeekChoices.from_string(value)
        except ValueError:
            raise serializers.ValidationError(
                f'"{value}" is not a valid day of week.'
            )


class RouteAssignSerializer(serializers.Serializer):
    stops = RouteStopSerializer(many=True, allow_empty=False)

    def validate_stops(self, value):
        orders = [s['stop_order'] for s in value]
        if sorted(orders) != list(range(1, len(orders) + 1)):
            raise serializers.ValidationError(
                'stop_order must be sequential starting from 1 with no gaps or duplicates.'
            )
        return value
