from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.base.idempotency import idempotent
from apps.base.utils import log_audit
from apps.auth_api.models import User
from apps.base.permissions import IsAdmin, IsAdminOrManager
from apps.base.views import CooperativeScopedViewSet

from .serializers import (
    AvatarUploadSerializer,
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

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', None) == 'admin':
            qs = self.queryset
        else:
            qs = self.queryset.filter(cooperative_id=self.request.cooperative_id)

        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None and is_active != '':
            qs = qs.filter(is_active=is_active.lower() == 'true')

        return qs

    @idempotent()
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAdminOrManager()]
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

    @action(detail=False, methods=['patch'])
    def avatar(self, request):
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        old_avatar = user.avatar
        user.avatar = serializer.validated_data['avatar']
        user.save()

        if old_avatar:
            try:
                import cloudinary
                public_id = old_avatar.name
                cloudinary.uploader.destroy(public_id)
            except Exception:
                pass

        return Response(UserListSerializer(user).data)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        if user.avatar:
            try:
                import cloudinary
                public_id = user.avatar.name
                cloudinary.uploader.destroy(public_id)
            except Exception:
                pass
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
