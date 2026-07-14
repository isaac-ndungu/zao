from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.auth_api.models import User
from apps.base.constants import UserRole
from apps.base.models import AuditLog
from apps.cooperatives.models import Cooperative
from apps.deductions.models import Deduction
from apps.deliveries.models import Delivery
from apps.disbursement.models import DisbursementBatch
from apps.farmers.models import Farmer
from apps.grading.models import Grade
from apps.inventory.models import Inventory
from apps.loans.models import Loan
from apps.payment_engine.models import FarmerPayment, PaymentCycle
from apps.sales.models import Buyer, Sale

MAX_QUERY_LENGTH = 100
MIN_QUERY_LENGTH = 2
MAX_PER_RESOURCE = 5


class GlobalSearchThrottle(UserRateThrottle):
    scope = 'global_search'


def _filter_icontains(qs, query, fields):
    filters = Q()
    for field in fields:
        filters |= Q(**{f'{field}__icontains': query})
    return qs.filter(filters)


def _role_base_qs(model, user):
    if user.role == UserRole.ADMIN:
        return model._base_manager.all()
    coop_id = getattr(user, 'cooperative_id', None)
    coop_field = 'cooperative_id'
    if getattr(model, 'cooperative', None) is None and hasattr(model, coop_field):
        pass
    if hasattr(model, 'cooperative_id'):
        return model._base_manager.filter(cooperative_id=coop_id)
    return model._base_manager.all()


