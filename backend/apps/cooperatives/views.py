from django.db.models import Count
from django.forms.models import model_to_dict
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from rest_framework.exceptions import PermissionDenied

from apps.base.constants import UserRole
from apps.base.permissions import IsAdmin, IsAdminOrManager
from apps.base.idempotency import idempotent
from apps.base.utils import log_audit
from apps.cooperatives.models import Cooperative, PaymentModel, ProduceType
from apps.cooperatives.serializers import (
    CooperativeListSerializer,
    CooperativeDetailSerializer,
)


class CooperativeViewSet(viewsets.ModelViewSet):
    queryset = Cooperative.objects.all()
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'registration_number', 'county', 'kra_pin']
    ordering_fields = ['name', 'created_at', 'member_count', 'county']
    ordering = ['name']

    @idempotent()
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAdmin()]
        if self.action == 'create':
            return [IsAdminOrManager()]
        return []

    def get_serializer_class(self):
        if self.action == 'list':
            return CooperativeListSerializer
        return CooperativeDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset().select_related('parent_union')
        user = self.request.user

        if user.is_authenticated and getattr(user, 'role', None) != UserRole.ADMIN:
            qs = qs.filter(id=user.cooperative_id)

        for param in ('county', 'produce_type', 'payment_model', 'sub_county'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})

        for param in ('is_active', 'is_verified'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val.lower() == 'true'})

        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, 'role', None) == UserRole.MANAGER:
            if user.cooperative_id:
                raise PermissionDenied('You already belong to a cooperative.')
        instance = serializer.save()
        if getattr(user, 'role', None) == UserRole.MANAGER:
            user.cooperative_id = instance.id
            user.save(update_fields=['cooperative_id'])
        log_audit(
            actor=self.request.user,
            resource_type='cooperative',
            resource_id=instance.id,
            action='CREATE',
            new_value=serializer.data,
            cooperative_id=instance.id,
        )

    def perform_update(self, serializer):
        previous = model_to_dict(serializer.instance, fields=[f.name for f in Cooperative._meta.get_fields()])
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='cooperative',
            resource_id=instance.id,
            action='UPDATE',
            previous_value=previous,
            new_value=serializer.data,
            cooperative_id=instance.id,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type='cooperative',
            resource_id=instance.id,
            action='DELETE',
            previous_value={'name': instance.name, 'registration_number': instance.registration_number},
            cooperative_id=instance.id,
        )
        instance.delete()

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'active': qs.filter(is_active=True).count(),
            'by_produce_type': qs.values('produce_type').annotate(count=Count('id')),
            'by_county': qs.values('county').annotate(count=Count('id')),
            'by_verified': qs.values('is_verified').annotate(count=Count('id')),
        })

    @action(detail=False, methods=['get'])
    def me(self, request):
        user = request.user
        if getattr(user, 'cooperative_id', None):
            coop = self.get_queryset().filter(id=user.cooperative_id).first()
            if coop:
                return Response(CooperativeDetailSerializer(coop).data)
        return Response({'detail': 'No cooperative assigned.'}, status=404)

    @action(detail=False, methods=['get'])
    def enums(self, request):
        return Response({
            'produce_types': ProduceType.choices,
            'payment_models': PaymentModel.choices,
        })
