from django.db import models

DEBIT_CREDIT_CHOICES = [
    ('debit', 'Debit'),
    ('credit', 'Credit'),
]


class Account(models.Model):
    account_id = models.AutoField(primary_key=True)
    account_name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=10, choices=[
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ])
    total_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    debit_or_credit = models.CharField(max_length=8, choices=DEBIT_CREDIT_CHOICES)

    def __str__(self):
        # Customization to display the accounts' values
        return f"{self.account_name} ({self.account_type.capitalize()}) -- {self.total_value}"

    class Meta:
        db_table = 'accounts'


class Transaction(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    debit = models.CharField(max_length=50)
    credit = models.CharField(max_length=50)
    dollar_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return f"{self.debit} / {self.credit} -- {self.dollar_amount}"

    class Meta:
        db_table = "transactions"
