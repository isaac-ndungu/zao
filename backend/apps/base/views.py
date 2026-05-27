from rest_framework.viewsets import ModelViewSet


class CooperativeScopedViewSet(ModelViewSet):
    def get_queryset(self):
        return self.queryset.filter(
            cooperative_id=self.request.user.cooperative_id
        )
