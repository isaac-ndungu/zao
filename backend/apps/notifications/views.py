from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.base.permissions import IsStaff

from .models import Notification
from .serializers import NotificationListSerializer, NotificationDetailSerializer
from .ussd import handle_ussd


@csrf_exempt
@require_POST
def ussd_callback(request):
    session_id = request.POST.get('sessionId', '')
    service_code = request.POST.get('serviceCode', '')
    phone_number = request.POST.get('phoneNumber', '')
    text = request.POST.get('text', '')

    expected = getattr(settings, 'AFRICASTALKING_USSD_CODE', '*384*12345#')
    if service_code != expected:
        return HttpResponse('END Invalid service code.', content_type='text/plain')

    prefix, message = handle_ussd(session_id, phone_number, text)
    return HttpResponse(f'{prefix} {message}', content_type='text/plain')


class NotificationLogViewSet(ReadOnlyModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationListSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        'content', 'channel', 'notification_type', 'status',
        'error_message', 'recipient__first_name', 'recipient__last_name',
        'recipient__phone_number',
    ]
    ordering_fields = ['created_at', 'sent_at', 'status', 'channel']
    ordering = ['-created_at']

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated:
            request.cooperative_id = request.user.cooperative_id

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return NotificationDetailSerializer
        return NotificationListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset.select_related('recipient', 'cooperative')
        if user.is_authenticated and getattr(user, 'role', None) == 'admin':
            return qs
        return qs.filter(
            cooperative_id=self.request.cooperative_id,
        )
