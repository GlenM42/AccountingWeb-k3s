from django.contrib.auth.views import LoginView
from .models import Account, Transaction
from django.shortcuts import render, redirect
from decimal import Decimal


def home_view(request):
    return render(request, 'index.html')


def login(request):
    response = LoginView.as_view(template_name='registration/login.html')(request)
    return response


def balance_sheet_view(request):
    # Retrieve accounts based on types
    assets = Account.objects.filter(account_type='asset')
    liabilities = Account.objects.filter(account_type='liability')
    equity_accounts = Account.objects.filter(account_type='equity')

    # Include revenue and expenses accounts in the equity column
    revenue_expenses = Account.objects.filter(account_type__in=['revenue', 'expense'])
    equity_accounts = equity_accounts.union(revenue_expenses)

    total_assets = sum(asset.total_value for asset in assets)
    total_liabilities = sum(liability.total_value for liability in liabilities)
    total_equity = sum(equity_account.total_value for equity_account in equity_accounts)

    return render(request, 'balance_sheet.html', {
        'assets': assets,
        'liabilities': liabilities,
        'equity_accounts': equity_accounts,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
    })


def transaction_history_view(request):
    transactions = Transaction.objects.all()
    return render(request, 'transaction_history.html', {'transactions': transactions})


def new_transaction_view(request):
    if request.method == 'POST':
        debit_account_name = request.POST['debit_account']
        credit_account_name = request.POST['credit_account']
        dollar_amount = Decimal(request.POST.get('dollar_amount', 0))
        description = request.POST['description']

        # Insert the transaction
        Transaction.objects.create(debit=debit_account_name, credit=credit_account_name, dollar_amount=dollar_amount,
                                   description=description)

        # Update the debit account
        debit_account_obj = Account.objects.get(account_name=debit_account_name)
        if debit_account_obj.debit_or_credit == 'debit':
            debit_account_obj.total_value += dollar_amount
        else:  # If it's a credit account
            debit_account_obj.total_value -= dollar_amount
        debit_account_obj.save()

        # Update the credit account
        credit_account_obj = Account.objects.get(account_name=credit_account_name)
        if credit_account_obj.debit_or_credit == 'credit':
            credit_account_obj.total_value += dollar_amount
        else:  # If it's a debit account
            credit_account_obj.total_value -= dollar_amount
        credit_account_obj.save()

        return redirect('transaction_history')  # Redirect to the transaction history page or any other page you want

    # Retrieve the list of account names for the drop-down
    account_names = [account.account_name for account in Account.objects.all()]

    return render(request, 'new_transaction.html', {'account_names': account_names})


def income_statement_view(request):
    # Lists of account names for revenues and expenses
    revenue_accounts = ["Revenue-Tutoring", "Revenue-Salary", "Revenue-Gift", "Gift Income", 'Revenue-Investment']
    expense_accounts = ["Utilities Expenses", 'Lodge Expenses', "Food Expenses", 'Rent Expense',
                        "Entertainment Expenses", 'Insurance Expense', 'Interest Expense', 'Office Supplies Expense',
                        'Telephone Expense']

    # Retrieve total revenue and expenses directly from the Account model
    revenue_details = Account.objects.filter(account_name__in=revenue_accounts).values('account_name', 'total_value')
    expense_details = Account.objects.filter(account_name__in=expense_accounts).values('account_name', 'total_value')

    # Calculate total revenue and total expenses
    total_revenue = sum(item['total_value'] for item in revenue_details)
    total_expenses = sum(item['total_value'] for item in expense_details)
    profit = total_revenue - total_expenses

    for item in revenue_details:
        item['relative_weight'] = (item['total_value'] / total_revenue) * 100 if total_revenue else 0
    for item in expense_details:
        item['relative_weight'] = (item['total_value'] / total_expenses) * 100 if total_expenses else 0
    profit_weight = (profit / total_revenue) * 100 if total_revenue else 0

    # Prepare data for rendering
    context = {
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'profit': profit,
        'revenue_details': revenue_details,
        'profit_weight': profit_weight,
        'expense_details': expense_details,
    }

    return render(request, 'income_statement.html', context)
