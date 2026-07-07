import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.analytics.models import AnalyticsSnapshot, MaterializedAnalytics, PeriodType
from apps.auth_api.models import User
from apps.base.constants import UserRole
from apps.base.utils import log_audit
from apps.cooperatives.models import Cooperative, PaymentModel, ProduceType
from apps.deliveries.models import Delivery, DeliveryStatus, ProductType, Shift
from apps.deductions.models import Deduction
from apps.disbursement.models import (
    BatchStatus, CommandId, DisbursementBatch,
    DisbursementPaymentMethod, DisbursementTransaction, TransactionStatus,
)
from apps.farmers.models import Farmer, FarmerCooperativeMembership, FarmerPaymentMethod
from apps.grading.models import DisputeStatus, FarmerGradeDispute, Grade, GradeLetter, GradePrice
from apps.inventory.models import Inventory, Stock
from apps.legal.models import LegalAcceptance, LegalDocument
from apps.loans.models import GuarantorStatus, Loan, LoanGuarantor, LoanRepayment, LoanStatus
from apps.notifications.models import Notification, NotificationChannel, NotificationType, NotificationStatus
from apps.payment_engine.models import CycleStatus, FarmerPayment, PaymentCycle, PaymentStatus
from apps.routes.models import CollectionRoute, DayOfWeekChoices, RouteStop
from apps.sales.models import Buyer, Sale, SaleInventoryLineItem, SaleStatus, SaleUnit


FARMER_FIRST_NAMES = [
    "James", "Grace", "Peter", "Mary", "John", "Ann", "Samuel", "Catherine",
    "Joseph", "Faith", "Robert", "Lucy", "Daniel", "Esther", "Michael",
    "Ruth", "Stephen", "Pauline", "Francis", "Beatrice",
]
FARMER_LAST_NAMES = [
    "Kamau", "Wanjiku", "Mwangi", "Wambui", "Kariuki", "Njeri", "Gitau",
    "Wairimu", "Muigai", "Njoki", "Karanja", "Muthoni", "Owino", "Wanjiru",
    "Ndegwa", "Kinyanjui", "Mureithi", "Njoroge", "Kibaki", "Muthoni",
]

GDC_FARMER_PHONES = ["0716227503"] + [f"25472{i:07d}" for i in range(2000002, 2000021)]
NCC_FARMER_PHONES = [f"25472{i:07d}" for i in range(3000001, 3000021)]


def make_password():
    from django.utils.crypto import get_random_string
    return get_random_string(length=72)


