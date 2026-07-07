from rest_framework import serializers

from .models import CollectionRoute, DayOfWeekChoices, RouteStop


def build_path_from_stops(stops_qs):
    """Build a GeoJSON LineString from an ordered queryset of RouteStops."""
    coords = [
        [float(s.longitude), float(s.latitude)]
        for s in stops_qs.order_by('stop_order')
    ]
    if len(coords) < 2:
        return {}
    return {'type': 'LineString', 'coordinates': coords}


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
    farmer_names = serializers.SerializerMethodField()
    route_id = serializers.SerializerMethodField()
    route_name = serializers.SerializerMethodField()

    class Meta:
        model = RouteStop
        fields = [
            'id', 'latitude', 'longitude', 'stop_order', 'estimated_minutes',
            'farmer_ids', 'farmer_names', 'route_id', 'route_name',
        ]

    def get_farmer_ids(self, obj):
        return [str(f.id) for f in obj.farmers.all()]

    def get_farmer_names(self, obj):
        return [f'{f.first_name} {f.last_name}' for f in obj.farmers.all()]

    def get_route_id(self, obj):
        return str(obj.route_id)

    def get_route_name(self, obj):
        return obj.route.name


class RouteListSerializer(serializers.ModelSerializer):
    farmer_count = serializers.IntegerField(read_only=True)
    stop_count = serializers.SerializerMethodField()

    class Meta:
        model = CollectionRoute
        fields = [
            'id', 'name', 'farmer_count', 'stop_count', 'estimated_distance_km',
            'is_active', 'day_of_week', 'created_at',
        ]

    def get_stop_count(self, obj):
        return obj.stops.count()


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
        if not value:
            return value
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


class RouteMapSerializer(serializers.ModelSerializer):
    stops = serializers.SerializerMethodField()

    class Meta:
        model = CollectionRoute
        fields = [
            'id', 'name', 'description', 'day_of_week', 'is_active',
            'estimated_distance_km', 'path', 'stops', 'created_at', 'updated_at',
        ]

    def get_stops(self, obj):
        return [
            {
                'id': str(s.id),
                'order': s.stop_order,
                'lat': float(s.latitude),
                'lng': float(s.longitude),
                'estimated_minutes': s.estimated_minutes,
                'farmers': [
                    {
                        'id': str(f.id),
                        'name': f'{f.first_name} {f.last_name}',
                        'phone_number': f.phone_number,
                        'member_number': (
                            f.primary_membership.member_number
                            if f.primary_membership else ''
                        ),
                    }
                    for f in s.farmers.all()
                ],
            }
            for s in obj.stops.all().prefetch_related('farmers')
        ]


class RouteAssignFarmerSerializer(serializers.Serializer):
    farmer_id = serializers.UUIDField()
    stop_id = serializers.IntegerField()


class RouteUnassignFarmerSerializer(serializers.Serializer):
    farmer_id = serializers.UUIDField()
