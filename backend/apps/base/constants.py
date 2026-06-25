from django.db import models


def get_soft_deletable_models():
    from django.apps import apps
    exclude = {'AuditLog'}
    return [m for m in apps.get_models() if m.__name__ not in exclude and hasattr(m, 'deleted_at')]


class UserRole(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    MANAGER = 'manager', 'Manager'
    ACCOUNTANT = 'accountant', 'Accountant'
    GRADER = 'grader', 'Grader'
    FARMER = 'farmer', 'Farmer'
    AUDITOR = 'auditor', 'Internal Auditor'
    EXTERNAL_AUDITOR = 'external_auditor', 'External Auditor'


KENYA_COUNTIES = [
    'Baringo', 'Bomet', 'Bungoma', 'Busia', 'Elgeyo Marakwet',
    'Embu', 'Garissa', 'Homa Bay', 'Isiolo', 'Kajiado',
    'Kakamega', 'Kericho', 'Kiambu', 'Kilifi', 'Kirinyaga',
    'Kisii', 'Kisumu', 'Kitui', 'Kwale', 'Laikipia',
    'Lamu', 'Machakos', 'Makueni', 'Mandera', 'Marsabit',
    'Meru', 'Migori', 'Mombasa', "Murang'a", 'Nairobi',
    'Nakuru', 'Nandi', 'Narok', 'Nyamira', 'Nyandarua',
    'Nyeri', 'Samburu', 'Siaya', 'Taita Taveta', 'Tana River',
    'Tharaka Nithi', 'Trans Nzoia', 'Turkana', 'Uasin Gishu',
    'Vihiga', 'Wajir', 'West Pokot',
]
