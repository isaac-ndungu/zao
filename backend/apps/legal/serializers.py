from rest_framework import serializers

from .models import LegalAcceptance, LegalDocument


class LegalDocumentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = ['id', 'slug', 'title', 'version', 'published_at']


class LegalDocumentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = ['id', 'slug', 'title', 'content', 'version', 'requires_acceptance', 'published_at', 'updated_at']


class LegalAcceptanceInputSerializer(serializers.Serializer):
    """Input schema for POST /api/legal/<slug>/accept/.

    ``version`` is optional. When supplied, the view verifies that it
    matches the currently active version's version — a mismatch returns
    400 so the client can refresh the page and re-read the document.
    """
    slug = serializers.SlugField()
    version = serializers.IntegerField(required=False, min_value=1)


class MyAcceptanceSerializer(serializers.Serializer):
    """Read-only response for GET /api/legal/<slug>/my-acceptance/."""
    accepted = serializers.BooleanField()
    accepted_version = serializers.IntegerField(allow_null=True)
    accepted_at = serializers.DateTimeField(allow_null=True)
    current_version = serializers.IntegerField()


class LegalAcceptanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalAcceptance
        fields = ['id', 'document', 'version', 'accepted_at']


class PendingLegalDocumentSerializer(serializers.Serializer):
    slug = serializers.SlugField()
    title = serializers.CharField()
    version = serializers.IntegerField()


class LegalDocumentAdminSerializer(serializers.ModelSerializer):
    """Full admin serializer for LegalDocument (all fields, writable).

    `published_at` is intentionally read-only here: the `publish`
    action on the viewset creates a new versioned row and sets
    `published_at` there. That keeps version history intact and
    prevents admins from silently re-publishing an old version.
    """
    class Meta:
        model = LegalDocument
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'published_at']


class LegalAcceptanceAdminSerializer(serializers.ModelSerializer):
    """Read-only admin log serializer with denormalized user/doc fields."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    document_slug = serializers.CharField(source='document.slug', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)

    class Meta:
        model = LegalAcceptance
        fields = [
            'id', 'user', 'user_email', 'document', 'document_slug', 'document_title',
            'version', 'accepted_at', 'ip_address', 'user_agent',
        ]
        read_only_fields = fields
