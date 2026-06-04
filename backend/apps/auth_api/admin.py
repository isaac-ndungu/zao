from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.auth_api.models import User, TwoFactorOTP


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'phone_number', 'first_name', 'last_name',
        'role', 'cooperative', 'is_staff', 'is_active', 'two_fa_enabled',
    ]
    list_select_related = ['cooperative']
    list_filter = ['role', 'is_staff', 'is_active']
    search_fields = ['email', 'phone_number', 'first_name', 'last_name']
    ordering = ['email']
    readonly_fields = ('date_joined', 'last_login', 'updated_at')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('phone_number', 'first_name', 'last_name')}),
        ('Cooperative & Role', {'fields': ('cooperative', 'role', 'two_fa_enabled')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone_number', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(TwoFactorOTP)
class TwoFactorOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'purpose', 'otp_code', 'expires_at', 'is_used', 'attempts']
    list_select_related = ['user']
    list_filter = ['purpose', 'is_used']
    readonly_fields = ['otp_code', 'created_at']
