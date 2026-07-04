from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.base.constants import UserRole


class IsRole(BasePermission):
    role = None

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == self.role
        )


class IsAdmin(IsRole):
    role = UserRole.ADMIN


class IsManager(IsRole):
    role = UserRole.MANAGER


class IsAccountant(IsRole):
    role = UserRole.ACCOUNTANT


class IsGrader(IsRole):
    role = UserRole.GRADER


class IsFarmer(IsRole):
    role = UserRole.FARMER


class IsAuditor(IsRole):
    role = UserRole.AUDITOR


class IsExternalAuditor(IsRole):
    role = UserRole.EXTERNAL_AUDITOR


class IsInRoles(BasePermission):
    roles = []

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) in self.roles
        )


class IsAdminOrManager(IsInRoles):
    roles = [UserRole.ADMIN, UserRole.MANAGER]


class IsStaff(IsInRoles):
    roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]


class IsAdminOrAuditor(IsInRoles):
    roles = [UserRole.ADMIN, UserRole.AUDITOR]


class IsInternalAuditor(IsInRoles):
    """Full read access: internal auditors and admins only. External auditors are excluded."""
    roles = [UserRole.AUDITOR, UserRole.ADMIN]


class IsAnyAuditor(IsInRoles):
    """Statements/report access: both internal and external auditors, plus admins."""
    roles = [UserRole.AUDITOR, UserRole.EXTERNAL_AUDITOR, UserRole.ADMIN]


class IsManagerOrGrader(IsInRoles):
    roles = [UserRole.MANAGER, UserRole.GRADER]


class IsAccountantOrManager(IsInRoles):
    roles = [UserRole.ACCOUNTANT, UserRole.MANAGER]


class IsManagerOrAuditor(IsInRoles):
    roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.AUDITOR]


class IsReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsAdminOrSuperUser(BasePermission):
    """Platform-level admin access: role=admin OR is_superuser=True.
    Excludes managers, accountants, graders, farmers, auditors, etc.
    Use for legal/compliance surfaces that must not be exposed to ops roles."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, 'is_superuser', False)
                or getattr(request.user, 'role', None) == UserRole.ADMIN
            )
        )
