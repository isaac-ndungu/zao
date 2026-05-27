from rest_framework.viewsets import ModelViewSet


class CooperativeScopedViewSet(ModelViewSet):
    def get_queryset(self):
        return self.queryset.filter(
            cooperative_id=self.request.cooperative_id
        )

    def perform_create(self, serializer):
        serializer.save(
            cooperative_id=self.request.cooperative_id
        )
