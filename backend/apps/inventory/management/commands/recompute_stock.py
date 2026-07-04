from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Recompute Stock from Inventory (cycle-pools). Use --check to assert no drift.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check', action='store_true',
            help='Print summary and report any drift without applying.',
        )

    def handle(self, *args, **options):
        from apps.inventory.models import Inventory, Stock

        expected = defaultdict(
            lambda: {'qty': Decimal('0'), 'unit': None, 'coop_id': None}
        )
        for pool in Inventory.objects.all().select_related('cooperative'):
            k = (pool.cooperative_id, pool.product_type, pool.grade)
            expected[k]['coop_id'] = pool.cooperative_id
            expected[k]['unit'] = pool.unit
            expected[k]['qty'] += (pool.quantity_in or Decimal('0')) - (pool.quantity_out or Decimal('0'))

        actual = {(s.cooperative_id, s.product_type, s.grade): s for s in Stock.objects.all()}

        n_coops = len({k[0] for k in expected})
        drift = []
        for k, data in expected.items():
            s = actual.get(k)
            if s is None:
                drift.append(f'MISSING Stock for {k}')
                continue
            if s.quantity_available != data['qty']:
                drift.append(
                    f'DRIFT {k}: stock={s.quantity_available} expected={data["qty"]}'
                )
        for k, s in actual.items():
            if k not in expected:
                drift.append(f'EXTRA Stock {k} (no Inventory pools)')

        self.stdout.write(f'Recomputed {len(expected)} Stock rows across {n_coops} cooperatives.')
        if drift:
            for d in drift:
                self.stdout.write(self.style.WARNING(d))
            if options['check']:
                self.stdout.write(self.style.ERROR('Drift detected.'))
                return
        else:
            self.stdout.write(self.style.SUCCESS('No drift detected between Stock and Inventory.'))

        if options['check']:
            return

        with transaction.atomic():
            for k, data in expected.items():
                Stock.objects.update_or_create(
                    cooperative_id=k[0], product_type=k[1], grade=k[2],
                    defaults={'unit': data['unit'], 'quantity_available': data['qty']},
                )
            extras = [k for k in actual if k not in expected]
            for k in extras:
                Stock.objects.filter(
                    cooperative_id=k[0], product_type=k[1], grade=k[2],
                ).delete()
        self.stdout.write(self.style.SUCCESS('Stock recomputed.'))
