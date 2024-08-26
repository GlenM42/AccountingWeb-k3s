# Generated by Django 5.0.3 on 2024-03-06 21:27

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('account_id', models.AutoField(primary_key=True, serialize=False)),
                ('account_name', models.CharField(max_length=255)),
                ('account_type', models.CharField(choices=[('asset', 'Asset'), ('liability', 'Liability'), ('equity', 'Equity'), ('revenue', 'Revenue'), ('expense', 'Expense')], max_length=10)),
                ('total_value', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('debit_or_credit', models.CharField(choices=[('debit', 'Debit'), ('credit', 'Credit')], max_length=8)),
            ],
            options={
                'db_table': 'accounts',
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('transaction_id', models.AutoField(primary_key=True, serialize=False)),
                ('transaction_date', models.DateTimeField(auto_now_add=True)),
                ('description', models.TextField()),
                ('debit', models.CharField(choices=[('Food Expenses', 'Food Expenses'), ('Equity', 'Equity'), ('Cash', 'Cash'), ('DC-Checking Account', 'DC-Checking Account'), ('Vanguard Money Fund', 'Vanguard Money Fund'), ('Vanguard Brokerage Account', 'Vanguard Brokerage Account'), ('DC-Savings Account', 'DC-Savings Account'), ('FCU-CC-Balance', 'FCU-CC-Balance'), ('Apple Card', 'Apple Card'), ('Revenue-Tutoring', 'Revenue-Tutoring'), ('Revenue-XO', 'Revenue-XO'), ('Utilities Expenses', 'Utilities Expenses'), ('Entertainment Expenses', 'Entertainment Expenses'), ('Salary Income', 'Salary Income'), ('Gift Income', 'Gift Income'), ('Investment Income', 'Investment Income'), ('General Asset Account', 'General Asset Account'), ('General Equity Account', 'General Equity Account'), ('General Liability Account', 'General Liability Account')], max_length=50)),
                ('credit', models.CharField(choices=[('Food Expenses', 'Food Expenses'), ('Equity', 'Equity'), ('Cash', 'Cash'), ('DC-Checking Account', 'DC-Checking Account'), ('Vanguard Money Fund', 'Vanguard Money Fund'), ('Vanguard Brokerage Account', 'Vanguard Brokerage Account'), ('DC-Savings Account', 'DC-Savings Account'), ('FCU-CC-Balance', 'FCU-CC-Balance'), ('Apple Card', 'Apple Card'), ('Revenue-Tutoring', 'Revenue-Tutoring'), ('Revenue-XO', 'Revenue-XO'), ('Utilities Expenses', 'Utilities Expenses'), ('Entertainment Expenses', 'Entertainment Expenses'), ('Salary Income', 'Salary Income'), ('Gift Income', 'Gift Income'), ('Investment Income', 'Investment Income'), ('General Asset Account', 'General Asset Account'), ('General Equity Account', 'General Equity Account'), ('General Liability Account', 'General Liability Account')], max_length=50)),
                ('dollar_amount', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
            ],
            options={
                'db_table': 'transactions',
            },
        ),
    ]
