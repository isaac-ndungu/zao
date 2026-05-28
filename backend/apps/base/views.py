from rest_framework.viewsets import ModelViewSet


class CooperativeScopedViewSet(ModelViewSet):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated:
            request.cooperative_id = request.user.cooperative_id

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', None) == 'admin':
            return self.queryset
        return self.queryset.filter(
            cooperative_id=self.request.cooperative_id
        )

    def perform_create(self, serializer):
        serializer.save(
            cooperative_id=self.request.cooperative_id
        )
