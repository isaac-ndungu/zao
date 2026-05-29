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


class IsManagerOrGrader(IsInRoles):
    roles = [UserRole.MANAGER, UserRole.GRADER]


class IsAccountantOrManager(IsInRoles):
    roles = [UserRole.ACCOUNTANT, UserRole.MANAGER]


class IsReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