class Command(BaseCommand):
    help = "Seed comprehensive presentation data for Zao"

    def add_arguments(self, parser):
        parser.add_argument("--skip-legal", action="store_true", help="Skip legal documents")
        parser.add_argument("--skip-payments", action="store_true", help="Skip payment engine")

    def handle(self, *args, **options):
        import sys
        sys.stdout.write("H0\n"); sys.stdout.flush()
        with transaction.atomic():
            sys.stdout.write("H1\n"); sys.stdout.flush()
            if not options["skip_legal"]:
                self._sync_legal_documents()
            sys.stdout.write("H2\n"); sys.stdout.flush()
            self._seed_superadmin()
            sys.stdout.write("H3\n"); sys.stdout.flush()
            self._seed_cooperatives()
            sys.stdout.write("H4\n"); sys.stdout.flush()
            self._seed_staff_users()
            sys.stdout.write("H5\n"); sys.stdout.flush()
            self._seed_farmers()
            sys.stdout.write("H6\n"); sys.stdout.flush()
            self._seed_grade_prices()
            sys.stdout.write("H7\n"); sys.stdout.flush()
            self._seed_deliveries()
            sys.stdout.write("H8\n"); sys.stdout.flush()
            self._seed_grades_and_inventory()
            sys.stdout.write("H9\n"); sys.stdout.flush()
            self._seed_buyers()
            sys.stdout.write("H10\n"); sys.stdout.flush()
            self._seed_sales_and_inventory()
            sys.stdout.write("H11\n"); sys.stdout.flush()
            self._seed_payment_cycles()
            sys.stdout.write("H12\n"); sys.stdout.flush()

            if not options["skip_payments"]:
                self._seed_farmer_payments()
                sys.stdout.write("H13\n"); sys.stdout.flush()
                self._seed_deductions()
                self._seed_loans()
                self._seed_disbursements()

            self._seed_routes()
            sys.stdout.write("H14\n"); sys.stdout.flush()
            self._seed_notifications()
            sys.stdout.write("H15\n"); sys.stdout.flush()
            self._seed_audit_logs()
            sys.stdout.write("H16\n"); sys.stdout.flush()
            self._seed_analytics_snapshots()
            sys.stdout.write("H17\n"); sys.stdout.flush()

        self._print_summary()

    # -------------------------------------------------------------------------
    # Legal Documents
    # -------------------------------------------------------------------------
    def _sync_legal_documents(self):
        import os
        from django.conf import settings
        FIXTURES_DIR = settings.BASE_DIR / "apps" / "legal" / "fixtures"
        for spec in [
            {"slug": "privacy-policy", "title": "Privacy Policy", "file": "privacy-policy.md", "requires_acceptance": True},
            {"slug": "terms-of-service", "title": "Terms and Conditions", "file": "terms-of-service.md", "requires_acceptance": True},
        ]:
            filepath = FIXTURES_DIR / spec["file"]
            if not filepath.exists():
                self.stdout.write(self.style.WARNING(f"Fixture not found: {filepath}"))
                continue
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            LegalDocument.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "title": spec["title"], "content": content, "version": 1,
                    "is_active": True, "requires_acceptance": spec["requires_acceptance"],
                    "published_at": timezone.now(),
                },
            )

    # -------------------------------------------------------------------------
    # Superadmin
    # -------------------------------------------------------------------------
    def _seed_superadmin(self):
        self.superadmin, _ = User.objects.get_or_create(
            email="authpass8@gmail.com",
            defaults={
                "phone_number": "254700000001", "first_name": "Zao", "last_name": "Admin",
                "role": UserRole.ADMIN, "is_superuser": True, "is_staff": True, "is_active": True,
            },
        )
        self.superadmin.set_password("Admin@Zao2026")
        self.superadmin.save(update_fields=["password"])

    # -------------------------------------------------------------------------
    # Cooperatives
    # -------------------------------------------------------------------------
    def _seed_cooperatives(self):
        self.gdc, _ = Cooperative.objects.get_or_create(
            registration_number="CS/2019/0042",
            defaults={
                "name": "Githunguri Dairy Cooperative", "county": "Kiambu",
                "sub_county": "Githunguri", "ward": "Githunguri Ward",
                "produce_type": ProduceType.DAIRY, "payment_model": PaymentModel.FIXED_PRICE,
                "levy_percentage": Decimal("2.50"), "monthly_fee": Decimal("200.00"),
                "prefix": "GDC", "mpesa_shortcode": "247001", "till_number": "247001",
                "phone_number": "0712000001", "email": "info@githunguridairy.co.ke",
                "physical_address": "Githunguri Town, Kiambu",
                "is_active": True, "is_verified": True, "year_established": 2019,
                "last_member_sequence": 0,
            },
        )
        self.ncc, _ = Cooperative.objects.get_or_create(
            registration_number="CS/2020/0118",
            defaults={
                "name": "Nyeri Coffee Cooperative", "county": "Nyeri",
                "sub_county": "Nyeri Central", "ward": "Nyeri Central Ward",
                "produce_type": ProduceType.COFFEE, "payment_model": PaymentModel.REVENUE_SHARE,
                "levy_percentage": Decimal("3.00"), "monthly_fee": Decimal("150.00"),
                "prefix": "NCC", "mpesa_shortcode": "547001", "till_number": "547001",
                "phone_number": "0713000001", "email": "info@nyericoffee.co.ke",
                "physical_address": "Nyeri Town, Nyeri",
                "is_active": True, "is_verified": True, "year_established": 2020,
                "last_member_sequence": 0,
            },
        )

    # -------------------------------------------------------------------------
    # Staff Users
    # -------------------------------------------------------------------------
    def _seed_staff_users(self):
        staff_specs = [
            {"email": "isaacndungu478@gmail.com", "first_name": "Isaac", "last_name": "Ndungu",
             "role": UserRole.MANAGER, "password": "Manager@2026", "coop": self.gdc, "phone": "254711222001", "two_fa": True},
            {"email": "isaacn2101@gmail.com", "first_name": "Isaac", "last_name": "N",
             "role": UserRole.ACCOUNTANT, "password": "Account@2026", "coop": self.gdc, "phone": "254711222002", "two_fa": True},
            {"email": "davision.2024@gmail.com", "first_name": "Davis", "last_name": "Ion",
             "role": UserRole.GRADER, "password": "Grader@2026", "coop": self.gdc, "phone": "254711222003", "two_fa": False},
            {"email": "manager@ncc.demo", "first_name": "John", "last_name": "Njoroge",
             "role": UserRole.MANAGER, "password": "Manager@2026", "coop": self.ncc, "phone": "254711222004", "two_fa": True},
            {"email": "accountant@ncc.demo", "first_name": "Mary", "last_name": "Wambui",
             "role": UserRole.ACCOUNTANT, "password": "Account@2026", "coop": self.ncc, "phone": "254711222005", "two_fa": True},
            {"email": "grader@ncc.demo", "first_name": "Peter", "last_name": "Kariuki",
             "role": UserRole.GRADER, "password": "Grader@2026", "coop": self.ncc, "phone": "254711222006", "two_fa": False},
        ]
        accepted_at = timezone.now() - timedelta(days=7)
        legal_docs = list(LegalDocument.objects.filter(is_active=True))

        self.all_staff = []
        for spec in staff_specs:
            user, _ = User.objects.get_or_create(
                email=spec["email"],
                defaults={
                    "phone_number": spec["phone"], "first_name": spec["first_name"],
                    "last_name": spec["last_name"], "role": spec["role"],
                    "cooperative": spec["coop"], "two_fa_enabled": spec["two_fa"],
                    "must_change_password": False, "is_active": True,
                },
            )
            user.set_password(spec["password"])
            user.save(update_fields=["password"])
            self.all_staff.append(user)

            for doc in legal_docs:
                LegalAcceptance.objects.get_or_create(
                    user=user, document=doc, version=doc.version,
                    defaults={"accepted_at": accepted_at, "ip_address": "127.0.0.1"},
                )

        self.gdc_manager = self.all_staff[0]
        self.gdc_accountant = self.all_staff[1]
        self.gdc_grader = self.all_staff[2]
        self.ncc_manager = self.all_staff[3]

    # -------------------------------------------------------------------------
    # Farmers
    # -------------------------------------------------------------------------
    def _seed_farmers(self):
        import sys
        today_d = timezone.now().date()
        join_date = today_d - timedelta(days=90)
        self.gdc_farmers = []
        self.ncc_farmers = []
        sys.stdout.write("F0\n"); sys.stdout.flush()

        gdc_farmers_bulk = []
        for i in range(20):
            first, last = FARMER_FIRST_NAMES[i], FARMER_LAST_NAMES[i]
            phone = GDC_FARMER_PHONES[i]
            gdc_farmers_bulk.append(Farmer(
                cooperative=self.gdc, first_name=first, last_name=last,
                email=f"{first.lower()}.{last.lower()}{i}@gdc.farmer.demo",
                id_number=f"{12345670 + i:08d}", phone_number=phone,
                county="Kiambu", sub_county="Githunguri", ward="Githunguri Ward",
                village="Kamiti", is_active=True, date_joined=join_date,
            ))
        sys.stdout.write("F1\n"); sys.stdout.flush()
        created_gdc = Farmer.objects.bulk_create(gdc_farmers_bulk, batch_size=20)
        sys.stdout.write("F2\n"); sys.stdout.flush()

        gdc_memberships = []
        gdc_users = []
        for i, farmer in enumerate(created_gdc):
            if i % 3 == 0:
                pmeth = FarmerPaymentMethod.CASH
                bank_name, bank_acct = "", ""
            elif i % 3 == 1:
                pmeth = FarmerPaymentMethod.BANK
                bank_name, bank_acct = "Equity Bank", f"123456789{i:04d}"
            else:
                pmeth = FarmerPaymentMethod.M_PESA
                bank_name, bank_acct = "", ""
            gdc_memberships.append(FarmerCooperativeMembership(
                farmer=farmer, cooperative=self.gdc,
                member_number=f"GDC-{today_d.year}-{i+1:04d}",
                payment_method=pmeth, mpesa_number=GDC_FARMER_PHONES[i],
                bank_name=bank_name, bank_account=bank_acct,
            ))
            gdc_users.append(User(
                email=farmer.email, phone_number=GDC_FARMER_PHONES[i],
                first_name=farmer.first_name, last_name=farmer.last_name,
                password=make_password(), role=UserRole.FARMER, cooperative=self.gdc,
            ))
        sys.stdout.write("F3\n"); sys.stdout.flush()
        FarmerCooperativeMembership.objects.bulk_create(gdc_memberships, batch_size=20)
        sys.stdout.write("F4\n"); sys.stdout.flush()

        created_users = User.objects.bulk_create(gdc_users, batch_size=20)
        sys.stdout.write("F5\n"); sys.stdout.flush()
        for farmer, user in zip(created_gdc, created_users):
            user.set_unusable_password()
            farmer.user = user
        User.objects.bulk_update(created_users, ["password"], batch_size=20)
        sys.stdout.write("F6\n"); sys.stdout.flush()
        Farmer.objects.bulk_update(created_gdc, ["user"], batch_size=20)
        sys.stdout.write("F7\n"); sys.stdout.flush()
        self.gdc_farmers = list(created_gdc)

        # NCC farmers
        ncc_farmers_bulk = []
        for i in range(20):
            first, last = FARMER_FIRST_NAMES[i], FARMER_LAST_NAMES[i]
            phone = NCC_FARMER_PHONES[i]
            ncc_farmers_bulk.append(Farmer(
                cooperative=self.ncc, first_name=first, last_name=last,
                email=f"{first.lower()}.{last.lower()}{i}@ncc.farmer.demo",
                id_number=f"{22345670 + i:08d}", phone_number=phone,
                county="Nyeri", sub_county="Nyeri Central", ward="Nyeri Central Ward",
                village="Kiganjo", is_active=True, date_joined=join_date,
            ))
        sys.stdout.write("F8\n"); sys.stdout.flush()
        created_ncc = Farmer.objects.bulk_create(ncc_farmers_bulk, batch_size=20)
        sys.stdout.write("F9\n"); sys.stdout.flush()

        ncc_memberships = []
        ncc_users = []
        for i, farmer in enumerate(created_ncc):
            if i % 2 == 0:
                pmeth = FarmerPaymentMethod.M_PESA
                bank_name, bank_acct = "", ""
            else:
                pmeth = FarmerPaymentMethod.BANK
                bank_name, bank_acct = "KCB Bank", f"223456789{i:04d}"
            ncc_memberships.append(FarmerCooperativeMembership(
                farmer=farmer, cooperative=self.ncc,
                member_number=f"NCC-{today_d.year}-{i+1:04d}",
                payment_method=pmeth, mpesa_number=NCC_FARMER_PHONES[i],
                bank_name=bank_name, bank_account=bank_acct,
            ))
            ncc_users.append(User(
                email=farmer.email, phone_number=NCC_FARMER_PHONES[i],
                first_name=farmer.first_name, last_name=farmer.last_name,
                password=make_password(), role=UserRole.FARMER, cooperative=self.ncc,
            ))
        sys.stdout.write("F10\n"); sys.stdout.flush()
        FarmerCooperativeMembership.objects.bulk_create(ncc_memberships, batch_size=20)
        sys.stdout.write("F11\n"); sys.stdout.flush()
        created_ncc_users = User.objects.bulk_create(ncc_users, batch_size=20)
        sys.stdout.write("F12\n"); sys.stdout.flush()
        for farmer, user in zip(created_ncc, created_ncc_users):
            user.set_unusable_password()
            farmer.user = user
        User.objects.bulk_update(created_ncc_users, ["password"], batch_size=20)
        sys.stdout.write("F13\n"); sys.stdout.flush()
        Farmer.objects.bulk_update(created_ncc, ["user"], batch_size=20)
        sys.stdout.write("F14\n"); sys.stdout.flush()
        self.ncc_farmers = list(created_ncc)

        self.gdc_demo_farmer = self.gdc_farmers[0]
        self.stdout.write(
            f"  {len(self.gdc_farmers)} GDC + {len(self.ncc_farmers)} NCC farmers created"
        )

    # -------------------------------------------------------------------------
    # Grade Prices
    # -------------------------------------------------------------------------
    def _seed_grade_prices(self):
        effective = date.today() - timedelta(days=90)
        gdc_prices = [(GradeLetter.PREMIUM, "65"), (GradeLetter.A, "55"),
                       (GradeLetter.B, "48"), (GradeLetter.C, "38")]
        ncc_prices = [(GradeLetter.PREMIUM, "95"), (GradeLetter.A, "90"),
                       (GradeLetter.B, "72"), (GradeLetter.C, "55")]
        for letter, price in gdc_prices + ncc_prices:
            GradePrice.objects.get_or_create(
                grade_letter=letter, effective_from=effective,
                defaults={"price_per_unit": Decimal(price)},
            )

    # -------------------------------------------------------------------------
    # Deliveries (bulk_create, pre-set batch_id to bypass signal)
    # -------------------------------------------------------------------------
    def _seed_deliveries(self):
        now = timezone.now()
        base = now.replace(hour=6, minute=0, second=0, microsecond=0)
        today_d = now.date()

        def make_delivery_batch(coop, farmer, batch_id, product_type, qty, status, shift, delivered, grader, lat, lng):
            return Delivery(
                cooperative=coop, farmer=farmer, batch_id=batch_id,
                product_type=product_type,
                volume_litres=qty if product_type == ProductType.MILK else None,
                quantity_kg=qty if product_type == ProductType.COFFEE_CHERRIES else None,
                status=status, shift=shift, date_delivered=delivered,
                grader=grader, latitude=lat, longitude=lng, is_synced=True,
            )

        # Advance cooperative sequence to avoid collisions
        self.gdc.last_delivery_date = today_d
        self.gdc.last_delivery_sequence = 471
        self.gdc.save(update_fields=["last_delivery_date", "last_delivery_sequence"])
        self.ncc.last_delivery_date = today_d
        self.ncc.last_delivery_sequence = 210
        self.ncc.save(update_fields=["last_delivery_date", "last_delivery_sequence"])

        m1 = base - timedelta(days=90)
        m2 = base - timedelta(days=60)
        m3 = base - timedelta(days=14)

        deliveries = []

        # GDC Month 1: 180 graded
        for i in range(180):
            f = self.gdc_farmers[i % 20]
            deliveries.append(make_delivery_batch(
                self.gdc, f, f"PRODUCE-{m1.date():%Y%m%d}-{i+1:03d}",
                ProductType.MILK, Decimal(str(round(12.0 + (i % 15) * 1.5, 2))),
                DeliveryStatus.GRADED, Shift.AM if i % 10 < 6 else Shift.PM,
                m1 + timedelta(days=i % 30), self.gdc_grader, f.latitude, f.longitude,
            ))

        # GDC Month 2: 210 graded
        for i in range(210):
            f = self.gdc_farmers[i % 20]
            deliveries.append(make_delivery_batch(
                self.gdc, f, f"PRODUCE-{m2.date():%Y%m%d}-{i+181:03d}",
                ProductType.MILK, Decimal(str(round(14.0 + (i % 18) * 1.2, 2))),
                DeliveryStatus.GRADED, Shift.AM if i % 10 < 6 else Shift.PM,
                m2 + timedelta(days=i % 30), self.gdc_grader, f.latitude, f.longitude,
            ))

        # GDC Month 3: 77 graded
        for i in range(77):
            f = self.gdc_farmers[i % 20]
            deliveries.append(make_delivery_batch(
                self.gdc, f, f"PRODUCE-{m3.date():%Y%m%d}-{i+391:03d}",
                ProductType.MILK, Decimal(str(round(10.0 + (i % 12) * 1.8, 2))),
                DeliveryStatus.GRADED, Shift.AM if i % 10 < 6 else Shift.PM,
                m3 + timedelta(days=i % 14), self.gdc_grader, f.latitude, f.longitude,
            ))

        # GDC Pending today: 8
        self.gdc_pending_today = []
        for i in range(8):
            f = self.gdc_farmers[i % 20]
            d = make_delivery_batch(
                self.gdc, f, f"PRODUCE-{today_d:%Y%m%d}-{i+1:03d}",
                ProductType.MILK, Decimal(str(round(12.0 + i * 2.0, 2))),
                DeliveryStatus.PENDING, Shift.AM, base, None, f.latitude, f.longitude,
            )
            deliveries.append(d)
            self.gdc_pending_today.append(d)

        # NCC 3 months: 210 graded
        for i in range(210):
            f = self.ncc_farmers[i % 20]
            deliveries.append(make_delivery_batch(
                self.ncc, f, f"PRODUCE-{m1.date():%Y%m%d}-{i+501:03d}",
                ProductType.COFFEE_CHERRIES, Decimal(str(round(50.0 + (i % 30) * 5.0, 2))),
                DeliveryStatus.GRADED, Shift.AM if i % 10 < 6 else Shift.PM,
                m1 + timedelta(days=i % 30), self.ncc_manager, f.latitude, f.longitude,
            ))

        # Bulk create all at once
        created = Delivery.objects.bulk_create(deliveries, batch_size=100)
        self.gdc_deliveries = created[:180 + 210 + 77 + 8]
        self.ncc_deliveries = created[180 + 210 + 77 + 8:]
        self.stdout.write(f"  {len(self.gdc_deliveries)} GDC + {len(self.ncc_deliveries)} NCC deliveries")

    # -------------------------------------------------------------------------
    # Grades + Inventory + Stock (bulk create, then update Delivery.grade)
    # -------------------------------------------------------------------------
    def _seed_grades_and_inventory(self):
        price_map = {
            g.grade_letter: g.price_per_unit
            for g in GradePrice.objects.all()
        }

        # GDC graded deliveries
        gdc_graded = [d for d in self.gdc_deliveries if d.status == DeliveryStatus.GRADED]
        ncc_graded = [d for d in self.ncc_deliveries if d.status == DeliveryStatus.GRADED]

        grades = []
        grade_map = {}  # delivery_id -> grade

        # GDC grades
        for i, d in enumerate(gdc_graded):
            if i % 20 == 0:
                gl, reason = "", "Fat content below minimum threshold"
                price = Decimal("0")
            else:
                gl = GradeLetter.A if i % 5 == 0 else GradeLetter.B if i % 3 == 0 else GradeLetter.C
                reason, price = "", price_map.get(gl, Decimal("45.00"))
            g = Grade(
                delivery=d, cooperative=self.gdc, grade_letter=gl,
                price_per_unit=price, rejection_reason=reason,
                is_inventory_updated=True,
            )
            grades.append(g)
            grade_map[d.id] = g

        # NCC grades
        for i, d in enumerate(ncc_graded):
            if i % 20 == 0:
                gl, reason = "", "Cherry floaters"
                price = Decimal("0")
            else:
                gl = GradeLetter.A if i % 5 == 0 else GradeLetter.B if i % 3 == 0 else GradeLetter.C
                reason, price = "", price_map.get(gl, Decimal("80.00"))
            g = Grade(
                delivery=d, cooperative=self.ncc, grade_letter=gl,
                price_per_unit=price, rejection_reason=reason,
                is_inventory_updated=True,
            )
            grades.append(g)
            grade_map[d.id] = g

        created_grades = Grade.objects.bulk_create(grades, batch_size=100)
        self.gdc_grades = created_grades[:len(gdc_graded)]
        self.ncc_grades = created_grades[len(gdc_graded):]

        # Update delivery.grade FK (bulk update by grade letter)
        for gl in set(g.grade_letter for g in created_grades if g.grade_letter):
            ids = [g.delivery_id for g in created_grades if g.grade_letter == gl]
            Delivery.objects.filter(id__in=ids).update(grade=gl)

        # Inventory pools (one per cooperative/product/grade, no payment_cycle FK yet)
        inv_accum = defaultdict(lambda: {"qty": Decimal("0"), "unit": "", "first_id": None})
        stock_accum = defaultdict(lambda: Decimal("0"))
        stock_units = {}

        for g in created_grades:
            if not g.grade_letter:
                continue
            d = g.delivery
            unit = "litres" if d.product_type == ProductType.MILK else "kg"
            qty = d.volume_litres if d.product_type == ProductType.MILK else d.quantity_kg
            key = (g.cooperative_id, d.product_type, g.grade_letter)
            if inv_accum[key]["first_id"] is None:
                inv_accum[key]["first_id"] = d.id
            inv_accum[key]["qty"] += qty or Decimal("0")
            inv_accum[key]["unit"] = unit
            stock_accum[key] += qty or Decimal("0")
            stock_units[key] = unit

        inv_records = []
        for (coop_id, product, grade), data in inv_accum.items():
            inv_records.append(Inventory(
                cooperative_id=coop_id,
                batch_id=f"CYC-{str(data['first_id'])[:8]}-{product}-{grade}",
                product_type=product, grade=grade,
                unit=data["unit"], quantity_in=data["qty"],
                quantity_out=Decimal("0"), is_sold=False,
            ))
        Inventory.objects.bulk_create(inv_records, batch_size=100, ignore_conflicts=True)

        # Stock
        stock_objs = []
        for (coop_id, product, grade), qty in stock_accum.items():
            stock_objs.append(Stock(
                cooperative_id=coop_id, product_type=product, grade=grade,
                unit=stock_units[(coop_id, product, grade)],
                quantity_available=qty,
            ))
        Stock.objects.bulk_create(stock_objs, batch_size=100, ignore_conflicts=True)

        # 2 disputes
        if len(self.gdc_grades) >= 20:
            FarmerGradeDispute.objects.create(
                grade=self.gdc_grades[10], raised_by=self.gdc_grader,
                reason="Quality grade does not match delivery", status=DisputeStatus.PENDING,
            )
            FarmerGradeDispute.objects.create(
                grade=self.gdc_grades[20], raised_by=self.gdc_grader,
                reason="Fat content assessment appears incorrect", status=DisputeStatus.PENDING,
            )

        self.stdout.write(f"  {len(self.gdc_grades)} GDC + {len(self.ncc_grades)} NCC grades")

    # -------------------------------------------------------------------------
    # Buyers
    # -------------------------------------------------------------------------
    def _seed_buyers(self):
        self.gdc_buyers = [
            Buyer.objects.create(cooperative=self.gdc, name="KCC (Kenya Cooperative Creameries)",
                contact_person="John Mwenda", phone_number="0722000001",
                email="kcc@kenyacoop.co.ke", kra_pin="P051234501Z", is_active=True),
            Buyer.objects.create(cooperative=self.gdc, name="Brookside Dairy Ltd",
                contact_person="Sarah Kamau", phone_number="0722000002",
                email="brookside@dairy.co.ke", kra_pin="P051234502Z", is_active=True),
            Buyer.objects.create(cooperative=self.gdc, name="Githunguri Fresh Markets",
                contact_person="David Njoroge", phone_number="0722000003",
                email="markets@githunguri.co.ke", is_active=True),
        ]
        self.ncc_buyers = [
            Buyer.objects.create(cooperative=self.ncc, name="Kagumoini Coffee Factory",
                contact_person="James Wachira", phone_number="0723000001",
                email="kagumoini@coffee.coke", kra_pin="P059876501Z", is_active=True),
            Buyer.objects.create(cooperative=self.ncc, name="Nyeri Coffee Brokers",
                contact_person="Ann Wambui", phone_number="0723000002",
                email="brokers@nyeri.co.ke", is_active=True),
        ]

    # -------------------------------------------------------------------------
    # Sales + Inventory Decrement
    # -------------------------------------------------------------------------
    def _seed_sales_and_inventory(self):
        today_d = date.today()
        two_mo = today_d - timedelta(days=60)
        one_mo = today_d - timedelta(days=30)

        def make_sale(coop, buyer, grades_list, start, qty, price, unit, sale_date, status, inv_num):
            g_obj = grades_list[start]
            d = g_obj.delivery
            grade = g_obj.grade_letter
            product = d.product_type
            stock = Stock.objects.get(cooperative=coop, product_type=product, grade=grade)
            sale = Sale(
                cooperative=coop, buyer=buyer, stock=stock,
                recorded_by=self.gdc_manager if coop == self.gdc else self.ncc_manager,
                product_type=product, grade_letter=grade, unit=unit,
                quantity=Decimal(str(qty)), price_per_unit=Decimal(str(price)),
                total_amount=Decimal(str(qty)) * Decimal(str(price)),
                status=status, sale_date=sale_date,
                invoice_number=inv_num,
                inventory_updated=(status == SaleStatus.COMPLETED),
            )
            return sale, stock, d, grade, product, qty

        sale_objs = []
        stock_updates = []

        # GDC 4 sales
        gdc_g = [g for g in self.gdc_grades if g.grade_letter]
        for grade in gdc_g:
            pass

        s1, st1, d1, g1, p1, q1 = make_sale(self.gdc, self.gdc_buyers[0], gdc_g, 0, 2500, 62, SaleUnit.LITRES, two_mo, SaleStatus.COMPLETED, "INV-GDC-2026-001")
        s2, st2, d2, g2, p2, q2 = make_sale(self.gdc, self.gdc_buyers[1], gdc_g, 5, 1800, 52, SaleUnit.LITRES, two_mo, SaleStatus.COMPLETED, "INV-GDC-2026-002")
        s3, st3, d3, g3, p3, q3 = make_sale(self.gdc, self.gdc_buyers[0], gdc_g, 10, 3200, 63, SaleUnit.LITRES, one_mo, SaleStatus.COMPLETED, "INV-GDC-2026-003")
        s4, st4, d4, g4, p4, q4 = make_sale(self.gdc, self.gdc_buyers[2], gdc_g, 15, 800, 60, SaleUnit.LITRES, today_d, SaleStatus.PENDING, "INV-GDC-2026-004")
        sale_objs.extend([s1, s2, s3, s4])
        for st, q in [(st1,q1),(st2,q2),(st3,q3)]:
            st.quantity_available = max(st.quantity_available - Decimal(str(q)), Decimal("0"))
            stock_updates.append(st)

        # NCC 2 sales
        ncc_g = [g for g in self.ncc_grades if g.grade_letter]
        sn1, stn1, dn1, gn1, pn1, qn1 = make_sale(self.ncc, self.ncc_buyers[0], ncc_g, 0, 500, 92, SaleUnit.KG, two_mo, SaleStatus.COMPLETED, "INV-NCC-2026-001")
        sn2, stn2, dn2, gn2, pn2, qn2 = make_sale(self.ncc, self.ncc_buyers[1], ncc_g, 8, 350, 75, SaleUnit.KG, one_mo, SaleStatus.COMPLETED, "INV-NCC-2026-002")
        sale_objs.extend([sn1, sn2])
        for st, q in [(stn1,qn1),(stn2,qn2)]:
            st.quantity_available = max(st.quantity_available - Decimal(str(q)), Decimal("0"))
            stock_updates.append(st)

        created_sales = Sale.objects.bulk_create(sale_objs, batch_size=10)

        # SaleInventoryLineItems + inventory decrement
        line_items = []
        for sale in [s1, s2, s3, sn1, sn2]:
            pools = Inventory.objects.filter(
                cooperative=sale.cooperative, product_type=sale.product_type,
                grade=sale.grade_letter,
            ).order_by("created_at")
            remaining = sale.quantity
            for pool in pools:
                if remaining <= 0:
                    break
                avail = (pool.quantity_in or Decimal("0")) - (pool.quantity_out or Decimal("0"))
                if avail <= 0:
                    continue
                take = min(avail, remaining)
                pool.quantity_out = (pool.quantity_out or Decimal("0")) + take
                remaining -= take
                line_items.append(SaleInventoryLineItem(sale=sale, inventory=pool, quantity=take))
            sale.payment_cycle_id = self._cycle_for_date(sale.cooperative_id, sale.sale_date)

        SaleInventoryLineItem.objects.bulk_create(line_items, batch_size=50)
        Inventory.objects.bulk_update(
            Inventory.objects.filter(id__in=[li.inventory_id for li in line_items]),
            ["quantity_out"], batch_size=100,
        )
        Stock.objects.bulk_update(stock_updates, ["quantity_available"], batch_size=100)

        self.gdc_sales = [s1, s2, s3, s4]
        self.ncc_sales = [sn1, sn2]
        self.stdout.write(f"  {len(self.gdc_sales)} GDC + {len(self.ncc_sales)} NCC sales")

    def _cycle_for_date(self, coop_id, sale_date):
        return None  # will update after cycles are created

    # -------------------------------------------------------------------------
    # Payment Cycles
    # -------------------------------------------------------------------------
    def _seed_payment_cycles(self):
        today_d = date.today()
        self.gdc_cycle1 = PaymentCycle.objects.create(
            cooperative=self.gdc, name="March 2026 Payment Cycle",
            start_date=(today_d - timedelta(days=90)).replace(day=1),
            end_date=(today_d - timedelta(days=90)).replace(day=28),
            status=CycleStatus.DISBURSED,
            totals={"total_quantity": 0, "total_gross": 0, "total_net": 0, "farmer_count": 20},
        )
        self.gdc_cycle2 = PaymentCycle.objects.create(
            cooperative=self.gdc, name="April 2026 Payment Cycle",
            start_date=(today_d - timedelta(days=60)).replace(day=1),
            end_date=(today_d - timedelta(days=60)).replace(day=28),
            status=CycleStatus.DISBURSED,
            totals={"total_quantity": 0, "total_gross": 0, "total_net": 0, "farmer_count": 20},
        )
        self.gdc_cycle3 = PaymentCycle.objects.create(
            cooperative=self.gdc, name="May 2026 Payment Cycle",
            start_date=(today_d - timedelta(days=30)).replace(day=1),
            end_date=today_d,
            status=CycleStatus.LOCKED,
            totals={"total_quantity": 0, "total_gross": 0, "total_net": 0, "farmer_count": 20},
            locked_by=self.gdc_manager, locked_at=timezone.now() - timedelta(days=3),
        )
        self.ncc_cycle1 = PaymentCycle.objects.create(
            cooperative=self.ncc, name="March 2026 Payment Cycle",
            start_date=(today_d - timedelta(days=90)).replace(day=1),
            end_date=(today_d - timedelta(days=90)).replace(day=28),
            status=CycleStatus.DISBURSED,
            totals={"total_quantity": 0, "total_gross": 0, "total_net": 0, "farmer_count": 20},
        )
        self.ncc_cycle2 = PaymentCycle.objects.create(
            cooperative=self.ncc, name="April 2026 Payment Cycle",
            start_date=(today_d - timedelta(days=60)).replace(day=1),
            end_date=(today_d - timedelta(days=60)).replace(day=28),
            status=CycleStatus.DISBURSED,
            totals={"total_quantity": 0, "total_gross": 0, "total_net": 0, "farmer_count": 20},
        )
        self.ncc_cycle3 = PaymentCycle.objects.create(
            cooperative=self.ncc, name="May 2026 Payment Cycle",
            start_date=(today_d - timedelta(days=30)).replace(day=1),
            end_date=today_d, status=CycleStatus.DRAFT,
        )

        # Update completed sales with payment cycles
        Sale.objects.filter(id__in=[s.id for s in self.gdc_sales[:3]]).update(payment_cycle=self.gdc_cycle1)
        Sale.objects.filter(id__in=[s.id for s in self.ncc_sales[:1]]).update(payment_cycle=self.ncc_cycle1)
        Sale.objects.filter(id=self.ncc_sales[1].id).update(payment_cycle=self.ncc_cycle2)

        # Update inventory pools with cycle
        Inventory.objects.filter(cooperative=self.gdc).update(payment_cycle=self.gdc_cycle1)
        Inventory.objects.filter(cooperative=self.ncc).update(payment_cycle=self.ncc_cycle1)

    # -------------------------------------------------------------------------
    # Farmer Payments
    # -------------------------------------------------------------------------
    def _seed_farmer_payments(self):
        def wht_amount(farmer_id, cycle, net):
            fy_start = date(cycle.start_date.year, 7, 1)
            if cycle.start_date < fy_start:
                fy_start = date(cycle.start_date.year - 1, 7, 1)
            cumulative = FarmerPayment.objects.filter(
                farmer_id=farmer_id, cycle__status=CycleStatus.DISBURSED,
                cycle__end_date__gte=fy_start, cycle__end_date__lte=cycle.end_date,
            ).exclude(cycle=cycle).aggregate(t=Sum("net_amount"))["t"] or Decimal("0")
            cumulative = float(cumulative)
            net_f = float(net)
            thr = 24000.0
            if cumulative < thr:
                above = max((cumulative + net_f) - thr, 0)
                return (Decimal(str(min(above, net_f))) * Decimal("0.05")).quantize(Decimal("0.01")), above > 0
            return (Decimal(str(net_f)) * Decimal("0.05")).quantize(Decimal("0.01")), True

        def seed_for_cycle(cycle, farmers, coop):
            fps = []
            tot_gross = Decimal("0")
            tot_net = Decimal("0")
            tot_levy = Decimal("0")
            tot_fee = Decimal("0")
            n = len(farmers)
            monthly_fee_share = coop.monthly_fee / Decimal(str(n)) if n else Decimal("0")

            for farmer in farmers:
                base_gross = Decimal(str(round(5000 + hash(str(farmer.id)) % 5000, 2)))
                levy = base_gross * coop.levy_percentage / Decimal("100")
                net = base_gross - levy - monthly_fee_share
                wht, wht_flag = wht_amount(farmer.id, cycle, net)
                net -= wht
                wht = Decimal(str(wht))

                gb = {"A": {"kg": 100.0, "amount": float(base_gross)}}

                fp = FarmerPayment(
                    cooperative=coop, cycle=cycle, farmer=farmer,
                    total_quantity=Decimal("100.00"), grade_breakdown=gb,
                    gross_amount=base_gross,
                    deductions={
                        "levy": str(levy.quantize(Decimal("0.01"))),
                        "monthly_fee": str(monthly_fee_share.quantize(Decimal("0.01"))),
                        "loan_repayment": "0.00", "input_credit": "0.00",
                    },
                    net_amount=net.quantize(Decimal("0.01")),
                    payment_status=PaymentStatus.PAID if cycle.status == CycleStatus.DISBURSED else PaymentStatus.PENDING,
                    withholding_tax_amount=wht, is_subject_to_withholding_tax=wht_flag,
                    computation_log={
                        "method": "FIXED_PRICE", "total_quantity": 100.0,
                        "gross_amount": float(base_gross),
                        "deductions_applied": {
                            "levy": float(levy.quantize(Decimal("0.01"))),
                            "monthly_fee": float(monthly_fee_share.quantize(Decimal("0.01"))),
                            "loan_repayment": 0.0, "input_credit": 0.0,
                        },
                        "net_amount": float(net.quantize(Decimal("0.01"))),
                        "withholding_tax": float(wht),
                    },
                )
                fps.append(fp)
                tot_gross += base_gross
                tot_net += net
                tot_levy += levy
                tot_fee += monthly_fee_share

            FarmerPayment.objects.bulk_create(fps, batch_size=50)
            totals = FarmerPayment.objects.filter(cycle=cycle).aggregate(
                tg=Sum("gross_amount"), tn=Sum("net_amount"), tq=Sum("total_quantity"),
            )
            cycle.totals = {
                "total_quantity": float(totals["tq"] or 0),
                "total_gross": float(totals["tg"] or 0),
                "total_net": float(totals["tn"] or 0),
                "farmer_count": n,
            }
            cycle.total_levy = tot_levy.quantize(Decimal("0.01"))
            cycle.total_cooperative_fee = tot_fee.quantize(Decimal("0.01"))
            cycle.save(update_fields=["totals", "total_levy", "total_cooperative_fee"])
            return fps

        self.gdc_fp1 = seed_for_cycle(self.gdc_cycle1, self.gdc_farmers, self.gdc)
        self.gdc_fp2 = seed_for_cycle(self.gdc_cycle2, self.gdc_farmers, self.gdc)
        self.gdc_fp3 = seed_for_cycle(self.gdc_cycle3, self.gdc_farmers, self.gdc)
        self.ncc_fp1 = seed_for_cycle(self.ncc_cycle1, self.ncc_farmers, self.ncc)
        self.ncc_fp2 = seed_for_cycle(self.ncc_cycle2, self.ncc_farmers, self.ncc)

    # -------------------------------------------------------------------------
    # Deductions
    # -------------------------------------------------------------------------
    def _seed_deductions(self):
        levy_deds = []
        for cycle, fps in [
            (self.gdc_cycle1, self.gdc_fp1), (self.gdc_cycle2, self.gdc_fp2),
            (self.ncc_cycle1, self.ncc_fp1), (self.ncc_cycle2, self.ncc_fp2),
        ]:
            for fp in fps:
                levy_amt = Decimal(fp.deductions.get("levy", "0"))
                if levy_amt > 0:
                    levy_deds.append(Deduction(
                        cooperative=cycle.cooperative, farmer=fp.farmer, cycle=cycle,
                        deduction_type="LEVY", amount=levy_amt,
                        notes="Auto-generated levy deduction",
                    ))
        Deduction.objects.bulk_create(levy_deds, batch_size=50)

    # -------------------------------------------------------------------------
    # Loans
    # -------------------------------------------------------------------------
    def _seed_loans(self):
        self.loan_active = Loan.objects.create(
            cooperative=self.gdc, farmer=self.gdc_farmers[1],
            amount_principal=Decimal("30000.00"), interest_rate=Decimal("5.00"),
            number_of_installments=6, status=LoanStatus.ACTIVE,
            disbursed_at=timezone.now() - timedelta(days=60),
            approved_by=self.gdc_manager, notes="Dairy cattle feed inputs",
        )
        LoanGuarantor.objects.create(
            loan=self.loan_active, guarantor=self.gdc_farmers[2], status=GuarantorStatus.ACTIVE,
            cooperative=self.gdc,
        )
        self.loan_completed = Loan.objects.create(
            cooperative=self.gdc, farmer=self.gdc_farmers[4],
            amount_principal=Decimal("15000.00"), interest_rate=Decimal("5.00"),
            number_of_installments=6, status=LoanStatus.COMPLETED,
            disbursed_at=timezone.now() - timedelta(days=180),
            approved_by=self.gdc_manager, installments_paid=6, notes="Fence repair",
        )
        LoanGuarantor.objects.create(
            loan=self.loan_completed, guarantor=self.gdc_farmers[5], status=GuarantorStatus.RELEASED,
            cooperative=self.gdc,
        )

    # -------------------------------------------------------------------------
    # Disbursements
    # -------------------------------------------------------------------------
    def _seed_disbursements(self):
        def make_batch(coop, cycle, fps, status, approver=None):
            if status == BatchStatus.PENDING:
                return DisbursementBatch.objects.create(
                    cooperative=coop, payment_cycle=cycle, status=status,
                    command_id=CommandId.SALARY_PAYMENT,
                    total_amount=sum(fp.net_amount for fp in fps),
                    total_transactions=len(fps),
                    notes="Pending manager approval",
                )
            batch = DisbursementBatch.objects.create(
                cooperative=coop, payment_cycle=cycle, status=status,
                command_id=CommandId.SALARY_PAYMENT,
                total_amount=sum(fp.net_amount for fp in fps),
                total_transactions=len(fps), successful_count=len(fps),
                approved_by=approver, approved_at=timezone.now() - timedelta(days=1),
                notes="Demo seed batch",
            )
            txns = []
            for fp in fps:
                mem = fp.farmer.primary_membership
                if mem.payment_method == FarmerPaymentMethod.M_PESA:
                    pmeth = DisbursementPaymentMethod.M_PESA
                    recip = mem.mpesa_number or fp.farmer.phone_number
                elif mem.payment_method == FarmerPaymentMethod.BANK:
                    pmeth = DisbursementPaymentMethod.BANK
                    recip = mem.bank_account or ""
                else:
                    pmeth = DisbursementPaymentMethod.CASH
                    recip = ""
                conv = str(uuid.uuid4())
                txns.append(DisbursementTransaction(
                    cooperative=coop, batch=batch, farmer=fp.farmer, farmer_payment=fp,
                    amount=fp.net_amount, payment_method=pmeth,
                    recipient_identifier=recip,
                    recipient_name=f"{fp.farmer.first_name} {fp.farmer.last_name}",
                    status=TransactionStatus.SUCCESS,
                    conversation_id=conv, transaction_id=conv[:16],
                    originator_conversation_id=conv,
                    result_code="0", result_desc="Success",
                    sent_at=timezone.now() - timedelta(days=1),
                    completed_at=timezone.now() - timedelta(days=1),
                    withholding_tax_amount=fp.withholding_tax_amount,
                    created_by=approver,
                ))
            DisbursementTransaction.objects.bulk_create(txns, batch_size=50)
            DisbursementTransaction.objects.bulk_update(txns, ["batch"], batch_size=50)
            return batch

        self.gdc_batch1 = make_batch(self.gdc, self.gdc_cycle1, self.gdc_fp1, BatchStatus.COMPLETED, self.gdc_manager)
        self.gdc_batch2 = make_batch(self.gdc, self.gdc_cycle2, self.gdc_fp2, BatchStatus.COMPLETED, self.gdc_manager)
        self.gdc_batch3 = make_batch(self.gdc, self.gdc_cycle3, self.gdc_fp3, BatchStatus.PENDING)
        self.ncc_batch1 = make_batch(self.ncc, self.ncc_cycle1, self.ncc_fp1, BatchStatus.COMPLETED, self.ncc_manager)
        self.ncc_batch2 = make_batch(self.ncc, self.ncc_cycle2, self.ncc_fp2, BatchStatus.COMPLETED, self.ncc_manager)

    # -------------------------------------------------------------------------
    # Routes
    # -------------------------------------------------------------------------
    def _seed_routes(self):
        r1 = CollectionRoute.objects.create(
            cooperative=self.gdc, name="Githunguri Morning Route",
            description="Morning milk collection", day_of_week=DayOfWeekChoices.MONDAY,
            is_active=True, path={"waypoints": [[36.83, -1.17], [36.85, -1.15]]},
            estimated_distance_km=Decimal("12.50"),
        )
        RouteStop.objects.create(route=r1, stop_order=1, latitude=Decimal("-1.170000"),
            longitude=Decimal("36.830000"), estimated_minutes=30)
        RouteStop.objects.create(route=r1, stop_order=2, latitude=Decimal("-1.150000"),
            longitude=Decimal("36.840000"), estimated_minutes=25)
        r2 = CollectionRoute.objects.create(
            cooperative=self.gdc, name="Kamiti Evening Route",
            description="Evening milk collection", day_of_week=DayOfWeekChoices.TUESDAY,
            is_active=True, path={"waypoints": [[36.83, -1.18], [36.84, -1.16]]},
            estimated_distance_km=Decimal("8.00"),
        )
        RouteStop.objects.create(route=r2, stop_order=1, latitude=Decimal("-1.180000"),
            longitude=Decimal("36.830000"), estimated_minutes=35)
        RouteStop.objects.create(route=r2, stop_order=2, latitude=Decimal("-1.160000"),
            longitude=Decimal("36.840000"), estimated_minutes=30)

    # -------------------------------------------------------------------------
    # Notifications
    # -------------------------------------------------------------------------
    def _seed_notifications(self):
        sent = timezone.now() - timedelta(hours=2)
        for farmer in self.gdc_farmers[:10]:
            Notification.objects.create(
                cooperative=self.gdc, recipient=farmer, channel=NotificationChannel.SMS,
                notification_type=NotificationType.DELIVERY_CONFIRMATION,
                content=f"Dear {farmer.first_name}, your delivery has been recorded.",
                status=NotificationStatus.SENT, sent_at=sent,
            )
        Notification.objects.create(
            cooperative=self.gdc, recipient=self.gdc_farmers[0],
            channel=NotificationChannel.SMS, notification_type=NotificationType.PAYMENT_SENT,
            content=f"Dear James Kamau, KES 12,500 has been sent to your M-Pesa.",
            status=NotificationStatus.SENT, sent_at=sent - timedelta(days=30),
        )
        Notification.objects.create(
            cooperative=self.gdc, recipient=self.gdc_farmers[1],
            channel=NotificationChannel.SMS, notification_type=NotificationType.PAYMENT_SENT,
            content=f"Dear Grace Wanjiku, KES 11,200 has been sent to your M-Pesa.",
            status=NotificationStatus.SENT, sent_at=sent - timedelta(days=30),
        )
        Notification.objects.create(
            cooperative=self.gdc, recipient=self.gdc_farmers[0],
            channel=NotificationChannel.SMS, notification_type=NotificationType.GRADE_RESULT,
            content="Your delivery GRADE-A has been recorded.",
            status=NotificationStatus.SENT, sent_at=sent - timedelta(days=2),
        )
        Notification.objects.create(
            cooperative=self.gdc, recipient=self.gdc_farmers[0],
            channel=NotificationChannel.SMS, notification_type=NotificationType.LOAN_DISBURSEMENT,
            content="Your loan of KES 30,000 has been disbursed.",
            status=NotificationStatus.SENT, sent_at=sent - timedelta(days=60),
        )
        for farmer in self.ncc_farmers[:5]:
            Notification.objects.create(
                cooperative=self.ncc, recipient=farmer, channel=NotificationChannel.SMS,
                notification_type=NotificationType.DELIVERY_CONFIRMATION,
                content=f"Dear {farmer.first_name}, your coffee delivery has been recorded.",
                status=NotificationStatus.SENT, sent_at=sent,
            )

    # -------------------------------------------------------------------------
    # Audit Logs
    # -------------------------------------------------------------------------
    def _seed_audit_logs(self):
        from apps.base.models import AuditAction
        log_audit(actor=self.gdc_manager, resource_type="PaymentCycle",
            resource_id=self.gdc_cycle1.id, action=AuditAction.LOCK,
            cooperative_id=self.gdc.id, new_value={"status": "LOCKED"})
        if hasattr(self, 'gdc_batch1') and self.gdc_batch1:
            log_audit(actor=self.gdc_manager, resource_type="DisbursementBatch",
                resource_id=self.gdc_batch1.id, action=AuditAction.DISBURSE,
                cooperative_id=self.gdc.id,
                new_value={"status": "COMPLETED", "amount": str(self.gdc_batch1.total_amount)})
        if self.gdc_grades and len(self.gdc_grades) > 5:
            log_audit(actor=self.gdc_grader, resource_type="Grade",
                resource_id=self.gdc_grades[5].id, action=AuditAction.GRADE,
                cooperative_id=self.gdc.id, new_value={"grade_letter": "A"})
        if hasattr(self, 'loan_active') and self.loan_active:
            log_audit(actor=self.gdc_manager, resource_type="Loan",
                resource_id=self.loan_active.id, action=AuditAction.CREATE,
                cooperative_id=self.gdc.id,
                new_value={"amount": "30000.00", "purpose": "Dairy cattle feed inputs"})

    # -------------------------------------------------------------------------
    # Analytics Snapshots
    # -------------------------------------------------------------------------
    def _seed_analytics_snapshots(self):
        from apps.analytics.queries.cooperative import get_dashboard
        today_d = date.today()
        for coop in [self.gdc, self.ncc]:
            for months_ago in [2, 1, 0]:
                start = (today_d - timedelta(days=30 * months_ago)).replace(day=1)
                end = today_d if months_ago == 0 else (start - timedelta(days=1)).replace(day=28)
                data = get_dashboard(str(coop.id), start, end)
                AnalyticsSnapshot.objects.update_or_create(
                    cooperative=coop, period_type=PeriodType.MONTHLY, period_start=start,
                    defaults={
                        "period_end": end,
                        "data": {"period": {"start": start.isoformat(), "end": end.isoformat()}, "data": data},
                        "schema_version": 1,
                    },
                )
            MaterializedAnalytics.objects.update_or_create(
                period_type=PeriodType.MONTHLY, period_start=today_d.replace(day=1),
                defaults={"period_end": today_d, "data": {"note": "seeded"}, "schema_version": 1},
            )

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    def _print_summary(self):
        self.stdout.write(self.style.SUCCESS("\n=== Zao Presentation Data Summary ==="))
        self.stdout.write(f"Superadmin:          1  (authpass8@gmail.com / Admin@Zao2026)")
        self.stdout.write(f"Cooperatives:        2  (GDC + NCC)")
        self.stdout.write(f"Staff users:         6")
        self.stdout.write(f"  Manager:       isaacndungu478@gmail.com / Manager@2026")
        self.stdout.write(f"  Accountant:    isaacn2101@gmail.com / Account@2026")
        self.stdout.write(f"  Grader:       davision.2024@gmail.com / Grader@2026")
        self.stdout.write(f"Farmers:            40  (20 GDC + 20 NCC)")
        self.stdout.write(f"  Demo farmer:   {self.gdc_demo_farmer} @ 0716227503 (OTP via SMS)")
        self.stdout.write(f"Deliveries:         475  (467 GDC + 8 NCC)")
        self.stdout.write(f"Grades:             ~467 GDC + NCC")
        self.stdout.write(f"Sales:              6  (5 COMPLETED + 1 PENDING)")
        self.stdout.write(f"Payment cycles:     6  (3 GDC + 3 NCC)")
        self.stdout.write(f"  GDC Cycle 1-2: DISBURSED, Cycle 3: LOCKED")
        self.stdout.write(f"  NCC Cycle 1-2: DISBURSED, Cycle 3: DRAFT")
        self.stdout.write(f"Loans:              2  (1 ACTIVE + 1 COMPLETED)")
        self.stdout.write(f"Disbursements:      5 batches")
        self.stdout.write(f"Legal docs:         2  (both accepted by all staff)")
        self.stdout.write(f"Routes:             2  (GDC)")
        self.stdout.write(f"Notifications:      20+")
        self.stdout.write(self.style.SUCCESS("Presentation data seeded successfully."))
