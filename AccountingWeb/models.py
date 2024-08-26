from django.db import models

DEBIT_CREDIT_CHOICES = [
    ('debit', 'Debit'),
    ('credit', 'Credit'),
]

TRANSACTION_CHOICES = [
    ("Food Expenses", "Food Expenses"),
    ("Equity", "Equity"),
    ("Cash", "Cash"),
    ("DC-Checking Account", "DC-Checking Account"),
    ("Vanguard Money Fund", "Vanguard Money Fund"),
    ("Vanguard Brokerage Account", "Vanguard Brokerage Account"),
    ("DC-Savings Account", "DC-Savings Account"),
    ("FCU-CC-Balance", "FCU-CC-Balance"),
    ("Apple Card", "Apple Card"),
    ("Revenue-Tutoring", "Revenue-Tutoring"),
    ("Revenue-XO", "Revenue-XO"),
    ("Utilities Expenses", "Utilities Expenses"),
    ("Entertainment Expenses", "Entertainment Expenses"),
    ("Salary Income", "Salary Income"),
    ("Gift Income", "Gift Income"),
    ("Investment Income", "Investment Income"),
    ("General Asset Account", "General Asset Account"),
    ("General Equity Account", "General Equity Account"),
    ("General Liability Account", "General Liability Account"),
].sort()


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

    class Meta:
        db_table = 'accounts'


class Transaction(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    debit = models.CharField(max_length=50, choices=TRANSACTION_CHOICES)
    credit = models.CharField(max_length=50, choices=TRANSACTION_CHOICES)
    dollar_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    class Meta:
        db_table = "transactions"
