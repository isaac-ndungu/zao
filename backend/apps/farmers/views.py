import csv
import io
import secrets
import uuid

from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVector, TrigramSimilarity,
)
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
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
from apps.base.export_mixins import CsvExportMixin

from .models import Farmer, FarmerCooperativeMembership
from .pagination import FarmerPagination
from apps.base.idempotency import idempotent
from .serializers import (
    FarmerCreateSerializer,
    FarmerDetailSerializer,
    FarmerListSerializer,
    FarmerSelfUpdateSerializer,
    MembershipCreateSerializer,
    MembershipSerializer,
)


def _create_farmer_user(farmer, cooperative_id):
    email = farmer.email or f'farmer_{farmer.id}@placeholder.local'
    user = User(
        email=email,
        phone_number=farmer.phone_number,
        first_name=farmer.first_name,
        last_name=farmer.last_name,
        role=UserRole.FARMER,
        cooperative_id=cooperative_id,
    )
    user.set_unusable_password()
    user.save()
    farmer.user = user
    farmer.save(update_fields=['user'])
    return user


class FarmerViewSet(CsvExportMixin, CooperativeScopedViewSet):
    csv_filename = 'farmers.csv'
    queryset = Farmer.objects.all().select_related('cooperative', 'user')
    pagination_class = FarmerPagination
    filter_backends = [OrderingFilter]
    ordering_fields = [
        'first_name', 'last_name',
        'date_joined', 'phone_number',
    ]
    ordering = ['first_name']

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', None) == 'admin':
            qs = self.queryset
        else:
            qs = self.queryset.filter(
                memberships__cooperative_id=self.request.cooperative_id,
                memberships__is_active=True,
            ).distinct()

        query = self.request.query_params.get('q', '').strip()
        if query:
            if len(query) < 3:
                qs = qs.filter(
                    Q(first_name__icontains=query)
                    | Q(last_name__icontains=query)
                    | Q(memberships__member_number__icontains=query)
                )
            else:
                search_vector = SearchVector('first_name', 'last_name')
                search_query = SearchQuery(query)
                qs = (
                    qs.annotate(
                        rank=SearchRank(search_vector, search_query),
                        similarity=TrigramSimilarity('last_name', query),
                    )
                    .filter(Q(rank__gte=0.1) | Q(similarity__gte=0.3))
                )
        for param in ('first_name', 'last_name', 'county', 'sub_county', 'ward', 'village'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        is_active = self.request.query_params.get('is_active')
        if is_active:
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
        if self.action in ('lookup',):
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

    @idempotent()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if getattr(request.user, 'role', None) == 'admin':
            cooperative_id = serializer.validated_data.pop('cooperative_id', None) or request.cooperative_id
        else:
            serializer.validated_data.pop('cooperative_id', None)
            cooperative_id = request.cooperative_id

        instance = serializer.save(cooperative_id=cooperative_id)

        _create_farmer_user(instance, cooperative_id)

        log_audit(
            actor=request.user,
            resource_type='farmer',
            resource_id=instance.id,
            action='CREATE',
            new_value={
                'name': f'{instance.first_name} {instance.last_name}',
                'phone': instance.phone_number,
            },
            cooperative_id=request.cooperative_id,
        )

        response_serializer = FarmerDetailSerializer(
            instance, context={'request': request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='farmer',
            resource_id=instance.id,
            action='UPDATE',
            previous_value={},
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
                'name': f'{instance.first_name} {instance.last_name}',
            },
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()

    @action(detail=False, methods=['get'])
    def lookup(self, request):
        phone = request.query_params.get('phone', '').strip()
        name = request.query_params.get('name', '').strip()
        if not phone and not name:
            return Response(
                {'error': 'Either phone or name query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        farmers = Farmer.objects.none()
        if phone:
            phone_clean = phone.lstrip('+')
            farmers = Farmer.objects.filter(phone_number__endswith=phone_clean)
        elif name:
            parts = name.split()
            if len(parts) == 1:
                farmers = Farmer.objects.filter(
                    first_name__icontains=parts[0]
                ) | Farmer.objects.filter(
                    last_name__icontains=parts[0]
                )
                farmers = farmers.distinct()
            else:
                farmers = Farmer.objects.filter(
                    first_name__icontains=parts[0],
                    last_name__icontains=parts[-1],
                )
        if not farmers.exists():
            return Response(
                {'error': 'Farmer not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        def serialize(f):
            primary = f.primary_membership
            return {
                'id': f.id,
                'first_name': f.first_name,
                'last_name': f.last_name,
                'phone_number': f.phone_number,
                'member_number': primary.member_number if primary else None,
                'primary_cooperative_name': f.cooperative.name if f.cooperative_id else None,
                'existing_memberships': [
                    {
                        'cooperative_id': str(m.cooperative_id),
                        'member_number': m.member_number,
                        'is_active': m.is_active,
                    }
                    for m in f.memberships.all()
                ],
            }

        return Response({
            'results': [serialize(f) for f in farmers],
        })

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
        ])
        writer.writerow([
            'Jane', 'Wanjiku', 'jane.wanjiku@example.com', '12345678',
            '0712345678', '0712345678', '1990-01-15',
            'Kiambu', 'Kikuyu', 'Karuna', 'Gitaru',
        ])
        return response

    @idempotent()
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
        created_farmers = []
        linked_farmers = []

        with transaction.atomic():
            for row_num, row in enumerate(rows, start=2):
                try:
                    phone = normalize_phone_for_csv(row.get('phone_number', '').strip())
                    existing = Farmer.objects.filter(phone_number=phone).first() if phone else None

                    if existing:
                        coop_id = request.cooperative_id
                        if getattr(request.user, 'role', None) == 'admin':
                            coop_id = row.get('cooperative_id', '').strip() or request.cooperative_id

                        if FarmerCooperativeMembership.objects.filter(
                            farmer=existing, cooperative_id=coop_id
                        ).exists():
                            linked_farmers.append({
                                'row': row_num,
                                'member_number': existing.primary_membership.member_number if existing.primary_membership else 'N/A',
                                'name': f'{existing.first_name} {existing.last_name}',
                                'status': 'already_member',
                            })
                        else:
                            FarmerCooperativeMembership.objects.create(
                                farmer=existing,
                                cooperative_id=coop_id,
                                payment_method=row.get('payment_method', 'M-PESA').strip() or 'M-PESA',
                                mpesa_number=normalize_phone_for_csv(row.get('mpesa_number', '').strip()) or phone,
                                bank_name=row.get('bank_name', '').strip(),
                                bank_account=row.get('bank_account', '').strip(),
                                bank_branch=row.get('bank_branch', '').strip(),
                            )
                            linked_farmers.append({
                                'row': row_num,
                                'member_number': existing.primary_membership.member_number if existing.primary_membership else 'N/A',
                                'name': f'{existing.first_name} {existing.last_name}',
                                'status': 'membership_added',
                            })
                    else:
                        mpesa_number = normalize_phone_for_csv(row.get('mpesa_number', '').strip()) or phone
                        data = {
                            'first_name': row.get('first_name', '').strip(),
                            'last_name': row.get('last_name', '').strip(),
                            'email': row.get('email', '').strip(),
                            'id_number': row.get('id_number', '').strip(),
                            'phone_number': phone,
                            'date_of_birth': row.get('date_of_birth', '').strip(),
                            'county': row.get('county', '').strip(),
                            'sub_county': row.get('sub_county', '').strip(),
                            'ward': row.get('ward', '').strip(),
                            'village': row.get('village', '').strip(),
                        }

                        serializer = FarmerCreateSerializer(data=data)
                        serializer.is_valid(raise_exception=True)
                        if getattr(request.user, 'role', None) == 'admin':
                            coop_id = serializer.validated_data.pop('cooperative_id', None) or request.cooperative_id
                        else:
                            serializer.validated_data.pop('cooperative_id', None)
                            coop_id = request.cooperative_id

                        instance = serializer.save(cooperative_id=coop_id)
                        _create_farmer_user(instance, coop_id)

                        # Update the auto-created membership with payment details
                        membership = instance.memberships.filter(cooperative_id=coop_id).first()
                        if membership:
                            membership.mpesa_number = mpesa_number
                            membership.payment_method = row.get('payment_method', 'M-PESA').strip() or 'M-PESA'
                            membership.bank_name = row.get('bank_name', '').strip()
                            membership.bank_account = row.get('bank_account', '').strip()
                            membership.bank_branch = row.get('bank_branch', '').strip()
                            membership.save(update_fields=[
                                'mpesa_number', 'payment_method', 'bank_name',
                                'bank_account', 'bank_branch',
                            ])

                        created_farmers.append({
                            'row': row_num,
                            'member_number': instance.primary_membership.member_number if instance.primary_membership else 'N/A',
                            'name': f'{instance.first_name} {instance.last_name}',
                        })

                except Exception as e:
                    errors.append({'row': row_num, 'error': str(e)})

            if errors:
                transaction.set_rollback(True)

        if errors:
            return Response(
                {'error': 'CSV import failed. No rows imported.', 'errors': errors},
                status=400,
            )

        result = {'message': f'{len(created_farmers)} farmer(s) created, {len(linked_farmers)} linked.'}
        if created_farmers:
            result['created_farmers'] = created_farmers
        if linked_farmers:
            result['linked_farmers'] = linked_farmers
        return Response(result)


def normalize_phone_for_csv(value):
    if not value:
        return ''
    if value.startswith('+'):
        value = value[1:]
    if value.startswith('0'):
        value = '254' + value[1:]
    return value


class MembershipViewSet(CsvExportMixin, CooperativeScopedViewSet):
    csv_filename = 'memberships.csv'
    queryset = FarmerCooperativeMembership.objects.all().select_related(
        'farmer', 'cooperative'
    )

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update'):
            return [IsAuthenticated(), IsManager()]
        return [IsAuthenticated()]

    def get_serializer(self, *args, **kwargs):
        if self.action == 'create' and 'farmer_pk' in self.kwargs:
            kwargs.setdefault('context', {})['farmer'] = get_object_or_404(
                Farmer, id=self.kwargs['farmer_pk']
            )
        return super().get_serializer(*args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return MembershipCreateSerializer
        return MembershipSerializer

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        try:
            uuid.UUID(str(lookup))
            filter_kwargs = {'pk': lookup}
        except ValueError:
            filter_kwargs = {'member_number': lookup}
        return get_object_or_404(queryset, **filter_kwargs)

    def get_queryset(self):
        farmer_id = self.kwargs.get('farmer_pk')
        if farmer_id:
            return self.queryset.filter(farmer_id=farmer_id)
        return self.queryset.filter(
            cooperative_id=self.request.cooperative_id
        )

    def perform_create(self, serializer):
        farmer = serializer.context.get('farmer')
        membership = serializer.save(farmer=farmer)
        log_audit(
            actor=self.request.user,
            resource_type='farmer_membership',
            resource_id=membership.id,
            action='MEMBERSHIP_ADDED',
            new_value={
                'farmer_id': str(farmer.id),
                'farmer_name': f'{farmer.first_name} {farmer.last_name}',
                'cooperative_id': str(membership.cooperative_id),
                'member_number': membership.member_number,
            },
            cooperative_id=self.request.cooperative_id,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='farmer_membership',
            resource_id=instance.id,
            action='MEMBERSHIP_UPDATED',
            new_value=serializer.validated_data,
            cooperative_id=self.request.cooperative_id,
        )

    @action(detail=True, methods=['patch'])
    def deactivate(self, request, farmer_pk=None, pk=None):
        membership = self.get_object()
        membership.is_active = False
        membership.save(update_fields=['is_active'])
        log_audit(
            actor=request.user,
            resource_type='farmer_membership',
            resource_id=membership.id,
            action='MEMBERSHIP_DEACTIVATED',
            new_value={'is_active': False},
            cooperative_id=request.cooperative_id,
        )
        return Response(MembershipSerializer(membership).data)

    @action(detail=True, methods=['patch'])
    def reactivate(self, request, farmer_pk=None, pk=None):
        membership = self.get_object()
        membership.is_active = True
        membership.save(update_fields=['is_active'])
        log_audit(
            actor=request.user,
            resource_type='farmer_membership',
            resource_id=membership.id,
            action='MEMBERSHIP_REACTIVATED',
            new_value={'is_active': True},
            cooperative_id=request.cooperative_id,
        )
        return Response(MembershipSerializer(membership).data)
