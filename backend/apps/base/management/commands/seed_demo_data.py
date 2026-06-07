import uuid
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.crypto import get_random_string
from django.utils import timezone

from apps.auth_api.models import User
from apps.base.constants import UserRole, KENYA_COUNTIES
from apps.base.utils import normalize_phone
from apps.cooperatives.models import Cooperative, ProduceType, PaymentModel
from apps.deliveries.models import Delivery, ProductType, DeliveryStatus, Shift
from apps.disbursement.models import (
    DisbursementBatch, DisbursementTransaction,
    BatchStatus, TransactionStatus, DisbursementPaymentMethod,
)
from apps.farmers.models import Farmer, FarmerPaymentMethod
from apps.grading.models import Grade, GradePrice, GradeLetter
from apps.inventory.models import Inventory
from apps.loans.models import Loan, LoanStatus, LoanGuarantor, GuarantorStatus
from apps.notifications.models import Notification, NotificationChannel, NotificationType, NotificationStatus
from apps.payment_engine.models import PaymentCycle, CycleStatus, FarmerPayment, PaymentStatus
from apps.sales.models import Sale, SaleStatus, Buyer, SaleUnit

COOP_DATA = [
    {
        "name": "Kirinyaga Dairy Farmers Co-op",
        "reg_no": "CSC/D/123/2020",
        "county": "Kirinyaga",
        "sub_county": "Mwea",
        "produce_type": ProduceType.DAIRY,
        "payment_model": PaymentModel.FIXED_PRICE,
        "levy_pct": Decimal("2.50"),
        "monthly_fee": Decimal("200.00"),
        "prefix": "KDF",
        "till_number": "654321",
        "kra_pin": "P051234567Z",
    },
    {
        "name": "Kiambu Coffee Growers Co-op",
        "reg_no": "CSC/D/456/2019",
        "county": "Kiambu",
        "sub_county": "Ruiru",
        "produce_type": ProduceType.COFFEE,
        "payment_model": PaymentModel.REVENUE_SHARE,
        "levy_pct": Decimal("3.00"),
        "monthly_fee": Decimal("250.00"),
        "prefix": "KCG",
        "till_number": "654322",
        "kra_pin": "P051234568Z",
    },
    {
        "name": "Mwingi Honey Producers Co-op",
        "reg_no": "CSC/D/789/2021",
        "county": "Kitui",
        "sub_county": "Mwingi",
        "produce_type": ProduceType.HONEY,
        "payment_model": PaymentModel.FIXED_PRICE,
        "levy_pct": Decimal("2.00"),
        "monthly_fee": Decimal("150.00"),
        "prefix": "MHP",
        "till_number": "654323",
        "kra_pin": "P051234569Z",
    },
]

COOP_COORDS = {
    "Kirinyaga": {"lat": -0.50, "lng": 37.30},
    "Kiambu":    {"lat": -1.17, "lng": 36.83},
    "Kitui":     {"lat": -1.37, "lng": 38.01},
}

FARMER_NAMES = [
    ("Grace", "Njoki"), ("Peter", "Kamau"), ("Mary", "Wanjiku"),
    ("John", "Mwangi"), ("Sarah", "Akinyi"), ("David", "Ochieng"),
    ("Alice", "Wambui"), ("James", "Njoroge"), ("Faith", "Chebet"),
    ("Samuel", "Kiprop"), ("Esther", "Nyambura"), ("Daniel", "Mutua"),
    ("Margaret", "Ndung'u"), ("Joseph", "Barasa"), ("Lydia", "Jepkosgei"),
    ("Simon", "Kiprono"), ("Rose", "Atieno"),
]

def create_user(email, first_name, last_name, role, cooperative, password="Password123!"):
    user = User.objects.create_user(
        email=email,
        phone_number=f"071{hash(email) % 10000000:07d}",
        first_name=first_name,
        last_name=last_name,
        password=password,
        role=role,
        cooperative=cooperative,
        is_active=True,
    )
    if role == UserRole.ADMIN:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    return user


