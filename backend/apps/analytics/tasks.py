import csv
import io
import logging
import traceback
from datetime import date, timedelta

from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from apps.base.models import AuditLog, AuditAction
from apps.notifications.email import send_export_failed
from apps.base.utils import log_audit
from apps.cooperatives.models import Cooperative

from .cache import invalidate_analytics_cache
from .models import AnalyticsExportTask, AnalyticsSnapshot, ExportStatus, MaterializedAnalytics, PeriodType
from .queries.cooperative import (
    get_dashboard as get_coop_dashboard,
    get_production as get_coop_production,
    get_financial as get_coop_financial,
    get_farmers as get_coop_farmers,
    get_sales as get_coop_sales,
    get_loans as get_coop_loans,
    get_operations as get_coop_operations,
    get_disbursements as get_coop_disbursements,
)
from .queries.admin import (
    get_admin_dashboard,
    get_admin_production,
    get_admin_financial,
    get_admin_farmers,
    get_admin_sales,
    get_admin_loans,
    get_admin_operations,
    get_admin_disbursements,
    get_admin_seasonal,
    get_admin_payment_efficiency,
    get_admin_farmer_retention,
)

logger = logging.getLogger(__name__)

COOP_QUERY_MAP = {
    'dashboard': get_coop_dashboard,
    'production': get_coop_production,
    'financial': get_coop_financial,
    'farmers': get_coop_farmers,
    'sales': get_coop_sales,
    'loans': get_coop_loans,
    'operations': get_coop_operations,
    'disbursements': get_coop_disbursements,
}

ADMIN_QUERY_MAP = {
    'dashboard': get_admin_dashboard,
    'production': get_admin_production,
    'financial': get_admin_financial,
    'farmers': get_admin_farmers,
    'sales': get_admin_sales,
    'loans': get_admin_loans,
    'operations': get_admin_operations,
    'disbursements': get_admin_disbursements,
    'seasonal': get_admin_seasonal,
    'payment_efficiency': get_admin_payment_efficiency,
    'farmer_retention': get_admin_farmer_retention,
}

QUERY_FN_KEY_MAP = {
    'dashboard': 'dashboard',
    'production': 'dashboard.production',
    'financial': 'dashboard.financial',
    'farmers': 'dashboard.farmers',
    'sales': 'dashboard.sales',
    'loans': 'dashboard.loans',
    'operations': 'dashboard.operations',
    'disbursements': 'dashboard.disbursements',
}


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------


def _compute_and_save_snapshot(cooperative_id, period_type, start_date, end_date):
    """Compute cooperative metrics and save as AnalyticsSnapshot."""
    data = get_coop_dashboard(
        cooperative_id=cooperative_id,
        start_date=start_date,
        end_date=end_date,
    )
    obj, created = AnalyticsSnapshot.objects.update_or_create(
        cooperative_id=cooperative_id,
        period_type=period_type,
        period_start=start_date,
        defaults={
            'period_end': end_date,
            'data': data,
            'schema_version': 1,
        },
    )
    invalidate_analytics_cache(cooperative_id=cooperative_id, scope='cooperative')
    return obj


@shared_task(bind=True, max_retries=2, default_retry_delay=300, soft_time_limit=120, time_limit=300)
def compute_coop_snapshot(self, cooperative_id, period_type, start_date_str, end_date_str):
    """Compute snapshot for a single cooperative."""
    start = date.fromisoformat(start_date_str)
    end = date.fromisoformat(end_date_str)
    try:
        with transaction.atomic():
            _compute_and_save_snapshot(cooperative_id, period_type, start, end)
    except Exception as exc:
        logger.exception('Snapshot failed for coop %s', cooperative_id)
        try:
            log_audit(
                action=AuditAction.SNAPSHOT_FAILED,
                resource_type='AnalyticsSnapshot',
                resource_id=cooperative_id,
                new_value={
                    'error': str(exc),
                    'period_type': period_type,
                    'start': start_date_str,
                    'end': end_date_str,
                },
            )
        except Exception:
            pass
        raise self.retry(exc=exc)


@shared_task(soft_time_limit=600, time_limit=1200)
def compute_daily_snapshots():
    today = date.today()
    yesterday = today - timedelta(days=1)
    for coop in Cooperative.objects.filter(is_active=True).iterator():
        compute_coop_snapshot.delay(
            str(coop.id), PeriodType.DAILY,
            yesterday.isoformat(), today.isoformat(),
        )


