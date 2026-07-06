from PIL import Image
from rest_framework import serializers

from apps.cooperatives.models import Cooperative
from .models import Grade, GradeImage, GradePrice, FarmerGradeDispute


def validate_delivery_scoped(value, request, instance=None):
    if instance is None and value.status != 'PENDING':
        raise serializers.ValidationError(
            'Only PENDING deliveries can be graded.'
        )
    if request and value.cooperative_id != request.cooperative_id:
        raise serializers.ValidationError(
            'Delivery does not belong to your cooperative.'
        )
    if hasattr(value, 'grade_record'):
        if instance and value.grade_record.id == instance.id:
            return value
        raise serializers.ValidationError(
            'This delivery already has a grade.'
        )
    return value


class GradeImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GradeImage
        fields = ['id', 'image', 'image_url', 'caption', 'uploaded_by_name', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_by', 'uploaded_at']

    def get_image_url(self, obj):
        return obj.image.url

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.email
        return None

    def validate_image(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Image size must not exceed 5MB.')

        value.seek(0)
        try:
            image = Image.open(value)
        except Exception:
            raise serializers.ValidationError('Uploaded file is not a valid image.')
        finally:
            value.seek(0)

        if image.format not in ('JPEG', 'PNG'):
            raise serializers.ValidationError(
                'Unsupported image format. Only JPEG and PNG images are allowed.'
            )
        if max(image.width, image.height) < 300:
            raise serializers.ValidationError(
                f'Image longest edge must be at least 300 pixels. '
                f'Got {image.width}×{image.height}.'
            )

        return value


class GradeListSerializer(serializers.ModelSerializer):
    batch_id = serializers.CharField(source='delivery.batch_id', read_only=True)
    farmer_name = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [
            'id', 'delivery', 'batch_id', 'farmer_name',
            'grade_letter', 'price_per_unit', 'rejection_reason',
            'is_overridden', 'overridden_at', 'override_reason',
            'created_at', 'updated_at',
        ]

    def get_farmer_name(self, obj):
        return f'{obj.delivery.farmer.first_name} {obj.delivery.farmer.last_name}'


class GradeDetailSerializer(serializers.ModelSerializer):
    batch_id = serializers.CharField(source='delivery.batch_id', read_only=True)
    farmer_name = serializers.SerializerMethodField()
    product_type = serializers.CharField(source='delivery.product_type', read_only=True)
    images = GradeImageSerializer(many=True, read_only=True)

    class Meta:
        model = Grade
        fields = '__all__'
        read_only_fields = [
            'id', 'delivery', 'is_overridden', 'overridden_by',
            'overridden_at', 'cooperative', 'created_at', 'updated_at',
        ]

    def get_farmer_name(self, obj):
        return f'{obj.delivery.farmer.first_name} {obj.delivery.farmer.last_name}'


class GradeCreateSerializer(serializers.ModelSerializer):
    cooperative_id = serializers.UUIDField(required=False, write_only=True)

    class Meta:
        model = Grade
        fields = [
            'delivery', 'grade_letter', 'price_per_unit', 'rejection_reason',
            'cooperative_id',
        ]
        extra_kwargs = {
            'grade_letter': {'required': False},
            'price_per_unit': {'required': False},
        }

    def validate_cooperative_id(self, value):
        if not Cooperative.objects.filter(id=value).exists():
            raise serializers.ValidationError('Cooperative not found.')
        return value

    def validate_delivery(self, value):
        return validate_delivery_scoped(
            value, request=self.context.get('request'), instance=self.instance,
        )

    def validate(self, attrs):
        has_grade = bool(attrs.get('grade_letter'))
        has_rejection = bool(attrs.get('rejection_reason'))

        if has_grade and has_rejection:
            raise serializers.ValidationError(
                'Cannot assign a grade and a rejection reason. '
                'Use rejection_reason only for rejected deliveries.'
            )
        if not has_grade and not has_rejection:
            raise serializers.ValidationError(
                'Provide either a grade_letter or a rejection_reason.'
            )
        if has_grade and not attrs.get('price_per_unit'):
            raise serializers.ValidationError(
                {'price_per_unit': 'Price per unit is required when assigning a grade.'}
            )
        return attrs


class GradeOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = [
            'grade_letter', 'price_per_unit', 'rejection_reason', 'override_reason',
        ]
        extra_kwargs = {
            'grade_letter': {'required': False},
            'price_per_unit': {'required': False},
        }

    def validate(self, attrs):
        if not attrs.get('override_reason'):
            raise serializers.ValidationError(
                {'override_reason': 'Override reason is required.'}
            )
        if attrs.get('grade_letter') and attrs.get('rejection_reason'):
            raise serializers.ValidationError(
                'Cannot set a grade letter and a rejection reason together.'
            )
        if attrs.get('grade_letter') and not attrs.get('price_per_unit'):
            raise serializers.ValidationError(
                {'price_per_unit': 'Price per unit is required when assigning a grade.'}
            )
        return attrs


class GradePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradePrice
        fields = ['id', 'grade_letter', 'price_per_unit', 'effective_from', 'created_at']
        read_only_fields = ['id', 'created_at']


class GradeDisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerGradeDispute
        fields = ['id', 'grade', 'reason', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']


class GradeDisputeResolveSerializer(serializers.Serializer):
    resolution = serializers.ChoiceField(
        choices=['RESOLVED', 'REJECTED'], default='RESOLVED', required=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    override_grade = serializers.BooleanField(default=False, required=False)
    new_grade_letter = serializers.ChoiceField(
        choices=['A', 'B', 'C', 'PREMIUM', 'STANDARD'],
        required=False, allow_null=True,
    )
    new_price_per_unit = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True, min_value=0,
    )

    def validate(self, attrs):
        unknown = set(self.initial_data) - {'resolution', 'notes', 'override_grade', 'new_grade_letter', 'new_price_per_unit'}
        if unknown:
            raise serializers.ValidationError(
                f"Unknown fields: {', '.join(sorted(unknown))}"
            )
        if attrs.get('override_grade'):
            if not attrs.get('new_grade_letter'):
                raise serializers.ValidationError(
                    {'new_grade_letter': 'Required when override_grade is true.'}
                )
        return attrs
