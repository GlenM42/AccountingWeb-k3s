from django.db import models

DEBIT_CREDIT_CHOICES = [
    ('debit', 'Debit'),
    ('credit', 'Credit'),
]

TRANSACTION_CHOICES = sorted([
    # Asset Accounts
    ("Cash", "Cash"),
    ("Accounts Receivable", "Accounts Receivable"),
    ("Inventory", "Inventory"),
    ("Prepaid Expenses", "Prepaid Expenses"),
    ("Office Supplies", "Office Supplies"),
    ("Furniture & Fixtures", "Furniture & Fixtures"),
    ("Buildings", "Buildings"),
    ("Vehicles", "Vehicles"),
    ("Land", "Land"),
    ("Checking Accounts", "Checking Accounts"),
    ("Savings Accounts", "Savings Accounts"),
    ("Investments Money", "Investments Money"),
    ("Investments Assets", "Investments Assets"),

    # Liability Accounts
    ("Accounts Payable", "Accounts Payable"),
    ("Credit Cards Payable", "Credit Cards Payable"),
    ("Wages Payable", "Wages Payable"),
    ("Interest Payable", "Interest Payable"),
    ("Notes Payable", "Notes Payable"),
    ("Mortgage Payable", "Mortgage Payable"),

    # Equity Accounts
    ("General Equity Account", "General Equity Account"),

    # Revenue Accounts
    ("Revenue-Salary", "Revenue-Salary"),
    ("Revenue-Tutoring", "Revenue-Tutoring"),
    ("Revenue-Gift", "Revenue-Gift"),
    ("Revenue-Investment", "Revenue-Investment"),

    # Expense Accounts
    ("Utilities Expenses", "Utilities Expenses"),
    ("Lodge Expenses", "Lodge Expenses"),
    ("Rent Expense", "Rent Expense"),
    ("Insurance Expense", "Insurance Expense"),
    ("Interest Expense", "Interest Expense"),
    ("Office Supplies Expense", "Office Supplies Expense"),
    ("Telephone Expense", "Telephone Expense"),
    ("Food Expenses", "Food Expenses"),
    ("Entertainment Expenses", "Entertainment Expenses"),
    ("Vacation Expenses", "Vacation Expenses"),
    ("Medical Expenses", "Medical Expenses"),
    ("Transportation Expenses", "Transportation Expenses"),
])


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