@shared_task(soft_time_limit=600, time_limit=1200)
def compute_weekly_snapshots():
    today = date.today()
    week_ago = today - timedelta(days=7)
    for coop in Cooperative.objects.filter(is_active=True).iterator():
        compute_coop_snapshot.delay(
            str(coop.id), PeriodType.WEEKLY,
            week_ago.isoformat(), today.isoformat(),
        )


@shared_task(soft_time_limit=600, time_limit=1200)
def compute_monthly_snapshots():
    today = date.today()
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    for coop in Cooperative.objects.filter(is_active=True).iterator():
        compute_coop_snapshot.delay(
            str(coop.id), PeriodType.MONTHLY,
            last_month_start.isoformat(), last_month_end.isoformat(),
        )


@shared_task(soft_time_limit=300, time_limit=600)
def compute_materialized_monthly():
    today = date.today()
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    data = get_admin_dashboard(start_date=last_month_start, end_date=last_month_end)

    MaterializedAnalytics.objects.update_or_create(
        period_type=PeriodType.MONTHLY,
        period_start=last_month_start,
        defaults={
            'period_end': last_month_end,
            'data': data,
            'schema_version': 1,
        },
    )
    invalidate_analytics_cache(cooperative_id=None, scope='global')


# ---------------------------------------------------------------------------
# Cache warming
# ---------------------------------------------------------------------------


@shared_task(soft_time_limit=120, time_limit=300)
def warm_analytics_cache():
    """Pre-compute cache for recently accessed cooperatives."""
    from datetime import datetime
    now_dt = timezone.now()

    access_pattern = 'analytics:last_access:*'
    try:
        from django.core.cache import cache as dj_cache
        backend = dj_cache.client.get_client()
        keys = backend.keys(access_pattern)
    except Exception:
        keys = []

    for key in keys:
        try:
            coop_id = key.split(':')[-1]
            if coop_id in ('None', 'global', ''):
                continue
            ttl = backend.ttl(key)
            if ttl and ttl > 0:
                for action_name in ('dashboard', 'production', 'financial'):
                    cache_key = f'analytics:warm:{coop_id}:{action_name}'
                    if dj_cache.get(cache_key):
                        continue
                    fn = COOP_QUERY_MAP.get(action_name)
                    if fn:
                        end = now_dt.date()
                        start = end - timedelta(days=30)
                        result = fn(cooperative_id=coop_id, start_date=start, end_date=end)
                        if result:
                            from .cache import set_cached_analytics
                            set_cached_analytics(f'analytics:computed:{coop_id}:{action_name}', result, ttl=600)
                            dj_cache.set(cache_key, True, 3600)
        except Exception:
            logger.exception('Cache warm failed for key %s', key)


# ---------------------------------------------------------------------------
# Leaderboard refresh
# ---------------------------------------------------------------------------


def _leaderboard_redis():
    import redis as redis_module
    return redis_module.Redis.from_url(settings.REDIS_URL)


@shared_task(soft_time_limit=60, time_limit=120)
def refresh_coop_leaderboard(cooperative_id, period='30d'):
    """Compute leaderboard data into Redis sorted sets for one cooperative."""
    from datetime import datetime
    r = _leaderboard_redis()
    today = date.today()
    if period == '30d':
        start = today - timedelta(days=30)
    elif period == '7d':
        start = today - timedelta(days=7)
    elif period == '1y':
        start = today - timedelta(days=365)
    else:
        start = today - timedelta(days=30)

    prefix = f'leaderboard:{cooperative_id or "global"}:{period}'

    volume_key = f'{prefix}:volume'
    r.delete(volume_key)
    from apps.deliveries.models import Delivery
    from django.db.models import Sum
    from .queries.common import coalesce_sum
    volume_qs = Delivery.objects.filter(
        cooperative_id=cooperative_id,
        date_delivered__gte=start, date_delivered__lt=today,
    )
    volume_data = dict(
        volume_qs.values('farmer_id')
        .annotate(total=coalesce_sum(Sum('quantity_kg')))
        .values_list('farmer_id', 'total')
    )
    if volume_data:
        r.zadd(volume_key, {str(k): float(v) for k, v in volume_data.items()})
        r.expire(volume_key, 7200)

    payout_key = f'{prefix}:payout'
    r.delete(payout_key)
    from apps.payment_engine.models import FarmerPayment
    payout_qs = FarmerPayment.objects.filter(
        cooperative_id=cooperative_id,
        cycle__end_date__gte=start, cycle__start_date__lt=today,
    )
    payout_data = dict(
        payout_qs.values('farmer_id')
        .annotate(total=coalesce_sum(Sum('net_amount')))
        .values_list('farmer_id', 'total')
    )
    if payout_data:
        r.zadd(payout_key, {str(k): float(v) for k, v in payout_data.items()})
        r.expire(payout_key, 7200)

    buyer_key = f'{prefix}:buyers'
    r.delete(buyer_key)
    from apps.sales.models import Sale
    buyer_qs = Sale.objects.filter(
        cooperative_id=cooperative_id, status='COMPLETED',
        sale_date__gte=start, sale_date__lt=today,
    )
    buyer_data = dict(
        buyer_qs.values('buyer__name')
        .annotate(total=coalesce_sum(Sum('total_amount')))
        .values_list('buyer__name', 'total')
    )
    if buyer_data:
        r.zadd(buyer_key, {str(k): float(v) for k, v in buyer_data.items()})
        r.expire(buyer_key, 7200)


