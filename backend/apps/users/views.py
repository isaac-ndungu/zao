from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auth_api.models import User
from apps.base.permissions import IsAdmin, IsAdminOrManager
from apps.base.views import CooperativeScopedViewSet
from apps.base.utils import log_audit

from .serializers import (
    UserCreateSerializer,
    UserListSerializer,
    UserSelfUpdateSerializer,
    UserUpdateSerializer,
)


class UserViewSet(CooperativeScopedViewSet):
    queryset = User.objects.all().select_related('cooperative')
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'phone_number', 'role']
    ordering_fields = ['first_name', 'last_name', 'email', 'role', 'date_joined']
    ordering = ['first_name']

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAdmin()]
        if self.action in ('create', 'list'):
            return [IsAuthenticated(), IsAdminOrManager()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserListSerializer

    def perform_create(self, serializer):
        instance = serializer.save(
            cooperative_id=self.request.cooperative_id
        )
        log_audit(
            actor=self.request.user,
            resource_type='user',
            resource_id=instance.id,
            action='CREATE',
            new_value={'email': instance.email, 'role': instance.role},
            cooperative_id=self.request.cooperative_id,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='user',
            resource_id=instance.id,
            action='UPDATE',
            previous_value={'email': instance.email, 'role': instance.role},
            new_value=serializer.validated_data,
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type='user',
            resource_id=instance.id,
            action='DELETE',
            previous_value={'email': instance.email, 'role': instance.role},
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        if request.method == 'PATCH':
            serializer = UserSelfUpdateSerializer(
                request.user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(UserListSerializer(request.user).data)

        return Response(UserListSerializer(request.user).data)
