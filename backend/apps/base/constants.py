from django.db import models


class UserRole(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    MANAGER = 'manager', 'Manager'
    ACCOUNTANT = 'accountant', 'Accountant'
    GRADER = 'grader', 'Grader'
    FARMER = 'farmer', 'Farmer'
    AUDITOR = 'auditor', 'Auditor'
