from rest_framework import serializers

from .models import LegalDocument, LegalAcceptance


class LegalDocumentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = ['id', 'slug', 'title', 'version', 'published_at']


class LegalDocumentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = ['id', 'slug', 'title', 'content', 'version', 'requires_acceptance', 'published_at', 'updated_at']


class LegalAcceptanceInputSerializer(serializers.Serializer):
    slug = serializers.SlugField()


class LegalAcceptanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalAcceptance
        fields = ['id', 'document', 'version', 'accepted_at']


class PendingLegalDocumentSerializer(serializers.Serializer):
    slug = serializers.SlugField()
    title = serializers.CharField()
    version = serializers.IntegerField()