@shared_task(soft_time_limit=300, time_limit=600)
def refresh_leaderboards():
    """Refresh leaderboard for all active cooperatives."""
    for coop in Cooperative.objects.filter(is_active=True).iterator():
        for period in ('30d', '7d', '1y'):
            refresh_coop_leaderboard.delay(str(coop.id), period)


# ---------------------------------------------------------------------------
# Export generation (async path)
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=2, default_retry_delay=60, soft_time_limit=120, time_limit=300)
def generate_export(self, export_task_id):
    """Generate an export CSV and update the AnalyticsExportTask."""
    try:
        task = AnalyticsExportTask.objects.select_related('requested_by').get(id=export_task_id)
    except AnalyticsExportTask.DoesNotExist:
        logger.error('Export task %s not found', export_task_id)
        return

    try:
        task.status = ExportStatus.PROCESSING
        task.save(update_fields=['status'])

        coop_id = str(task.cooperative_id) if task.cooperative_id else None
        params = task.params or {}
        start = date.fromisoformat(params.get('start', date.today().isoformat()))
        end = date.fromisoformat(params.get('end', date.today().isoformat()))

        fn = COOP_QUERY_MAP.get(task.export_type)
        if fn is None:
            raise ValueError(f'Unknown export type: {task.export_type}')

        data = fn(cooperative_id=coop_id, start_date=start, end_date=end)

        buffer = io.StringIO()
        writer = csv.writer(buffer)

        def flatten(prefix, value):
            rows = {}
            if isinstance(value, dict):
                for k, v in value.items():
                    for fk, fv in flatten(f'{prefix}_{k}', v).items():
                        rows[fk] = fv
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    for fk, fv in flatten(f'{prefix}_{i}', v).items():
                        rows[fk] = fv
            else:
                rows[prefix] = value
            return rows

        if isinstance(data, dict) and 'data' in data:
            row_data = flatten('', data['data'])
        else:
            row_data = flatten('', data)

        fieldnames = list(row_data.keys())
        writer.writerow(fieldnames)
        writer.writerow([row_data.get(f, '') for f in fieldnames])

        filename = f'exports/{export_task_id}.csv'
        path = default_storage.save(filename, io.BytesIO(buffer.getvalue().encode('utf-8')))

        if hasattr(default_storage, 'url'):
            download_url = default_storage.url(path)
        else:
            download_url = f'/media/{path}'

        task.status = ExportStatus.COMPLETED
        task.download_url = download_url
        task.row_count = 1
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'download_url', 'row_count', 'completed_at'])

    except Exception as exc:
        logger.exception('Export generation failed for task %s', export_task_id)
        task.status = ExportStatus.FAILED
        task.error_message = str(exc)
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'error_message', 'completed_at'])

        try:
            log_audit(
                action=AuditAction.EXPORT_FAILED,
                resource_type='AnalyticsExportTask',
                resource_id=export_task_id,
                new_value={'error': str(exc), 'export_type': task.export_type},
            )
        except Exception:
            pass

        if task.requested_by and task.requested_by.email:
            try:
                send_export_failed(task, str(exc), getattr(settings, 'FRONTEND_URL', None))
            except Exception:
                pass
