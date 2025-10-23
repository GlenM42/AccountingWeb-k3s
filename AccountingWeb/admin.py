from django.contrib import admin
from .models import Account, Transaction

class OwnerScopedMixin:
    """Force owner scoping across list/query and object permissions for ALL users (even superuser)."""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(owner=request.user)

    def has_view_permission(self, request, obj=None):
        if obj is None:
            return True
        return obj.owner_id == request.user.id

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return obj.owner_id == request.user.id

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        return obj.owner_id == request.user.id

    def has_module_permission(self, request):
        # allow entering the app
        return True

class AccountAdmin(admin.ModelAdmin):
    list_display = ("owner", "account_name", "account_type",)
    search_fields = ("account_name",)
    list_filter = ("owner", "account_type")
    readonly_fields = ("total_value_ct", "total_value_iv")


class TransactionAdmin(admin.ModelAdmin):
    # show the related account names
    list_display = ("owner", "transaction_date", "debit", "credit",)
    list_filter = ("owner", "transaction_date")
    readonly_fields = ("description_ct", "description_iv", "dollar_amount_ct", "dollar_amount_iv")
    search_fields = (
        "description",
        "debit",
        "credit",
    )

    def get_queryset(self, request):
        # optional: scope admin list to the current user
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)


# Register Account with the custom AccountAdmin class
admin.site.register(Account, AccountAdmin)

# Register Transaction normally
admin.site.register(Transaction, TransactionAdmin)
