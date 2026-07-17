import ipaddress
import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet
from rest_framework.mixins import CreateModelMixin

from .models import ContactMessage, Notification
from .serializers import ContactMessageSerializer, ContactMessageAdminSerializer, NotificationListSerializer, NotificationDetailSerializer
from .email import send_contact_message_to_admin
from .ussd import handle_ussd

logger = logging.getLogger(__name__)


def _validate_ussd_ip(request) -> bool:
    whitelist = getattr(settings, 'AFRICASTALKING_CALLBACK_IP_WHITELIST', '')
    if not whitelist:
        return True
    remote_ip = request.META.get('REMOTE_ADDR', '')
    try:
        addr = ipaddress.ip_address(remote_ip)
    except ValueError:
        logger.warning('Invalid USSD callback remote address: %s', remote_ip)
        return False
    for cidr in whitelist.split(','):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            logger.warning('Invalid CIDR in USSD whitelist: %s', cidr)
    logger.warning('USSD callback from %s rejected — not in whitelist', remote_ip)
    return False


@csrf_exempt
@require_POST
def ussd_callback(request):
    if not _validate_ussd_ip(request):
        return HttpResponse('END Forbidden.', content_type='text/plain')

    session_id = request.POST.get('sessionId', '')
    service_code = request.POST.get('serviceCode', '')
    phone_number = request.POST.get('phoneNumber', '')
    text = request.POST.get('text', '')

    expected = getattr(settings, 'AFRICASTALKING_USSD_CODE', '*384*12345#')
    logger.warning('USSD callback: service_code=%s expected=%s', service_code, expected)
    if service_code != expected:
        return HttpResponse('END Invalid service code.', content_type='text/plain')

    prefix, message = handle_ussd(session_id, phone_number, text)
    return HttpResponse(f'{prefix} {message}', content_type='text/plain')


@extend_schema(
    summary="Notification log",
    description="Read-only view of all notifications (SMS, USSD, in-app). Farmers see only their own; managers see cooperative-wide; admins see all.",
    tags=["Notifications"],
)
class NotificationLogViewSet(ReadOnlyModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationListSerializer
    permission_classes = [IsAuthenticated]
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
        if user.is_superuser:
            return qs
        farmer = getattr(user, 'farmer_profile', None)
        if farmer:
            return qs.filter(recipient=farmer)
        return qs.filter(cooperative_id=self.request.cooperative_id)


@extend_schema(
    summary="Submit a contact message",
    description="Public endpoint for the website contact form. Sends an email to the admin and stores the message.",
    tags=["Contact"],
)
class ContactMessageViewSet(CreateModelMixin, GenericViewSet):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        send_contact_message_to_admin(contact)
        return Response(
            {'detail': 'Your message has been sent successfully.'},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary="Contact messages (admin)",
    description="Read-only view of all contact form submissions for admins.",
    tags=["Contact"],
)
class ContactMessageAdminViewSet(ReadOnlyModelViewSet):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageAdminSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'email', 'subject', 'message']
    ordering_fields = ['created_at', 'is_read']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        return self.queryset.none()
