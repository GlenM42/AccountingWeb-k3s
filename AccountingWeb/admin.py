from django.contrib import admin
from .models import Account, Transaction


class AccountAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = ('account_name', 'account_type', 'total_value', 'debit_or_credit')
    # Enable search by account name
    search_fields = ('account_name',)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'description', 'debit', 'credit', 'dollar_amount')
    search_fields = ('description', 'debit', 'credit')


# Register Account with the custom AccountAdmin class
admin.site.register(Account, AccountAdmin)

# Register Transaction normally
admin.site.register(Transaction, TransactionAdmin)
