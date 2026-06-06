import csv
import io
import secrets

from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVector, TrigramSimilarity,
)
from django.db import transaction
from django.db.models import Count, Q
from django.utils.crypto import get_random_string
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
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


def _create_farmer_user(farmer, cooperative_id):
    """Create a linked User with unusable password for a farmer."""
    email = farmer.email or f'farmer_{farmer.id}@placeholder.local'
    user = User.objects.create_user(
        email=email,
        phone_number=farmer.phone_number,
        first_name=farmer.first_name,
        last_name=farmer.last_name,
        password=get_random_string(length=72),
        role=UserRole.FARMER,
        cooperative_id=cooperative_id,
    )
    user.set_unusable_password()
    user.save(update_fields=['password'])
    farmer.user = user
    farmer.save(update_fields=['user'])
    return user


class FarmerViewSet(CooperativeScopedViewSet):
    queryset = Farmer.objects.all().select_related('cooperative', 'user')
    filter_backends = [OrderingFilter]
    ordering_fields = [
        'first_name', 'last_name', 'member_number',
        'date_joined', 'phone_number',
    ]
    ordering = ['first_name']

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.query_params.get('q', '').strip()
        if query:
            if len(query) < 3:
                qs = qs.filter(
                    Q(first_name__icontains=query)
                    | Q(last_name__icontains=query)
                    | Q(member_number__icontains=query)
                )
            else:
                search_vector = SearchVector('first_name', 'last_name', 'member_number')
                search_query = SearchQuery(query)
                qs = (
                    qs.annotate(
                        rank=SearchRank(search_vector, search_query),
                        similarity=TrigramSimilarity('last_name', query),
                    )
                    .filter(Q(rank__gte=0.1) | Q(similarity__gte=0.3))
                )
        for param in ('first_name', 'last_name', 'county', 'sub_county', 'ward', 'village', 'payment_method'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs

    def filter_queryset(self, qs):
        qs = super().filter_queryset(qs)
        query = self.request.query_params.get('q', '').strip()
        if query and len(query) >= 3:
            qs = qs.order_by('-rank', '-similarity')
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

        instance = serializer.save(
            cooperative_id=cooperative_id,
        )

        _create_farmer_user(instance, cooperative_id)

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

        if request.method == 'PATCH':
            if not farmer:
                return Response(
                    {'error': 'No farmer profile linked to this user.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = FarmerSelfUpdateSerializer(
                farmer, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            log_audit(
                actor=request.user,
                resource_type='farmer',
                resource_id=farmer.id,
                action='UPDATE',
                new_value=serializer.validated_data,
                cooperative_id=request.cooperative_id,
            )
            return Response(
                FarmerDetailSerializer(farmer, context={'request': request}).data
            )

        if not farmer:
            return Response(
                {'error': 'No farmer profile linked to this user.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            FarmerDetailSerializer(farmer, context={'request': request}).data
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = self.get_queryset().count()
        active = self.get_queryset().filter(is_active=True).count()
        with_loans = self.get_queryset().filter(has_active_loan=True).count()
        return Response({
            'total': total,
            'active': active,
            'with_active_loans': with_loans,
        })

    @action(detail=False, methods=['get'])
    def import_template(self, request):
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="farmer_import_template.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            'first_name', 'last_name', 'email', 'id_number',
            'phone_number', 'mpesa_number', 'date_of_birth',
            'county', 'sub_county', 'ward', 'village',
            'payment_method', 'bank_name', 'bank_account', 'bank_branch',
        ])
        writer.writerow([
            'Jane', 'Wanjiku', 'jane.wanjiku@example.com', '12345678',
            '0712345678', '0712345678', '1990-01-15',
            'Kiambu', 'Kikuyu', 'Karuna', 'Gitaru',
            'M-PESA', '', '', '',
        ])
        return response

    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided.'}, status=400)

        max_size = 5 * 1024 * 1024
        if file.size > max_size:
            return Response(
                {'error': 'File size exceeds 5MB limit.'},
                status=400,
            )

        decoded = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        rows = list(reader)

        if not rows:
            return Response({'error': 'CSV file is empty.'}, status=400)

        errors = []
        created = []

        with transaction.atomic():
            for row_num, row in enumerate(rows, start=2):
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

                    instance = serializer.save(cooperative_id=coop_id)
                    _create_farmer_user(instance, coop_id)
                    created.append({
                        'row': row_num,
                        'member_number': instance.member_number,
                        'name': f'{instance.first_name} {instance.last_name}',
                    })
                except Exception as e:
                    errors.append({'row': row_num, 'error': str(e)})

            if errors:
                raise ValueError('rollback')

        if errors:
            return Response(
                {'error': 'CSV import failed. No rows imported.', 'errors': errors},
                status=400,
            )

        return Response({
            'message': f'{len(created)} farmer(s) imported successfully.',
            'created': created,
        })
