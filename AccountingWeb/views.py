from decimal import Decimal
from django.shortcuts import redirect
import json
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .calculations import calculate_account_balance_over_time
from .models import Account, Transaction


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
    # Dynamically fetch revenue and expense accounts from the Account model
    revenue_details = Account.objects.filter(account_type='revenue').values('account_name', 'total_value')
    expense_details = Account.objects.filter(account_type='expense').values('account_name', 'total_value')

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


def get_graph_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        account_name = data.get('account')
        days = data.get('days', 30)

        # Calculate the graph data for the selected account
        dates, values = calculate_account_balance_over_time(account_name, days)

        initial_balance = values[0]
        final_balance = values[-1]
        change_in_dollars = final_balance - initial_balance
        if initial_balance > 0:
            change_in_percent = (change_in_dollars / initial_balance * 100)
        elif initial_balance < 0:
            change_in_percent = 0
        else:
            if change_in_dollars > 0:
                change_in_percent = 100
            else:
                change_in_percent = -100
        return JsonResponse({
            'dates': dates,
            'values': values,
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'change_in_dollars': change_in_dollars,
            'change_in_percent': change_in_percent
        })


def summary_view(request):
    account_names = Account.objects.values_list('account_name', flat=True)
    context = {'account_names': account_names}
    return render(request, 'summary.html', context)


def favicon_redirect(request):
    return redirect('/static/html5up-stellar/images/favicon.ico')


def apple_icon_redirect(request):
    return redirect('/static/html5up-stellar/images/apple-touch-icon.png')


def apple_icon_precomposed_redirect(request):
    return redirect('/static/html5up-stellar/images/apple-touch-icon-precomposed.png')
