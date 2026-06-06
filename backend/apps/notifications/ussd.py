import logging
import re

from django.utils import timezone

from apps.base.utils import normalize_phone_for_sms
from apps.farmers.models import Farmer

from .models import Notification, USSDSession
from .utils import format_delivery_for_ussd

logger = logging.getLogger(__name__)


def _log_ussd_notification(session, content):
    if session.farmer:
        Notification.objects.create(
            cooperative=session.farmer.cooperative,
            recipient=session.farmer,
            channel='USSD',
            notification_type='USSD_SESSION',
            content=content,
            status='SENT',
        )


def _end(session, message):
    session.save(update_fields=['last_activity', 'phone_number'])
    _log_ussd_notification(session, message)
    return ('END', message)


def _con(session, message, next_menu):
    session.current_menu = next_menu
    session.save(update_fields=['current_menu', 'last_activity', 'phone_number'])
    return ('CON', message)


def handle_ussd(session_id: str, phone_number: str, text: str):
    phone = normalize_phone_for_sms(phone_number)

    session, _ = USSDSession.objects.get_or_create(
        session_id=session_id,
        defaults={'phone_number': phone},
    )
    session.phone_number = phone
    session.last_activity = timezone.now()

    text = text.strip()
    parts = text.split('*') if text else ['']
    current_input = parts[-1]
    prior = parts[:-1] if text else []

    # Input sanitisation
    if current_input and (len(current_input) > 20 or not re.match(r'^[a-zA-Z0-9\-]+$', current_input)):
        return _end(session, 'Invalid input. Please try again.')

    state = session.current_menu

    #   HOME / empty input                        ─
    if state == 'HOME' and not current_input:
        return _con(session, 'Welcome to Zao Cooperative.\nEnter your member number:', 'MEMBER_NUMBER')

    if state == 'HOME' and current_input:
        state = 'MEMBER_NUMBER'

    #   MEMBER_NUMBER                           
    if state == 'MEMBER_NUMBER':
        if not current_input:
            return _con(session, 'Enter your member number:', 'MEMBER_NUMBER')

        farmer = Farmer.objects.filter(member_number=current_input).first()
        if not farmer:
            logger.warning('USSD invalid member number: %s (session %s)', current_input, session_id)
            return _end(session, 'Invalid member number. Please try again.')

        session.farmer = farmer
        session.save(update_fields=['farmer'])
        return _con(
            session,
            '1. My Deliveries\n2. My Payments\n3. My Profile',
            'MENU',
        )

    #   MENU                               ─
    if state == 'MENU':
        if current_input == '1':
            from apps.deliveries.models import Delivery
            deliveries = Delivery.objects.filter(
                farmer=session.farmer,
            ).order_by('-date_delivered')[:3]
            if not deliveries:
                return _end(session, 'No deliveries found.')
            lines = [format_delivery_for_ussd(d) for d in deliveries]
            return _con(
                session,
                'Recent deliveries:\n' + '\n'.join(lines) + '\n0. Back',
                'DELIVERIES',
            )

        if current_input == '2':
            from apps.payment_engine.models import FarmerPayment
            payment = FarmerPayment.objects.filter(
                farmer=session.farmer,
            ).order_by('-created_at').first()
            if not payment:
                return _end(session, 'No payments found.')
            return _end(
                session,
                f'Last payment: KES {float(payment.net_amount):,.2f} on {payment.cycle.name}',
            )

        if current_input == '3':
            f = session.farmer
            return _end(
                session,
                f'Name: {f.first_name} {f.last_name}\n'
                f'Member: {f.primary_membership.member_number if f.primary_membership else "---"}\n'
                f'Payment: {f.primary_membership.get_payment_method_display() if f.primary_membership else "---"}',
            )

        if current_input == '0':
            return _con(
                session, 'Welcome to Zao Cooperative.\nEnter your member number:', 'HOME',
            )

        return _end(session, 'Sorry, we could not process your request. Please dial again.')

    #   DELIVERIES (back)                         
    if state == 'DELIVERIES':
        if current_input == '0':
            return _con(
                session,
                '1. My Deliveries\n2. My Payments\n3. My Profile',
                'MENU',
            )

        return _end(session, 'Sorry, we could not process your request. Please dial again.')

    #   Catch-all                             
    logger.warning('USSD unhandled state: %s input: %s (session %s)', state, current_input, session_id)
    return _end(session, 'Sorry, we could not process your request. Please dial again.')