class Command(BaseCommand):
    help = "Seed demo data: 3 coops, users, 51 farmers, deliveries, grades, sales, cycles, disbursements"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing seed data first")

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear_data()

        if self._has_data():
            self.stdout.write(self.style.WARNING("Seed data already exists. Use --clear to re-seed."))
            return

        with transaction.atomic():
            self._seed()

    def _has_data(self):
        return Cooperative.objects.count() >= 3

    def _clear_data(self):
        models = [
            DisbursementTransaction, DisbursementBatch, FarmerPayment, PaymentCycle,
            LoanGuarantor, Loan, Sale, Buyer, Grade, GradePrice, Inventory,
            Delivery, Farmer, Notification, User, Cooperative,
        ]
        for m in models:
            m.objects.all().delete()
        self.stdout.write("Cleared existing data.")

    def _seed(self):
        cooperatives = self._create_cooperatives()
        users = self._create_users(cooperatives)
        farmers = self._create_farmers(cooperatives)
        deliveries = self._create_deliveries(farmers, users)
        grade_prices = self._create_grade_prices()
        grades = self._create_grades(deliveries, users, cooperatives)
        inventory = self._create_inventory(grades)
        buyers = self._create_buyers(cooperatives)
        sales = self._create_sales(buyers, inventory, users, cooperatives)
        cycles = self._create_cycles(cooperatives, users, farmers)
        farmer_payments = self._create_farmer_payments(cycles, farmers)
        self._create_disbursements(cycles, farmers, farmer_payments, users)
        self._create_loans(farmers, farmer_payments, cooperatives)
        self._create_notifications(farmers, cooperatives)
        self._print_summary(cooperatives, users, farmers, deliveries, grades, inventory, buyers, sales, cycles, farmer_payments)

    def _create_cooperatives(self):
        coops = []
        for cd in COOP_DATA:
            coop = Cooperative.objects.create(
                name=cd["name"],
                registration_number=cd["reg_no"],
                county=cd["county"],
                sub_county=cd["sub_county"],
                produce_type=cd["produce_type"],
                payment_model=cd["payment_model"],
                levy_percentage=cd["levy_pct"],
                monthly_fee=cd["monthly_fee"],
                prefix=cd["prefix"],
                till_number=cd["till_number"],
                kra_pin=cd["kra_pin"],
                mpesa_shortcode=cd["till_number"],
                is_active=True,
                is_verified=True,
                last_member_sequence=0,
                year_established=2020,
                member_count=17,
                phone_number=f"071{hash(cd['name']) % 10000000:07d}",
                email=f"info@{cd['prefix'].lower()}.coop",
                physical_address=f"{cd['sub_county']}, {cd['county']} County",
            )
            coops.append(coop)
        self.stdout.write(f"Created {len(coops)} cooperatives")
        return coops

    def _create_users(self, cooperatives):
        users = []
        all_roles = [
            (UserRole.ADMIN, "System", "Admin", None),
        ]
        for coop in cooperatives:
            prefix = coop.prefix.lower()
            all_roles.extend([
                (UserRole.MANAGER, f"{prefix}_manager", "Manager", coop),
                (UserRole.ACCOUNTANT, f"{prefix}_accountant", "Accountant", coop),
                (UserRole.GRADER, f"{prefix}_grader", "Grader", coop),
                (UserRole.FARMER, f"{prefix}_farmer", "Farmer", coop),
            ])
        for role, first, last, coop in all_roles:
            email = f"{first}.{last}@zao.app".lower().replace(" ", "_")
            user = create_user(email, first.title(), last.title(), role, coop)
            users.append(user)
        self.stdout.write(f"Created {len(users)} users")
        return users

    def _create_farmers(self, cooperatives):
        farmers = []
        for coop in cooperatives:
            for i in range(17):
                first, last = FARMER_NAMES[i % len(FARMER_NAMES)]
                coords = COOP_COORDS.get(coop.county, {"lat": 0.0, "lng": 37.0})
                raw_phone = f"07{i+1:02d}{hash(str(coop.id)) % 1000000:06d}"
                phone = normalize_phone(raw_phone)
                farmer = Farmer.objects.create(
                    cooperative=coop,
                    first_name=first,
                    last_name=last,
                    id_number=f"{hash((str(coop.id), str(i))) % 10000000:08d}",
                    phone_number=phone,
                    county=coop.county,
                    sub_county=coop.sub_county,
                    latitude=Decimal(str(round(coords["lat"] + (i % 5) * 0.02, 6))),
                    longitude=Decimal(str(round(coords["lng"] + (i % 4) * 0.025, 6))),
                    is_active=True,
                )
                # Update the auto-created membership with payment details
                membership = farmer.memberships.filter(cooperative=coop).first()
                if membership:
                    membership.payment_method = FarmerPaymentMethod.M_PESA if i % 3 else FarmerPaymentMethod.BANK
                    membership.mpesa_number = phone
                    if i % 3 == 0:
                        membership.bank_name = "Equity Bank"
                        membership.bank_account = f"123456789{i:02d}"
                    membership.save(update_fields=['payment_method', 'mpesa_number', 'bank_name', 'bank_account'])
                farmers.append(farmer)
                # Create linked User for farmer login
                email = farmer.email or f'farmer_{farmer.id}@placeholder.local'
                user = User.objects.create_user(
                    email=email,
                    phone_number=farmer.phone_number,
                    first_name=farmer.first_name,
                    last_name=farmer.last_name,
                    password=get_random_string(length=72),
                    role=UserRole.FARMER,
                    cooperative_id=coop.id,
                )
                user.set_unusable_password()
                user.save(update_fields=['password'])
                farmer.user = user
                farmer.save(update_fields=['user'])
        self.stdout.write(f"Created {len(farmers)} farmers")
        return farmers

    def _create_deliveries(self, farmers, users):
        deliveries = []
        graders = [u for u in users if u.role == UserRole.GRADER]
        base_date = timezone.now().replace(hour=6, minute=0, second=0, microsecond=0)
        today = timezone.localdate()
        for i, farmer in enumerate(farmers):
            for d in range(2):
                day_offset = (i * 2 + d) % 30
                is_graded = d == 0
                status = DeliveryStatus.GRADED if is_graded else DeliveryStatus.PENDING
                vol = Decimal(str(round(15.0 + (i % 20) * 1.5, 2)))
                seq = i * 2 + d + 1
                batch_id = f"PRODUCE-{today:%Y%m%d}-{seq:03d}"
                dlng = float(farmer.longitude) + (0.01 if d == 1 else -0.01)
                dlat = float(farmer.latitude) + (0.005 if i % 2 == 0 else -0.005)
                delivery = Delivery.objects.create(
                    farmer=farmer,
                    cooperative=farmer.cooperative,
                    batch_id=batch_id,
                    product_type=ProductType.MILK,
                    volume_litres=vol,
                    status=status,
                    shift=Shift.AM if d == 0 else Shift.PM,
                    date_delivered=base_date - timedelta(days=day_offset),
                    grader=graders[i % len(graders)] if is_graded else None,
                    latitude=Decimal(str(round(dlat, 6))),
                    longitude=Decimal(str(round(dlng, 6))),
                    is_synced=True,
                )
                deliveries.append(delivery)
        self.stdout.write(f"Created {len(deliveries)} deliveries")
        return deliveries

    def _create_grade_prices(self):
        prices = []
        today = date.today()
        for grade_letter, price in [("A", 55.00), ("B", 45.00), ("C", 35.00), ("PREMIUM", 65.00), ("STANDARD", 30.00)]:
            gp = GradePrice.objects.create(
                grade_letter=grade_letter,
                price_per_unit=Decimal(str(price)),
                effective_from=today - timedelta(days=90),
            )
            prices.append(gp)
        self.stdout.write(f"Created {len(prices)} grade prices")
        return prices

    def _create_grades(self, deliveries, users, cooperatives):
        grades = []
        graders = [u for u in users if u.role == UserRole.GRADER]
        managers = [u for u in users if u.role == UserRole.MANAGER]
        for i, delivery in enumerate(deliveries):
            if delivery.status != DeliveryStatus.GRADED:
                continue
            grade_letters = [GradeLetter.A, GradeLetter.B, GradeLetter.C, GradeLetter.PREMIUM]
            gl = grade_letters[i % len(grade_letters)]
            grade = Grade.objects.create(
                delivery=delivery,
                cooperative=delivery.cooperative,
                grade_letter=gl,
                price_per_unit=Decimal(str(45.0 + (i % 4) * 10.0)),
                is_inventory_updated=True,
            )
            delivery.grade = gl
            delivery.save(update_fields=["grade"])
            grades.append(grade)
        self.stdout.write(f"Created {len(grades)} grades")
        return grades

    def _create_inventory(self, grades):
        inventory = []
        for grade in grades:
            inv = Inventory.objects.create(
                cooperative=grade.cooperative,
                batch_id=grade.delivery.batch_id,
                product_type=grade.delivery.product_type,
                grade=grade.grade_letter,
                unit="litres",
                quantity_in=grade.delivery.volume_litres or 0,
            )
            inventory.append(inv)
        self.stdout.write(f"Created {len(inventory)} inventory records")
        return inventory

    def _create_buyers(self, cooperatives):
        buyers = []
        for coop in cooperatives:
            buyer = Buyer.objects.create(
                cooperative=coop,
                name=f"{coop.name.split(' Co-op')[0]} Buyer Ltd",
                contact_person="John Buyer",
                phone_number=f"0722{hash(str(coop.id)) % 100000:05d}",
                email=f"buyer@{coop.prefix.lower()}.com",
                is_active=True,
            )
            buyers.append(buyer)
        self.stdout.write(f"Created {len(buyers)} buyers")
        return buyers

    def _create_sales(self, buyers, inventory, users, cooperatives):
        sales = []
        managers = [u for u in users if u.role == UserRole.MANAGER]
        for i, inv in enumerate(inventory[:10]):
            sale = Sale.objects.create(
                buyer=buyers[i % len(buyers)],
                inventory=inv,
                cooperative=inv.cooperative,
                product_type=inv.product_type,
                grade_letter=inv.grade,
                unit=SaleUnit.LITRES,
                quantity=inv.quantity_in,
                price_per_unit=Decimal("50.00"),
                total_amount=inv.quantity_in * Decimal("50.00"),
                status=SaleStatus.COMPLETED if i % 2 == 0 else SaleStatus.PENDING,
                inventory_updated=i % 2 == 0,
                recorded_by=managers[i % len(managers)],
                invoice_number=f"INV-{inv.cooperative.prefix}-{2026}{i+1:03d}",
            )
            inv.quantity_out = inv.quantity_in if i % 2 == 0 else 0
            inv.is_sold = i % 2 == 0
            inv.save(update_fields=["quantity_out", "is_sold"])
            sales.append(sale)
        self.stdout.write(f"Created {len(sales)} sales")
        return sales

    def _create_cycles(self, cooperatives, users, farmers):
        cycles = []
        for coop in cooperatives:
            for months_ago, status in [(1, CycleStatus.COMPUTED), (0, CycleStatus.DRAFT)]:
                start = date.today().replace(day=1) - timedelta(days=months_ago * 31)
                end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                cycle = PaymentCycle.objects.create(
                    cooperative=coop,
                    name=f"{start.strftime('%B %Y')} Payment Cycle",
                    start_date=start,
                    end_date=end,
                    status=status,
                    totals={"total_quantity": 0, "total_gross": 0, "total_net": 0, "farmer_count": 0},
                )
                cycles.append(cycle)
        self.stdout.write(f"Created {len(cycles)} payment cycles")
        return cycles

    def _create_farmer_payments(self, cycles, farmers):
        payments = []
        computed_cycles = [c for c in cycles if c.status == CycleStatus.COMPUTED]
        for cycle in computed_cycles:
            coop_farmers = [f for f in farmers if f.cooperative_id == cycle.cooperative_id]
            total_gross = Decimal("0")
            total_net = Decimal("0")
            for farmer in coop_farmers:
                gross = Decimal(str(round(5000.0 + hash(str(farmer.id)) % 5000, 2)))
                levy = gross * cycle.cooperative.levy_percentage / Decimal("100")
                net = gross - levy - cycle.cooperative.monthly_fee
                payment = FarmerPayment.objects.create(
                    cycle=cycle,
                    farmer=farmer,
                    cooperative=cycle.cooperative,
                    total_quantity=Decimal("100.00"),
                    grade_breakdown={
                        "A": {"kg": "100.00", "amount": str(gross)},
                    },
                    gross_amount=gross,
                    deductions={
                        "levy": str(levy),
                        "monthly_fee": str(cycle.cooperative.monthly_fee),
                        "loan_repayment": "0.00",
                        "input_credit": "0.00",
                    },
                    net_amount=net,
                    payment_status=PaymentStatus.PENDING,
                    computation_log={
                        "method": "FIXED_PRICE",
                        "total_quantity": "100.00",
                        "gross_amount": str(gross),
                        "deductions_applied": ["levy", "monthly_fee"],
                        "net_amount": str(net),
                        "withholding_tax": "0.00",
                    },
                    is_subject_to_withholding_tax=False,
                    withholding_tax_amount=Decimal("0"),
                )
                total_gross += gross
                total_net += net
                payments.append(payment)
            cycle.totals = {
                "total_quantity": sum(float(p.total_quantity) for p in payments if p.cycle_id == cycle.id),
                "total_gross": float(total_gross),
                "total_net": float(total_net),
                "farmer_count": len(coop_farmers),
            }
            cycle.total_levy = total_gross * cycle.cooperative.levy_percentage / Decimal("100")
            cycle.total_cooperative_fee = cycle.cooperative.monthly_fee * len(coop_farmers)
            cycle.computed_at = timezone.now()
            cycle.save(update_fields=["totals", "total_levy", "total_cooperative_fee", "computed_at"])
        self.stdout.write(f"Created {len(payments)} farmer payments")
        return payments

    def _create_disbursements(self, cycles, farmers, farmer_payments, users):
        managers = [u for u in users if u.role == UserRole.MANAGER]
        computed_cycles = [c for c in cycles if c.status == CycleStatus.COMPUTED]
        for cycle in computed_cycles[:1]:
            coop_fps = [fp for fp in farmer_payments if fp.cycle_id == cycle.id]
            batch = DisbursementBatch.objects.create(
                cooperative=cycle.cooperative,
                payment_cycle=cycle,
                status=BatchStatus.PENDING,
                total_amount=sum(fp.net_amount for fp in coop_fps),
                total_transactions=len(coop_fps),
                created_by=managers[0] if managers else None,
                notes="Demo seed batch",
            )
            for fp in coop_fps:
                membership = fp.farmer.memberships.filter(
                    cooperative=cycle.cooperative
                ).first()
                recipient = ''
                if membership:
                    if membership.payment_method == 'M-PESA':
                        recipient = membership.mpesa_number or fp.farmer.phone_number
                    elif membership.payment_method == 'BANK':
                        recipient = membership.bank_account or ''
                DisbursementTransaction.objects.create(
                    batch=batch,
                    cooperative=cycle.cooperative,
                    farmer=fp.farmer,
                    farmer_payment=fp,
                    amount=fp.net_amount,
                    payment_method=DisbursementPaymentMethod.M_PESA,
                    recipient_identifier=recipient,
                    recipient_name=f"{fp.farmer.first_name} {fp.farmer.last_name}",
                    status=TransactionStatus.PENDING,
                    conversation_id=str(uuid.uuid4()),
                )
        self.stdout.write("Created disbursement batch + transactions")

    def _create_loans(self, farmers, farmer_payments, cooperatives):
        loans = []
        for coop in cooperatives:
            coop_farmers = [f for f in farmers if f.cooperative_id == coop.id][:5]
            for farmer in coop_farmers:
                principal = Decimal(str(round(10000.0 + hash(str(farmer.id)) % 40000, 2)))
                interest = Decimal("5.00")
                total_rep = principal * (Decimal("1") + interest / Decimal("100"))
                installments = 12
                loan = Loan.objects.create(
                    cooperative=coop,
                    farmer=farmer,
                    amount_principal=principal,
                    interest_rate=interest,
                    number_of_installments=installments,
                    status=LoanStatus.ACTIVE,
                    notes="Demo seed loan",
                )
                farmer.has_active_loan = True
                farmer.save(update_fields=["has_active_loan"])
                loans.append(loan)
        self.stdout.write(f"Created {len(loans)} loans")

    def _create_notifications(self, farmers, cooperatives):
        notifications = []
        for farmer in farmers[:20]:
            n = Notification.objects.create(
                cooperative=farmer.cooperative,
                recipient=farmer,
                channel=NotificationChannel.SMS,
                notification_type=NotificationType.DELIVERY_CONFIRMATION,
                content=f"Dear {farmer.first_name}, your delivery has been recorded.",
                status=NotificationStatus.SENT,
            )
            notifications.append(n)
        self.stdout.write(f"Created {len(notifications)} notifications")

    def _print_summary(self, coops, users, farmers, deliveries, grades, inventory, buyers, sales, cycles, farmer_payments):
        self.stdout.write(self.style.SUCCESS("\n=== Seed Data Summary ==="))
        self.stdout.write(f"Cooperatives:      {len(coops)}")
        self.stdout.write(f"Users:             {len(users)}")
        self.stdout.write(f"Farmers:           {len(farmers)}")
        self.stdout.write(f"Deliveries:        {len(deliveries)}")
        self.stdout.write(f"Grades:            {len(grades)}")
        self.stdout.write(f"Inventory:         {len(inventory)}")
        self.stdout.write(f"Buyers:            {len(buyers)}")
        self.stdout.write(f"Sales:             {len(sales)}")
        self.stdout.write(f"Payment Cycles:    {len(cycles)}")
        self.stdout.write(f"Farmer Payments:   {len(farmer_payments)}")
        self.stdout.write(self.style.SUCCESS("Done seeding demo data."))
