import logging
import re

from django.utils import timezone

from apps.base.utils import normalize_phone_for_sms
from apps.farmers.models import FarmerCooperativeMembership

from .models import Notification, USSDMenuConfig, USSDSession
from .utils import format_delivery_for_ussd

logger = logging.getLogger(__name__)

REQUIRES_MEMBERSHIP = frozenset({'MENU', 'DELIVERIES', 'PAYMENTS'})


def _log_ussd_notification(session, content):
    if not session.farmer:
        return
    coop_id = None
    if session.membership:
        coop_id = session.membership.cooperative_id
    elif session.farmer.cooperative_id:
        coop_id = session.farmer.cooperative_id
    Notification.objects.create(
        cooperative_id=coop_id,
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


def _get_menu_config(session, menu_key, language='en'):
    menus = USSDMenuConfig.objects.filter(
        cooperative_id=session.membership.cooperative_id,
        menu_key=menu_key,
        language=language,
        is_active=True,
    )
    if not menus.exists() and language != 'en':
        logger.info(
            'USSD language fallback: coop=%s menu=%s requested=%s -> en',
            session.membership.cooperative_id, menu_key, language,
        )
        menus = USSDMenuConfig.objects.filter(
            cooperative_id=session.membership.cooperative_id,
            menu_key=menu_key,
            language='en',
            is_active=True,
        )
    return menus.order_by('order')


def _render_menu(menus):
    lines = []
    for menu in menus:
        lines.append(menu.title)
        for opt in menu.options:
            lines.append(f'{opt["key"]}. {opt["label"]}')
    return '\n'.join(lines)


def _render_options(menus):
    lines = []
    for menu in menus:
        for opt in menu.options:
            lines.append(f'{opt["key"]}. {opt["label"]}')
    return '\n'.join(lines)


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

    if current_input and (len(current_input) > 20 or not re.match(r'^[a-zA-Z0-9\-]+$', current_input)):
        return _end(session, 'Invalid input. Please try again.')

    state = session.current_menu

    # Guard: states that require a selected membership
    if state in REQUIRES_MEMBERSHIP and not session.membership_id:
        return _end(session, 'Session expired. Please dial again.')

    # ── HOME ──
    if state == 'HOME' and not current_input:
        menus = _get_menu_config(session, 'home', 'en')
        if menus.exists():
            msg = menus.first().title
        else:
            msg = 'Welcome to Zao Cooperative.\nEnter your member number:'
        return _con(session, msg, 'MEMBER_NUMBER')

    if state == 'HOME' and current_input:
        state = 'MEMBER_NUMBER'

    # ── MEMBER_NUMBER ──
    if state == 'MEMBER_NUMBER':
        if not current_input:
            return _con(session, 'Enter your member number:', 'MEMBER_NUMBER')

        membership = FarmerCooperativeMembership.objects.filter(
            member_number=current_input,
            farmer__phone_number=phone,
            is_active=True,
        ).select_related('farmer', 'cooperative').first()

        if not membership:
            logger.warning(
                'USSD invalid member number: %s phone: %s (session %s)',
                current_input, phone, session_id,
            )
            return _end(session, 'Invalid member number. Please try again.')

        session.farmer = membership.farmer

        # Count active memberships to decide if co-op picker is needed
        active_memberships = list(
            FarmerCooperativeMembership.objects.filter(
                farmer=membership.farmer,
                is_active=True,
            ).select_related('cooperative')
        )

        if len(active_memberships) == 1:
            session.membership = membership
            session.save(update_fields=['farmer', 'membership'])
            menus = _get_menu_config(session, 'menu', 'en')
            if menus.exists():
                msg = _render_options(menus)
            else:
                msg = '1. My Deliveries\n2. My Payments\n3. My Profile'
            return _con(session, msg, 'MENU')

        # Multiple active memberships → show picker
        session.save(update_fields=['farmer'])
        lines = [
            f'{i}. {m.cooperative.name}'
            for i, m in enumerate(active_memberships, start=1)
        ]
        return _con(
            session,
            'Select cooperative:\n' + '\n'.join(lines),
            'COOP_PICKER',
        )

    # ── COOP_PICKER ──
    if state == 'COOP_PICKER':
        if not current_input or not session.farmer_id:
            return _end(session, 'Session expired. Please dial again.')

        active_memberships = list(
            FarmerCooperativeMembership.objects.filter(
                farmer=session.farmer,
                is_active=True,
            ).select_related('cooperative')
        )

        try:
            idx = int(current_input) - 1
            membership = active_memberships[idx]
        except (ValueError, IndexError):
            return _end(session, 'Invalid selection. Please dial again.')

        session.membership = membership
        session.save(update_fields=['membership'])
        menus = _get_menu_config(session, 'menu', 'en')
        if menus.exists():
            msg = _render_options(menus)
        else:
            msg = '1. My Deliveries\n2. My Payments\n3. My Profile'
        return _con(session, msg, 'MENU')

    # ── MENU ──
    if state == 'MENU':
        if current_input == '1':
            from apps.deliveries.models import Delivery
            coop = session.membership.cooperative
            limit = coop.ussd_delivery_limit or 3
            deliveries = Delivery.objects.filter(
                farmer=session.farmer,
                cooperative_id=coop.pk,
            ).order_by('-date_delivered')[:limit]
            if not deliveries:
                return _end(session, 'No deliveries found.')
            lines = [format_delivery_for_ussd(d) for d in deliveries]
            menus = _get_menu_config(session, 'deliveries', 'en')
            if menus.exists():
                back_option = menus.first().title + '\n' + '\n'.join(lines)
            else:
                back_option = 'Recent deliveries:\n' + '\n'.join(lines)
            return _con(session, back_option + '\n0. Back', 'DELIVERIES')

        if current_input == '2':
            from apps.payment_engine.models import FarmerPayment
            payment = FarmerPayment.objects.filter(
                farmer=session.farmer,
                cooperative_id=session.membership.cooperative_id,
            ).order_by('-created_at').first()
            if not payment:
                return _end(session, 'No payments found.')
            return _end(
                session,
                f'Last payment: KES {float(payment.net_amount):,.2f} on {payment.cycle.name}',
            )

        if current_input == '3':
            m = session.membership
            f = session.farmer
            return _end(
                session,
                f'Name: {f.first_name} {f.last_name}\n'
                f'Member: {m.member_number}\n'
                f'Co-op: {m.cooperative.name}\n'
                f'Payment: {m.get_payment_method_display()}',
            )

        if current_input == '0':
            session.membership = None
            session.farmer = None
            session.save(update_fields=['membership', 'farmer'])
            return _con(
                session, 'Welcome to Zao Cooperative.\nEnter your member number:', 'HOME',
            )

        return _end(session, 'Sorry, we could not process your request. Please dial again.')

    # ── DELIVERIES (back) ──
    if state == 'DELIVERIES':
        if current_input == '0':
            menus = _get_menu_config(session, 'menu', 'en')
            if menus.exists():
                msg = _render_options(menus)
            else:
                msg = '1. My Deliveries\n2. My Payments\n3. My Profile'
            return _con(session, msg, 'MENU')

        return _end(session, 'Sorry, we could not process your request. Please dial again.')

    logger.warning(
        'USSD unhandled state: %s input: %s (session %s)',
        state, current_input, session_id,
    )
    return _end(session, 'Sorry, we could not process your request. Please dial again.')
