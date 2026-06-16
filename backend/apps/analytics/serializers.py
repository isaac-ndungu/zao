from rest_framework import serializers


class AnalyticsQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(
        choices=['24h', '7d', '30d', '90d', '1y', 'all'],
        required=False, default='30d',
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    compare_to = serializers.ChoiceField(
        choices=['previous'],
        required=False,
    )


class AnalyticsResponseSerializer(serializers.Serializer):
    period = serializers.DictField()
    data = serializers.DictField()
    comparison = serializers.DictField(required=False)
    cached = serializers.BooleanField(read_only=True, default=False)
    cached_at = serializers.DateTimeField(read_only=True, required=False)


class LeaderboardQuerySerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=['top_farmers_by_volume', 'top_farmers_by_payout', 'top_buyers'],
        required=False, default='top_farmers_by_volume',
    )
    limit = serializers.IntegerField(required=False, default=10, min_value=1, max_value=100)
    period = serializers.ChoiceField(
        choices=['7d', '30d', '90d', '1y', 'all'],
        required=False, default='30d',
    )


class ExportQuerySerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=['dashboard', 'production', 'financial', 'farmers',
                 'sales', 'loans', 'operations', 'disbursements'],
        required=True,
    )
    format = serializers.ChoiceField(
        choices=['csv'],
        default='csv',
    )
    period = serializers.ChoiceField(
        choices=['7d', '30d', '90d', '1y', 'all'],
        required=False, default='30d',
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
