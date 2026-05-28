import csv
import io
import secrets

from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auth_api.models import User
from apps.base.constants import UserRole
from apps.base.permissions import IsManager
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet

from .models import Farmer
from .serializers import (
    FarmerCreateSerializer,
    FarmerDetailSerializer,
    FarmerListSerializer,
    FarmerSelfUpdateSerializer,
)


class FarmerViewSet(CooperativeScopedViewSet):
    queryset = Farmer.objects.all().select_related('cooperative', 'user')
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        'first_name', 'last_name', 'member_number',
        'phone_number', 'mpesa_number',
    ]
    ordering_fields = [
        'first_name', 'last_name', 'member_number',
        'date_joined', 'phone_number',
    ]
    ordering = ['first_name']

    def get_queryset(self):
        qs = super().get_queryset()
        for param in ('first_name', 'last_name', 'county', 'sub_county', 'ward', 'village', 'payment_method'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'import_csv'):
            return [IsAuthenticated(), IsManager()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return FarmerCreateSerializer
        if self.action in ('update', 'partial_update'):
            return FarmerCreateSerializer
        if self.action == 'list':
            return FarmerListSerializer
        return FarmerDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if getattr(request.user, 'role', None) == 'admin':
            cooperative_id = serializer.validated_data.pop('cooperative_id', None) or request.cooperative_id
        else:
            serializer.validated_data.pop('cooperative_id', None)
            cooperative_id = request.cooperative_id
        user_id = serializer.validated_data.pop('user_id', None)
        user_email = serializer.validated_data.pop('user_email', None)
        user = None
        temp_password = None

        if user_id:
            user = User.objects.get(id=user_id)
        elif user_email:
            password = secrets.token_urlsafe(6)
            user = User.objects.create_user(
                email=user_email,
                phone_number=serializer.validated_data.get('phone_number', ''),
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', ''),
                password=password,
                role=UserRole.FARMER,
                cooperative_id=request.cooperative_id,
            )
            temp_password = password

        instance = serializer.save(
            cooperative_id=cooperative_id,
            user=user,
        )

        log_audit(
            actor=request.user,
            resource_type='farmer',
            resource_id=instance.id,
            action='CREATE',
            new_value={
                'member_number': instance.member_number,
                'name': f'{instance.first_name} {instance.last_name}',
            },
            cooperative_id=request.cooperative_id,
        )

        response_serializer = FarmerDetailSerializer(
            instance, context={'request': request}
        )
        data = response_serializer.data
        if temp_password:
            data['temp_password'] = temp_password

        return Response(data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='farmer',
            resource_id=instance.id,
            action='UPDATE',
            previous_value={
                'member_number': instance.member_number,
            },
            new_value=serializer.validated_data,
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type='farmer',
            resource_id=instance.id,
            action='DELETE',
            previous_value={
                'member_number': instance.member_number,
                'name': f'{instance.first_name} {instance.last_name}',
            },
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        farmer = getattr(request.user, 'farmer_profile', None)
        if not farmer:
            return Response(
                {'detail': 'No farmer profile found.'}, status=404
            )

        if request.method == 'PATCH':
            serializer = FarmerSelfUpdateSerializer(
                farmer, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(FarmerDetailSerializer(farmer).data)

    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided.'}, status=400)

        decoded = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))

        created = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                data = {
                    'first_name': row.get('first_name', '').strip(),
                    'last_name': row.get('last_name', '').strip(),
                    'email': row.get('email', '').strip(),
                    'id_number': row.get('id_number', '').strip(),
                    'phone_number': row.get('phone_number', '').strip(),
                    'mpesa_number': row.get('mpesa_number', '').strip(),
                    'county': row.get('county', '').strip(),
                    'sub_county': row.get('sub_county', '').strip(),
                    'ward': row.get('ward', '').strip(),
                    'village': row.get('village', '').strip(),
                    'payment_method': row.get('payment_method', 'M-PESA').strip(),
                    'bank_name': row.get('bank_name', '').strip(),
                    'bank_account': row.get('bank_account', '').strip(),
                    'bank_branch': row.get('bank_branch', '').strip(),
                    'is_active': True,
                }
                date_of_birth = row.get('date_of_birth', '').strip()
                if date_of_birth:
                    data['date_of_birth'] = date_of_birth

                serializer = FarmerCreateSerializer(data=data)
                serializer.is_valid(raise_exception=True)
                if getattr(request.user, 'role', None) == 'admin':
                    coop_id = serializer.validated_data.pop('cooperative_id', None) or request.cooperative_id
                else:
                    serializer.validated_data.pop('cooperative_id', None)
                    coop_id = request.cooperative_id
                serializer.validated_data.pop('user_id', None)
                serializer.validated_data.pop('user_email', None)
                serializer.save(
                    cooperative_id=coop_id,
                )
                created += 1
            except Exception as e:
                errors.append({'row': row_num, 'error': str(e)})

        return Response({'created': created, 'errors': errors})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'active': qs.filter(is_active=True).count(),
            'by_payment_method': qs.values('payment_method').annotate(
                count=Count('id')
            ),
            'by_county': qs.values('county').annotate(count=Count('id')),
        })
