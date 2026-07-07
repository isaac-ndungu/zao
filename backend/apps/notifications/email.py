import logging
import socket
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_email(
    subject: str,
    heading: str,
    content_html: str,
    to_email: list[str],
    from_email: Optional[str] = None,
    otp_code: Optional[str] = None,
    otp_expiry: Optional[str] = None,
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
) -> dict:
    if not to_email:
        return {'success': False, 'error': 'No recipients'}

    if settings.NOTIFICATIONS_DRY_RUN:
        logger.info(
            'DRY RUN email to %s | subject: %s | otp: %s',
            to_email, subject, otp_code,
        )
        return {'success': True, 'external_id': 'dry-run', 'error': None}

    from_email = from_email or settings.DEFAULT_FROM_EMAIL

    context = {
        'subject': subject,
        'heading': heading,
        'content': content_html,
        'otp_code': otp_code,
        'otp_expiry': otp_expiry,
        'action_url': action_url,
        'action_label': action_label,
        'year': datetime.now().year,
    }

    try:
        html_body = render_to_string('notifications/email/base.html', context)
        text_body = strip_tags(content_html)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=to_email,
        )
        email.attach_alternative(html_body, 'text/html')

        socket.setdefaulttimeout(10)
        email.send(fail_silently=False)
        logger.info('Email sent to %s: %s', to_email, subject)
        return {'success': True, 'external_id': None, 'error': None}

    except Exception as e:
        logger.error('Failed to send email to %s: %s', to_email, e)
        return {'success': False, 'external_id': None, 'error': str(e)}


def send_login_otp(user, otp_code: str) -> dict:
    return send_email(
        subject='Your Zao Login Code',
        heading='Your verification code',
        content_html=f'''
            <p style="margin: 0 0 12px; font-size: 15px; color: #424242; line-height: 1.6;">
              Enter the code below to complete your sign-in:
            </p>
        ''',
        to_email=[user.email],
        otp_code=otp_code,
        otp_expiry='5 minutes',
    )


def send_password_reset_otp(user, otp_code: str) -> dict:
    return send_email(
        subject='Reset Your Zao Password',
        heading='Reset your password',
        content_html=f'''
            <p style="margin: 0 0 12px; font-size: 15px; color: #424242; line-height: 1.6;">
              We received a request to reset your password. Use the code below to proceed.
              If you did not request this, please ignore this email.
            </p>
        ''',
        to_email=[user.email],
        otp_code=otp_code,
        otp_expiry='10 minutes',
    )


def send_invite_otp(user, otp_code: str, role: str, invite_link: str) -> dict:
    role_display = role.replace('_', ' ').title()
    return send_email(
        subject="You've been invited to Zao",
        heading=f'Join Zao as {role_display}',
        content_html=f'''
            <p style="margin: 0 0 12px; font-size: 15px; color: #424242; line-height: 1.6;">
              You've been invited to join Zao as a <strong>{role_display}</strong>.
              Use the code below to accept your invitation.
            </p>
            <p style="margin: 0; font-size: 13px; color: #757575; line-height: 1.6;">
              This invitation expires in 7 days.
            </p>
        ''',
        to_email=[user.email],
        otp_code=otp_code,
        otp_expiry='10 minutes',
        action_url=invite_link,
        action_label='Accept Invitation',
    )


def send_account_credentials(user, password: str) -> dict:
    return send_email(
        subject='Your Zao Account Has Been Created',
        heading='Welcome to Zao',
        content_html=f'''
            <p style="margin: 0 0 12px; font-size: 15px; color: #424242; line-height: 1.6;">
              Your Zao account has been created. Here are your sign-in details:
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 16px 0; background-color: #f5f5f5; border-radius: 8px; overflow: hidden;">
              <tr>
                <td style="padding: 12px 16px; border-bottom: 1px solid #eeeeee;">
                  <span style="font-size: 12px; color: #9e9e9e; text-transform: uppercase; letter-spacing: 0.5px;">Email</span>
                </td>
                <td style="padding: 12px 16px; border-bottom: 1px solid #eeeeee;">
                  <span style="font-size: 14px; color: #212121; font-weight: 500;">{user.email}</span>
                </td>
              </tr>
              <tr>
                <td style="padding: 12px 16px;">
                  <span style="font-size: 12px; color: #9e9e9e; text-transform: uppercase; letter-spacing: 0.5px;">Temporary Password</span>
                </td>
                <td style="padding: 12px 16px;">
                  <span style="font-size: 14px; color: #212121; font-weight: 500; font-family: 'Courier New', monospace;">{password}</span>
                </td>
              </tr>
            </table>
            <p style="margin: 0; font-size: 13px; color: #757575; line-height: 1.6;">
              Please log in and change your password immediately after first sign-in.
            </p>
        ''',
        to_email=[user.email],
    )


