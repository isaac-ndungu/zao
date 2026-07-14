from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.base.constants import UserRole
from apps.conftest import (
    CooperativeFactory,
    DeliveryFactory,
    FarmerFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(coop=None):
    """Return an APIClient authenticated as a manager in *coop*."""
    if coop is None:
        coop = CooperativeFactory()
    user = UserFactory(role=UserRole.MANAGER, is_staff=True, is_active=True)
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    user.cooperative = coop
    user.save(update_fields=["cooperative"])
    return client, coop


def _make_farmer(coop):
    """Return a farmer belonging to *coop*."""
    return FarmerFactory(cooperative=coop)


def _make_delivery(coop, **kwargs):
    farmer = kwargs.pop("farmer", None) or _make_farmer(coop)
    defaults = {
        "farmer": farmer,
        "cooperative": coop,
        "product_type": "MILK",
        "volume_litres": Decimal("10.00"),
        "status": "PENDING",
        "batch_id": f"BAT{timezone.now().strftime('%H%M%S%f')}",
    }
    defaults.update(kwargs)
    return DeliveryFactory(**defaults)


# ===========================================================================
# 1. map action
# ===========================================================================

class TestMapAction:
    def test_returns_delivery_with_own_coords(self):
        client, coop = _make_client()
        d = _make_delivery(coop, latitude=Decimal("1.234567"), longitude=Decimal("36.789012"))

        resp = client.get("/api/deliveries/map/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["id"] == d.id
        assert float(resp.data[0]["latitude"]) == 1.234567

    def test_coalesces_farmer_coords(self):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        farmer.latitude = Decimal("-1.111111")
        farmer.longitude = Decimal("37.111111")
        farmer.save(update_fields=["latitude", "longitude"])
        d = _make_delivery(coop, farmer=farmer, latitude=None, longitude=None)

        resp = client.get("/api/deliveries/map/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert float(resp.data[0]["latitude"]) == -1.111111

    def test_filters_out_null_coords(self):
        client, coop = _make_client()
        _make_delivery(coop, latitude=None, longitude=None)

        resp = client.get("/api/deliveries/map/")
        assert resp.status_code == 200
        assert len(resp.data) == 0

    def test_filter_by_date(self):
        client, coop = _make_client()
        today = timezone.now().date()
        _make_delivery(coop, latitude=Decimal("1.0"), longitude=Decimal("36.0"),
                       date_delivered=timezone.now())
        _make_delivery(coop, latitude=Decimal("1.0"), longitude=Decimal("36.0"),
                       date_delivered=timezone.now() - timedelta(days=3))

        resp = client.get(f"/api/deliveries/map/?date={today}")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_filter_by_grade(self):
        client, coop = _make_client()
        _make_delivery(coop, latitude=Decimal("1.0"), longitude=Decimal("36.0"),
                       grade="A", status="GRADED")
        _make_delivery(coop, latitude=Decimal("1.0"), longitude=Decimal("36.0"),
                       grade="B", status="GRADED")

        resp = client.get("/api/deliveries/map/?grade=A")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["grade"] == "A"


# ===========================================================================
# 2. summary action
# ===========================================================================

class TestSummaryAction:
    def test_empty_summary(self):
        client, _ = _make_client()
        resp = client.get("/api/deliveries/summary/")
        assert resp.status_code == 200
        assert resp.data["total"] == 0
        assert resp.data["pending_grading"] == 0

    def test_counts_by_product_type_and_status(self):
        client, coop = _make_client()
        _make_delivery(coop, product_type="MILK", status="PENDING")
        _make_delivery(coop, product_type="MILK", status="GRADED", grade="A")
        _make_delivery(coop, product_type="COFFEE_CHERRIES", quantity_kg=Decimal("5.00"),
                       volume_litres=None, status="PENDING")

        resp = client.get("/api/deliveries/summary/")
        assert resp.data["total"] == 3
        assert resp.data["pending_grading"] == 2

        by_type = {row["product_type"]: row["count"] for row in resp.data["by_product_type"]}
        assert by_type["MILK"] == 2
        assert by_type["COFFEE_CHERRIES"] == 1

        by_status = {row["status"]: row["count"] for row in resp.data["by_status"]}
        assert by_status["PENDING"] == 2
        assert by_status["GRADED"] == 1


# ===========================================================================
# 3. batches action
# ===========================================================================

class TestBatchesAction:
    def test_aggregated_list(self):
        client, coop = _make_client()
        _make_delivery(coop, batch_id="BAT001", volume_litres=Decimal("10.00"))
        _make_delivery(coop, batch_id="BAT002", volume_litres=Decimal("20.00"))
        _make_delivery(coop, batch_id="BAT003", quantity_kg=Decimal("5.00"), volume_litres=None)

        resp = client.get("/api/deliveries/batches/")
        assert resp.status_code == 200
        assert resp.data["count"] == 3

    def test_detail_by_batch_id(self):
        client, coop = _make_client()
        d = _make_delivery(coop, batch_id="BAT100", volume_litres=Decimal("10.00"))

        resp = client.get("/api/deliveries/batches/?batch_id=BAT100")
        assert resp.status_code == 200
        assert resp.data["batch_id"] == "BAT100"
        assert resp.data["delivery_count"] == 1
        assert float(resp.data["total_volume_litres"]) == 10.00

    def test_batch_not_found(self):
        client, _ = _make_client()
        resp = client.get("/api/deliveries/batches/?batch_id=NONEXISTENT")
        assert resp.status_code == 404

    def test_date_filter_on_aggregated(self):
        client, coop = _make_client()
        _make_delivery(coop, batch_id="BAT300", date_delivered=timezone.now())
        _make_delivery(coop, batch_id="BAT400",
                       date_delivered=timezone.now() - timedelta(days=10))

        resp = client.get(
            f"/api/deliveries/batches/?date_from={(timezone.now() - timedelta(days=1)).date()}"
        )
        assert resp.status_code == 200
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["batch_id"] == "BAT300"


# ===========================================================================
# 4-10. DeliveryCreateSerializer validation
# ===========================================================================

def _create_delivery(data, client, coop):
    """POST to the create endpoint and return the response."""
    return client.post("/api/deliveries/", data, format="json")


def _base_payload(coop, farmer):
    """Minimal valid payload for a MILK delivery."""
    return {
        "farmer": str(farmer.id),
        "product_type": "MILK",
        "volume_litres": "10.00",
        "status": "PENDING",
        "date_delivered": (timezone.now() - timedelta(hours=1)).isoformat(),
    }


class TestCreateSerializerValidation:
    # -- 4. MILK requires volume_litres ------------------------------------
    def test_milk_requires_volume_litres(self):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        payload = _base_payload(coop, farmer)
        payload["volume_litres"] = None

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 400
        assert "volume_litres" in resp.data

    # -- 5. COFFEE_CHERRIES requires quantity_kg ---------------------------
    def test_coffee_cherries_requires_quantity_kg(self):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        payload = _base_payload(coop, farmer)
        payload["product_type"] = "COFFEE_CHERRIES"
        payload.pop("volume_litres")
        payload["quantity_kg"] = None

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 400
        assert "quantity_kg" in resp.data

    def test_honey_requires_quantity_kg(self):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        payload = _base_payload(coop, farmer)
        payload["product_type"] = "HONEY"
        payload.pop("volume_litres")
        payload["quantity_kg"] = None

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 400
        assert "quantity_kg" in resp.data

    # -- 6. GRADED status requires grade ------------------------------------
    def test_graded_requires_grade(self):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        payload = _base_payload(coop, farmer)
        payload["status"] = "GRADED"
        payload["grade"] = ""

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 400
        assert "grade" in resp.data

    # -- 7. REJECTED status requires rejection_reason -----------------------
    def test_rejected_requires_rejection_reason(self):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        payload = _base_payload(coop, farmer)
        payload["status"] = "REJECTED"
        payload["rejection_reason"] = ""

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 400
        assert "rejection_reason" in resp.data

    # -- 8. Future date rejected -------------------------------------------
    def test_future_date_rejected(self):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        payload = _base_payload(coop, farmer)
        payload["date_delivered"] = (timezone.now() + timedelta(days=1)).isoformat()

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 400
        assert "date_delivered" in resp.data

    # -- 9. Too-old date rejected ------------------------------------------
    def test_too_old_date_rejected(self):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        payload = _base_payload(coop, farmer)
        payload["date_delivered"] = (timezone.now() - timedelta(days=8)).isoformat()

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 400
        assert "date_delivered" in resp.data

    # -- 10. Farmer required on create -------------------------------------
    def test_farmer_required_on_create(self):
        client, coop = _make_client()
        payload = _base_payload(coop, _make_farmer(coop))
        payload.pop("farmer")

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 400
        assert "farmer" in resp.data

    # -- Bonus: farmer from wrong coop rejected -----------------------------
    def test_farmer_from_different_coop_rejected(self):
        client, coop = _make_client()
        other_coop = CooperativeFactory()
        foreign_farmer = _make_farmer(other_coop)
        payload = _base_payload(coop, foreign_farmer)

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 400
        assert "farmer" in resp.data

    # -- Bonus: inactive farmer rejected -----------------------------------
    def test_inactive_farmer_rejected(self):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        farmer.is_active = False
        farmer.save(update_fields=["is_active"])
        payload = _base_payload(coop, farmer)

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 400
        assert "farmer" in resp.data

    # -- Happy path --------------------------------------------------------
    @patch("apps.deliveries.views.send_delivery_sms.delay")
    def test_valid_milk_delivery_created(self, mock_sms):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        payload = _base_payload(coop, farmer)

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 201
        assert resp.data["product_type"] == "MILK"
        mock_sms.assert_called_once()

    @patch("apps.deliveries.views.send_delivery_sms.delay")
    def test_valid_graded_delivery_with_grade(self, mock_sms):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        payload = _base_payload(coop, farmer)
        payload["status"] = "GRADED"
        payload["grade"] = "A"

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 201
        assert resp.data["grade"] == "A"

    @patch("apps.deliveries.views.send_delivery_sms.delay")
    def test_valid_rejected_delivery_with_reason(self, mock_sms):
        client, coop = _make_client()
        farmer = _make_farmer(coop)
        payload = _base_payload(coop, farmer)
        payload["status"] = "REJECTED"
        payload["rejection_reason"] = "Contaminated"

        resp = _create_delivery(payload, client, coop)
        assert resp.status_code == 201
        assert resp.data["rejection_reason"] == "Contaminated"
