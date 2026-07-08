from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Wipe all data from all tables using TRUNCATE CASCADE. Use with caution."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename NOT IN (
                    'spatial_ref_sys',
                    'geography_columns',
                    'geometry_columns'
                )
            """)
            tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            self.stdout.write(self.style.WARNING("No tables found."))
            return

        sql = "; ".join(f'TRUNCATE TABLE "{t}" RESTART IDENTITY CASCADE' for t in tables)
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cursor.execute("COMMIT")

        self.stdout.write(self.style.SUCCESS(f"Wiped {len(tables)} tables."))