def send_account_deactivated(user) -> dict:
    return send_email(
        subject='Your Zao Account Has Been Deactivated',
        heading='Account deactivated',
        content_html=f'''
            <p style="margin: 0 0 12px; font-size: 15px; color: #424242; line-height: 1.6;">
              Your Zao account (<strong>{user.email}</strong>) has been deactivated by an administrator.
            </p>
            <p style="margin: 0; font-size: 13px; color: #757575; line-height: 1.6;">
              If you believe this was done in error, please contact your administrator or reach out to our support team.
            </p>
        ''',
        to_email=[user.email],
    )


def send_password_reset_by_admin(user, new_password: str) -> dict:
    return send_email(
        subject='Your Zao Password Has Been Reset',
        heading='Password reset by administrator',
        content_html=f'''
            <p style="margin: 0 0 12px; font-size: 15px; color: #424242; line-height: 1.6;">
              An administrator has reset your Zao password. Your new sign-in details are:
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 16px 0; background-color: #f5f5f5; border-radius: 8px; overflow: hidden;">
              <tr>
                <td style="padding: 12px 16px; border-bottom: 1px solid #eeeeee;">
                  <span style="font-size: 12px; color: #9e9e9e; text-transform: uppercase; letter-spacing: 0.5px;">Email</span>
                </td>
                <td style="padding: 12px 16px; border-bottom: 1px solid #eeeeee;">
                  <span style="font-size: 14px; color: #212121; font-weight: 500;">{user.email}</span>
                </td>
              </tr>
              <tr>
                <td style="padding: 12px 16px;">
                  <span style="font-size: 12px; color: #9e9e9e; text-transform: uppercase; letter-spacing: 0.5px;">New Password</span>
                </td>
                <td style="padding: 12px 16px;">
                  <span style="font-size: 14px; color: #212121; font-weight: 500; font-family: 'Courier New', monospace;">{new_password}</span>
                </td>
              </tr>
            </table>
            <p style="margin: 0; font-size: 13px; color: #757575; line-height: 1.6;">
              Please log in and change your password as soon as possible.
            </p>
        ''',
        to_email=[user.email],
    )


def send_stuck_payments_alert(recipient_emails: list[str], txns: list, frontend_url: str) -> dict:
    from ..disbursement.models import Disbursement

    rows = ''
    for txn in txns:
        status_color = '#e53935' if txn.status == 'FAILED' else '#ff9800'
        rows += f'''
            <tr>
              <td style="padding: 10px 16px; border-bottom: 1px solid #eeeeee; font-size: 13px; color: #424242;">{txn.id}</td>
              <td style="padding: 10px 16px; border-bottom: 1px solid #eeeeee; font-size: 13px; color: #424242;">{txn.recipient_name or 'Unknown'}</td>
              <td style="padding: 10px 16px; border-bottom: 1px solid #eeeeee; font-size: 13px; color: #424242; font-weight: 600;">KES {txn.amount:,.2f}</td>
              <td style="padding: 10px 16px; border-bottom: 1px solid #eeeeee;">
                <span style="display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase; background-color: {status_color}20; color: {status_color};">{txn.status}</span>
              </td>
            </tr>
        '''

    content_html = f'''
        <p style="margin: 0 0 16px; font-size: 15px; color: #424242; line-height: 1.6;">
          The following <strong>{len(txns)} disbursement transaction(s)</strong> were found stuck in the reconciliation check and have been processed. Please review the disbursement dashboard for full details.
        </p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; border-radius: 8px; overflow: hidden; margin-bottom: 16px;">
          <thead>
            <tr style="background-color: #1a5c2e; color: #ffffff;">
              <th style="padding: 10px 16px; text-align: left; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">ID</th>
              <th style="padding: 10px 16px; text-align: left; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Recipient</th>
              <th style="padding: 10px 16px; text-align: left; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Amount</th>
              <th style="padding: 10px 16px; text-align: left; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Status</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
    '''

    return send_email(
        subject=f'[ACTION REQUIRED] {len(txns)} Stuck Payment(s) Need Attention',
        heading='Disbursement Alert',
        content_html=content_html,
        to_email=recipient_emails,
        action_url=f'{frontend_url}/disbursements' if frontend_url else None,
        action_label='View Disbursements',
    )


def send_export_failed(task, error: str, frontend_url: str) -> dict:
    return send_email(
        subject='Zao Analytics Export Failed',
        heading='Export job failed',
        content_html=f'''
            <p style="margin: 0 0 12px; font-size: 15px; color: #424242; line-height: 1.6;">
              Your requested <strong>{task.export_type.replace('_', ' ').title()}</strong> analytics export has failed.
            </p>
            <div style="background-color: #ffebee; border-left: 4px solid #e53935; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 16px 0;">
              <p style="margin: 0; font-size: 13px; color: #c62828; font-weight: 500;">Error: {error}</p>
            </div>
            <p style="margin: 0; font-size: 13px; color: #757575; line-height: 1.6;">
              Please try again. If the problem persists, contact support.
            </p>
        ''',
        to_email=[task.requested_by.email],
        action_url=f'{frontend_url}/analytics' if frontend_url else None,
        action_label='Try Again',
    )
