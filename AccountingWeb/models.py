from django.db import models
from django.conf import settings

DEBIT_CREDIT_CHOICES = [
    ('debit', 'Debit'),
    ('credit', 'Credit'),
]


class UserSecret(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='secret')
    kdf = models.CharField(max_length=16, default='argon2id')
    salt_b64 = models.CharField(max_length=64)
    dek_wrapped_b64 = models.TextField()
    dek_iv_b64 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Account(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts",
        db_column='owner_id',
    )
    account_id = models.AutoField(primary_key=True)
    account_name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=10, choices=[
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ])
    # total_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    debit_or_credit = models.CharField(max_length=8, choices=DEBIT_CREDIT_CHOICES)

    # New encrypted fields
    total_value_ct = models.TextField(blank=True, null=True)
    total_value_iv = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        # Customization to display the accounts' values
        return f"{self.account_type.capitalize()} account #{self.account_id}"

    class Meta:
        db_table = 'accounts'


class Transaction(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
        db_column='owner_id',
    )
    transaction_id = models.AutoField(primary_key=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    # description = models.TextField()
    debit = models.CharField(max_length=50)
    credit = models.CharField(max_length=50)
    # dollar_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    # New encrypted fields
    description_ct = models.TextField(blank=True, null=True)
    description_iv = models.CharField(max_length=64, blank=True, null=True)
    dollar_amount_ct = models.TextField(blank=True, null=True)
    dollar_amount_iv = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"Transaction {self.transaction_id} on {self.transaction_date:%Y-%m-%d}"

    class Meta:
        db_table = "transactions"