def _search_resource(model, user, query, search_fields, label_fn, subtitle_fn, type_label, icon, url_pattern, coop_filter=True):
    if coop_filter and user.role != UserRole.ADMIN:
        coop_id = getattr(user, 'cooperative_id', None)
        qs = model._base_manager.filter(cooperative_id=coop_id)
    else:
        qs = model._base_manager.all()

    if hasattr(model, 'deleted_at'):
        qs = qs.filter(deleted_at__isnull=True)

    if hasattr(model, 'is_active'):
        qs = qs.filter(is_active=True)

    qs = _filter_icontains(qs, query, search_fields)
    qs = qs[:MAX_PER_RESOURCE]

    items = []
    for obj in qs:
        items.append({
            'id': str(getattr(obj, 'id', '')),
            'type': type_label,
            'label': label_fn(obj),
            'subtitle': subtitle_fn(obj),
            'url': url_pattern.format(id=getattr(obj, 'id', '')),
        })

    return {
        'key': type_label,
        'label': type_label.replace('_', ' ').title(),
        'icon': icon,
        'total': len(items),
        'items': items,
    }


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [GlobalSearchThrottle]

    def _get_member_number(self, farmer, coop_id=None):
        filters = Q(is_active=True)
        if coop_id:
            filters &= Q(cooperative_id=coop_id)
        membership = farmer.memberships.filter(filters).first()
        return membership.member_number if membership else None

    def get(self, request):
        query = request.query_params.get('q', '').strip()

        if len(query) > MAX_QUERY_LENGTH:
            return Response(
                {'error': f'Query too long. Maximum {MAX_QUERY_LENGTH} characters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(query) < MIN_QUERY_LENGTH:
            return Response({'query': query, 'results': []})

        user = request.user
        role = user.role
        results = []
        coop_id = getattr(request, 'cooperative_id', None) or user.cooperative_id

        if role == UserRole.ADMIN:
            results = self._search_admin(query, coop_id)
        elif role == UserRole.MANAGER:
            results = self._search_manager(query, coop_id)
        elif role == UserRole.ACCOUNTANT:
            results = self._search_accountant(query, coop_id)
        elif role == UserRole.GRADER:
            results = self._search_grader(query, coop_id)
        elif role == UserRole.AUDITOR:
            results = self._search_auditor(query, coop_id)
        elif role == UserRole.EXTERNAL_AUDITOR:
            results = self._search_external_auditor(query, coop_id)

        return Response({'query': query, 'results': results})

    def _admin_base(self, query, coop_id=None):
        def _search(model, fields, label_fn, subtitle_fn, type_label, icon, url_pattern, check_active=True):
            qs = model._base_manager.all()
            if hasattr(model, 'deleted_at'):
                qs = qs.filter(deleted_at__isnull=True)
            if check_active and hasattr(model, 'is_active'):
                qs = qs.filter(is_active=True)
            qs = _filter_icontains(qs, query, fields)
            if model is Farmer:
                qs = qs.prefetch_related('memberships')
            return self._format_results(qs, label_fn, subtitle_fn, type_label, icon, url_pattern)

        results = []
        results.append(_search(Farmer, ['first_name', 'last_name', 'phone_number', 'email', 'memberships__member_number'],
            lambda f: f"{f.first_name} {f.last_name}", lambda f: f"{self._get_member_number(f) or 'N/A'} | {f.county or ''}",
            'farmers', 'person', '/admin/farmers/{id}'))
        results.append(_search(Cooperative, ['name', 'registration_number', 'county'],
            lambda c: c.name, lambda c: f"Reg: {c.registration_number} | {c.county}",
            'cooperatives', 'groups', '/admin/cooperatives/{id}'))
        results.append(_search(User, ['first_name', 'last_name', 'email', 'phone_number', 'role'],
            lambda u: f"{u.first_name} {u.last_name}", lambda u: f"{u.email} | {u.role or ''}",
            'users', 'group', '/admin/users/{id}', check_active=False))
        results.append(_search(Delivery, ['batch_id', 'farmer__first_name', 'farmer__last_name', 'local_id'],
            lambda d: d.batch_id, lambda d: f"{d.farmer.first_name} {d.farmer.last_name} | {d.product_type or ''}",
            'deliveries', 'inventory_2', '/admin/deliveries/{id}'))
        results.append(_search(Grade, ['delivery__batch_id', 'grade_letter', 'delivery__farmer__first_name', 'delivery__farmer__last_name'],
            lambda g: f"Grade {g.grade_letter}", lambda g: f"{g.delivery.batch_id} | {g.delivery.farmer.first_name} {g.delivery.farmer.last_name}",
            'grades', 'grading', '/admin/grades/{id}'))
        results.append(_search(Loan, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number', 'notes'],
            lambda l: f"KES {l.amount_principal:,.0f}", lambda l: f"{l.farmer.first_name} {l.farmer.last_name} | {l.status or ''}",
            'loans', 'account_balance', '/admin/loans/{id}'))
        results.append(_search(PaymentCycle, ['name'],
            lambda c: c.name, lambda c: c.status or '',
            'payment_cycles', 'payments', '/admin/cycles/{id}'))
        results.append(_search(FarmerPayment, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number'],
            lambda p: f"{p.farmer.first_name} {p.farmer.last_name}", lambda p: f"KES {p.net_amount:,.0f} | {p.payment_status or ''}",
            'payments', 'payments', '/admin/payments/{id}'))
        results.append(_search(DisbursementBatch, ['id', 'cooperative__name', 'notes'],
            lambda b: f"Batch {str(b.id)[:8]}", lambda b: f"KES {b.total_amount:,.0f} | {b.status or ''}",
            'disbursements', 'account_balance_wallet', '/admin/disbursements/{id}'))
        results.append(_search(Inventory, ['batch_id', 'grade', 'product_type'],
            lambda i: i.batch_id, lambda i: f"{i.product_type or ''} {i.grade or ''} | {i.unit or ''}",
            'inventory', 'inventory_2', '/admin/inventory/{id}'))
        results.append(_search(Buyer, ['name', 'contact_person', 'phone_number', 'email'],
            lambda b: b.name, lambda b: b.contact_person or b.phone_number or '',
            'buyers', 'store', '/admin/buyers/{id}'))
        results.append(_search(Sale, ['buyer__name', 'product_type', 'invoice_number'],
            lambda s: f"Invoice {s.invoice_number}" if s.invoice_number else f"KES {s.total_amount:,.0f}",
            lambda s: f"{s.buyer.name} | {s.product_type or ''}",
            'sales', 'receipt_long', '/admin/sales/{id}'))
        results.append(_search(Deduction, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number', 'deduction_type'],
            lambda d: d.deduction_type.replace('_', ' ').title(), lambda d: f"{d.farmer.first_name} {d.farmer.last_name} | KES {d.amount:,.0f}",
            'deductions', 'money_off', '/admin/deductions/{id}'))
        results.append(_search(AuditLog, ['actor__first_name', 'actor__last_name', 'resource_type', 'action', 'resource_id'],
            lambda a: f"{a.action} {a.resource_type}", lambda a: f"{a.actor.first_name} {a.actor.last_name}" if a.actor else 'System',
            'audit_log', 'history', '/admin/audit/{id}'))

        return [r for r in results if r['total'] > 0]

    def _search_admin(self, query, coop_id):
        return self._admin_base(query)

    def _search_manager(self, query, coop_id):
        def _search(model, fields, label_fn, subtitle_fn, type_label, icon, url_pattern, check_active=True):
            qs = model._base_manager.filter(cooperative_id=coop_id)
            if hasattr(model, 'deleted_at'):
                qs = qs.filter(deleted_at__isnull=True)
            if check_active and hasattr(model, 'is_active'):
                qs = qs.filter(is_active=True)
            qs = _filter_icontains(qs, query, fields)
            if model is Farmer:
                qs = qs.prefetch_related('memberships')
            return self._format_results(qs, label_fn, subtitle_fn, type_label, icon, url_pattern)

        results = []
        results.append(_search(Farmer, ['first_name', 'last_name', 'phone_number', 'memberships__member_number'],
            lambda f: f"{f.first_name} {f.last_name}", lambda f: f"{self._get_member_number(f, coop_id) or 'N/A'} | {f.county or ''}",
            'farmers', 'person', '/manager/farmers/{id}'))
        results.append(_search(Delivery, ['batch_id', 'farmer__first_name', 'farmer__last_name', 'local_id'],
            lambda d: d.batch_id, lambda d: f"{d.farmer.first_name} {d.farmer.last_name} | {d.product_type or ''}",
            'deliveries', 'inventory_2', '/manager/deliveries/{id}'))
        results.append(_search(Grade, ['delivery__batch_id', 'grade_letter', 'delivery__farmer__first_name', 'delivery__farmer__last_name'],
            lambda g: f"Grade {g.grade_letter}", lambda g: f"{g.delivery.batch_id} | {g.delivery.farmer.first_name} {g.delivery.farmer.last_name}",
            'grades', 'grading', '/manager/grades/{id}'))
        results.append(_search(Loan, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number', 'notes'],
            lambda l: f"KES {l.amount_principal:,.0f}", lambda l: f"{l.farmer.first_name} {l.farmer.last_name} | {l.status or ''}",
            'loans', 'account_balance', '/manager/loans/{id}'))
        results.append(_search(PaymentCycle, ['name'],
            lambda c: c.name, lambda c: c.status or '',
            'payment_cycles', 'payments', '/manager/cycles/{id}'))
        results.append(_search(FarmerPayment, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number'],
            lambda p: f"{p.farmer.first_name} {p.farmer.last_name}", lambda p: f"KES {p.net_amount:,.0f} | {p.payment_status or ''}",
            'payments', 'payments', '/manager/payments/{id}'))
        results.append(_search(DisbursementBatch, ['id', 'notes'],
            lambda b: f"Batch {str(b.id)[:8]}", lambda b: f"KES {b.total_amount:,.0f} | {b.status or ''}",
            'disbursements', 'account_balance_wallet', '/manager/disbursements/{id}'))
        results.append(_search(Inventory, ['batch_id', 'grade', 'product_type'],
            lambda i: i.batch_id, lambda i: f"{i.product_type or ''} {i.grade or ''}",
            'inventory', 'inventory_2', '/manager/inventory/{id}'))
        results.append(_search(Buyer, ['name', 'contact_person', 'phone_number'],
            lambda b: b.name, lambda b: b.contact_person or b.phone_number or '',
            'buyers', 'store', '/manager/sales/{id}'))
        results.append(_search(Sale, ['buyer__name', 'product_type', 'invoice_number'],
            lambda s: f"Invoice {s.invoice_number}" if s.invoice_number else f"KES {s.total_amount:,.0f}",
            lambda s: f"{s.buyer.name} | {s.product_type or ''}",
            'sales', 'receipt_long', '/manager/sales/{id}'))
        results.append(_search(Deduction, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number', 'deduction_type'],
            lambda d: d.deduction_type.replace('_', ' ').title(), lambda d: f"{d.farmer.first_name} {d.farmer.last_name} | KES {d.amount:,.0f}",
            'deductions', 'money_off', '/manager/deductions/{id}'))
        results.append(_search(User, ['first_name', 'last_name', 'email', 'phone_number', 'role'],
            lambda u: f"{u.first_name} {u.last_name}", lambda u: f"{u.email} | {u.role or ''}",
            'users', 'group', '/manager/users/{id}', check_active=False))
        results.append(_search(AuditLog, ['actor__first_name', 'actor__last_name', 'resource_type', 'action', 'resource_id'],
            lambda a: f"{a.action} {a.resource_type}", lambda a: f"{a.actor.first_name} {a.actor.last_name}" if a.actor else 'System',
            'audit_log', 'history', '/manager/audit-log/{id}'))
        return [r for r in results if r['total'] > 0]

    def _search_accountant(self, query, coop_id):
        def _search(model, fields, label_fn, subtitle_fn, type_label, icon, url_pattern):
            qs = model._base_manager.filter(cooperative_id=coop_id)
            if hasattr(model, 'deleted_at'):
                qs = qs.filter(deleted_at__isnull=True)
            if hasattr(model, 'is_active'):
                qs = qs.filter(is_active=True)
            qs = _filter_icontains(qs, query, fields)
            if model is Farmer:
                qs = qs.prefetch_related('memberships')
            return self._format_results(qs, label_fn, subtitle_fn, type_label, icon, url_pattern)

        results = []
        results.append(_search(Farmer, ['first_name', 'last_name', 'memberships__member_number', 'phone_number'],
            lambda f: f"{f.first_name} {f.last_name}", lambda f: f"{self._get_member_number(f, coop_id) or 'N/A'} | {f.county or ''}",
            'farmers', 'person', '/accountant/farmers/{id}'))
        results.append(_search(Loan, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number'],
            lambda l: f"KES {l.amount_principal:,.0f}", lambda l: f"{l.farmer.first_name} {l.farmer.last_name} | {l.status or ''}",
            'loans', 'account_balance', '/accountant/loans/{id}'))
        results.append(_search(PaymentCycle, ['name'],
            lambda c: c.name, lambda c: c.status or '',
            'payment_cycles', 'payments', '/accountant/cycles/{id}'))
        results.append(_search(DisbursementBatch, ['id', 'notes'],
            lambda b: f"Batch {str(b.id)[:8]}", lambda b: f"KES {b.total_amount:,.0f} | {b.status or ''}",
            'disbursements', 'account_balance_wallet', '/accountant/disbursements/{id}'))
        results.append(_search(Deduction, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number', 'deduction_type'],
            lambda d: d.deduction_type.replace('_', ' ').title(), lambda d: f"{d.farmer.first_name} {d.farmer.last_name} | KES {d.amount:,.0f}",
            'deductions', 'money_off', '/accountant/deductions/{id}'))
        results.append(_search(FarmerPayment, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number'],
            lambda p: f"{p.farmer.first_name} {p.farmer.last_name}", lambda p: f"KES {p.net_amount:,.0f} | {p.payment_status or ''}",
            'payments', 'payments', '/accountant/payments/{id}'))
        return [r for r in results if r['total'] > 0]

    def _search_grader(self, query, coop_id):
        def _search(model, fields, label_fn, subtitle_fn, type_label, icon, url_pattern):
            qs = model._base_manager.filter(cooperative_id=coop_id)
            if hasattr(model, 'deleted_at'):
                qs = qs.filter(deleted_at__isnull=True)
            qs = _filter_icontains(qs, query, fields)
            return self._format_results(qs, label_fn, subtitle_fn, type_label, icon, url_pattern)

        results = []
        results.append(_search(Delivery, ['batch_id', 'farmer__first_name', 'farmer__last_name', 'local_id'],
            lambda d: d.batch_id, lambda d: f"{d.farmer.first_name} {d.farmer.last_name} | {d.product_type or ''}",
            'deliveries', 'inventory_2', '/grader/deliveries/{id}'))
        results.append(_search(Grade, ['delivery__batch_id', 'grade_letter', 'delivery__farmer__first_name', 'delivery__farmer__last_name'],
            lambda g: f"Grade {g.grade_letter}", lambda g: f"{g.delivery.batch_id} | {g.delivery.farmer.first_name} {g.delivery.farmer.last_name}",
            'grades', 'grading', '/grader/grades/{id}'))
        return [r for r in results if r['total'] > 0]

    def _search_auditor(self, query, coop_id):
        def _search(model, fields, label_fn, subtitle_fn, type_label, icon, url_pattern, check_active=True):
            qs = model._base_manager.filter(cooperative_id=coop_id)
            if hasattr(model, 'deleted_at'):
                qs = qs.filter(deleted_at__isnull=True)
            if check_active and hasattr(model, 'is_active'):
                qs = qs.filter(is_active=True)
            qs = _filter_icontains(qs, query, fields)
            if model is Farmer:
                qs = qs.prefetch_related('memberships')
            return self._format_results(qs, label_fn, subtitle_fn, type_label, icon, url_pattern)

        results = []
        results.append(_search(AuditLog, ['actor__first_name', 'actor__last_name', 'resource_type', 'action', 'resource_id'],
            lambda a: f"{a.action} {a.resource_type}", lambda a: f"{a.actor.first_name} {a.actor.last_name}" if a.actor else 'System',
            'audit_log', 'history', '/auditor/audit-log/{id}'))
        results.append(_search(Farmer, ['first_name', 'last_name', 'memberships__member_number', 'phone_number'],
            lambda f: f"{f.first_name} {f.last_name}", lambda f: f"{self._get_member_number(f, coop_id) or 'N/A'} | {f.county or ''}",
            'farmers', 'person', '/auditor/farmers/{id}'))
        results.append(_search(Delivery, ['batch_id', 'farmer__first_name', 'farmer__last_name'],
            lambda d: d.batch_id, lambda d: f"{d.farmer.first_name} {d.farmer.last_name} | {d.product_type or ''}",
            'deliveries', 'inventory_2', '/auditor/deliveries/{id}'))
        results.append(_search(Loan, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number'],
            lambda l: f"KES {l.amount_principal:,.0f}", lambda l: f"{l.farmer.first_name} {l.farmer.last_name} | {l.status or ''}",
            'loans', 'account_balance', '/auditor/loans/{id}'))
        results.append(_search(PaymentCycle, ['name'],
            lambda c: c.name, lambda c: c.status or '',
            'payment_cycles', 'payments', '/auditor/cycles/{id}'))
        results.append(_search(FarmerPayment, ['farmer__first_name', 'farmer__last_name', 'farmer__memberships__member_number'],
            lambda p: f"{p.farmer.first_name} {p.farmer.last_name}", lambda p: f"KES {p.net_amount:,.0f} | {p.payment_status or ''}",
            'payments', 'payments', '/auditor/payments/{id}'))
        return [r for r in results if r['total'] > 0]

    def _search_external_auditor(self, query, coop_id):
        def _search(model, fields, label_fn, subtitle_fn, type_label, icon, url_pattern):
            qs = model._base_manager.filter(cooperative_id=coop_id)
            if hasattr(model, 'deleted_at'):
                qs = qs.filter(deleted_at__isnull=True)
            qs = _filter_icontains(qs, query, fields)
            return self._format_results(qs, label_fn, subtitle_fn, type_label, icon, url_pattern)

        results = []
        results.append(_search(AuditLog, ['actor__first_name', 'actor__last_name', 'resource_type', 'action'],
            lambda a: f"{a.action} {a.resource_type}", lambda a: f"{a.actor.first_name} {a.actor.last_name}" if a.actor else 'System',
            'audit_log', 'history', '/external-auditor/audit-trail/{id}'))
        results.append(_search(Loan, ['farmer__first_name', 'farmer__last_name', 'status'],
            lambda l: f"KES {l.amount_principal:,.0f}", lambda l: f"Status: {l.status or ''}",
            'loans', 'account_balance', '/external-auditor/loan-portfolio/{id}'))
        return [r for r in results if r['total'] > 0]

    def _format_results(self, qs, label_fn, subtitle_fn, type_label, icon, url_pattern):
        items = []
        for obj in qs:
            items.append({
                'id': str(getattr(obj, 'id', '')),
                'type': type_label,
                'label': label_fn(obj),
                'subtitle': subtitle_fn(obj),
                'url': url_pattern.format(id=getattr(obj, 'id', '')),
            })

        return {
            'key': type_label,
            'label': type_label.replace('_', ' ').title(),
            'icon': icon,
            'total': len(items),
            'items': items,
        }
