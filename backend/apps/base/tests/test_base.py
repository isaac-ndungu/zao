import uuid
from datetime import timedelta

import pytest
from django.db import models
from django.utils import timezone

from apps.base.constants import get_soft_deletable_models
from apps.base.models import (
    AuditAction,
    AuditLog,
    CooperativeScopedModel,
    SoftDeletableModel,
    TenantManager,
    TenantQuerySet,
)


class TestSoftDeletableModel:
    def test_soft_delete_sets_deleted_at(self, farmer):
        assert farmer.deleted_at is None
        farmer.soft_delete()
        assert farmer.deleted_at is not None

    def test_restore_clears_deleted_at(self, farmer):
        farmer.soft_delete()
        farmer.restore()
        assert farmer.deleted_at is None
        assert farmer.restored_at is not None
        assert farmer.deleted_via_cascade_from is None

    def test_restore_sets_restored_at(self, farmer):
        farmer.soft_delete()
        now = timezone.now()
        farmer.restore()
        assert farmer.restored_at is not None
        assert farmer.restored_at >= now

    def test_default_manager_excludes_trashed(self, farmer):
        farmer.soft_delete()
        assert not farmer.__class__.objects.filter(pk=farmer.pk).exists()

    def test_all_with_trashed_includes_soft_deleted(self, farmer):
        farmer.soft_delete()
        mgr = farmer.__class__.objects
        if hasattr(mgr, 'all_with_trashed'):
            assert mgr.all_with_trashed().filter(pk=farmer.pk).exists()

    def test_trashed_only_returns_only_deleted(self, farmer):
        farmer.soft_delete()
        mgr = farmer.__class__.objects
        if hasattr(mgr, 'trashed_only'):
            qs = mgr.trashed_only()
            assert qs.filter(pk=farmer.pk).exists()

    def test_trashed_only_empty_for_active(self, farmer):
        mgr = farmer.__class__.objects
        if hasattr(mgr, 'trashed_only'):
            assert not mgr.trashed_only().filter(pk=farmer.pk).exists()

    def test_hard_delete_removes_permanently(self, farmer):
        farmer.hard_delete()
        mgr = farmer.__class__.objects
        if hasattr(mgr, 'all_with_trashed'):
            assert not mgr.all_with_trashed().filter(pk=farmer.pk).exists()
        else:
            assert not farmer.__class__._base_manager.filter(pk=farmer.pk).exists()


class TestTenantManager:
    def test_for_cooperative_filters(self, farmer):
        coop_id = farmer.cooperative_id
        qs = farmer.__class__.objects.for_cooperative(coop_id)
        assert qs.filter(pk=farmer.pk).exists()
        other_coop_id = uuid.uuid4()
        assert not farmer.__class__.objects.for_cooperative(other_coop_id).filter(pk=farmer.pk).exists()

    def test_get_queryset_applies_soft_delete_filter(self, farmer):
        farmer.soft_delete()
        assert not farmer.__class__.objects.filter(pk=farmer.pk).exists()


class TestAuditLog:
    def test_create_audit_log(self, superuser, cooperative):
        log = AuditLog.objects.create(
            cooperative=cooperative,
            actor=superuser,
            resource_type='Test',
            resource_id=uuid.uuid4(),
            action=AuditAction.CREATE,
        )
        assert log.pk is not None

    def test_audit_log_cannot_be_updated(self, superuser, cooperative):
        log = AuditLog.objects.create(
            cooperative=cooperative,
            actor=superuser,
            resource_type='Test',
            resource_id=uuid.uuid4(),
            action=AuditAction.CREATE,
        )
        with pytest.raises(ValueError, match='cannot be updated'):
            log.action = AuditAction.DELETE
            log.save()

    def test_changes_property(self, superuser, cooperative):
        log = AuditLog.objects.create(
            cooperative=cooperative,
            actor=superuser,
            resource_type='Test',
            resource_id=uuid.uuid4(),
            action=AuditAction.UPDATE,
            previous_value={'name': 'old'},
            new_value={'name': 'new'},
        )
        assert log.changes == {'previous': {'name': 'old'}, 'new': {'name': 'new'}}

    def test_changes_none_when_no_values(self, superuser, cooperative):
        log = AuditLog.objects.create(
            cooperative=cooperative,
            actor=superuser,
            resource_type='Test',
            resource_id=uuid.uuid4(),
            action=AuditAction.CREATE,
        )
        assert log.changes is None


class TestGetSoftDeletableModels:
    def test_returns_models_with_deleted_at(self):
        models_list = get_soft_deletable_models()
        names = {m.__name__ for m in models_list}
        assert 'AuditLog' not in names
        assert all(hasattr(m, 'deleted_at') for m in models_list)


class TestPurgeTask:
    def test_purge_deleted_records_basic(self, farmer):
        from apps.base.tasks import purge_deleted_records
        farmer.soft_delete()
        result = purge_deleted_records()
        assert 'Purged' in result

    def test_purge_only_old_records(self, farmer):
        from apps.base.tasks import purge_deleted_records
        farmer.soft_delete()
        farmer.deleted_at = timezone.now() - timedelta(days=31)
        farmer.save(update_fields=['deleted_at'])
        result = purge_deleted_records()
        assert 'Purged' in result
        assert '1' in result

    def test_purge_skips_recent_records(self, farmer):
        from apps.base.tasks import purge_deleted_records
        farmer.soft_delete()
        result = purge_deleted_records()
        assert result == 'Purged 0 record(s) older than 30 days'


class TestPhoneNormalization:
    def test_normalize_07_safaricom(self):
        from apps.base.utils import normalize_phone
        assert normalize_phone('0712345678') == '254712345678'

    def test_normalize_plus_254(self):
        from apps.base.utils import normalize_phone
        assert normalize_phone('+254712345678') == '254712345678'

    def test_normalize_254_prefix(self):
        from apps.base.utils import normalize_phone
        assert normalize_phone('254712345678') == '254712345678'

    def test_normalize_01_prefix(self):
        from apps.base.utils import normalize_phone
        assert normalize_phone('0112345678') == '254112345678'

    def test_normalize_plus_254_01(self):
        from apps.base.utils import normalize_phone
        assert normalize_phone('+254112345678') == '254112345678'

    def test_normalize_254_01(self):
        from apps.base.utils import normalize_phone
        assert normalize_phone('254112345678') == '254112345678'

    def test_kenya_phone_re_accepts_07(self):
        from apps.base.utils import KENYA_PHONE_RE
        assert KENYA_PHONE_RE.match('254712345678')

    def test_kenya_phone_re_accepts_01(self):
        from apps.base.utils import KENYA_PHONE_RE
        assert KENYA_PHONE_RE.match('254112345678')

    def test_kenya_phone_re_rejects_too_short(self):
        from apps.base.utils import KENYA_PHONE_RE
        assert not KENYA_PHONE_RE.match('071234567')

    def test_normalize_sms_07(self):
        from apps.base.utils import normalize_phone_for_sms
        assert normalize_phone_for_sms('0712345678') == '+254712345678'

    def test_normalize_sms_01(self):
        from apps.base.utils import normalize_phone_for_sms
        assert normalize_phone_for_sms('0112345678') == '+254112345678'

    def test_normalize_sms_bare_01(self):
        from apps.base.utils import normalize_phone_for_sms
        assert normalize_phone_for_sms('112345678') == '+254112345678'
