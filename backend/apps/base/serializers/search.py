from rest_framework import serializers


class SearchResultEntrySerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    label = serializers.CharField()
    subtitle = serializers.CharField()
    url = serializers.CharField()


class SearchResultGroupSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    icon = serializers.CharField()
    total = serializers.IntegerField()
    items = SearchResultEntrySerializer(many=True)


class GlobalSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    results = SearchResultGroupSerializer(many=True)
