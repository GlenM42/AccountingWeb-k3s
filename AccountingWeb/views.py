from decimal import Decimal
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from .calculations import calculate_account_balance_over_time
from .models import Account, Transaction
from .utils import parse_date, snapshot_details, ledger_details
import calendar
from datetime import date, timedelta

CUTOFF = date(2023, 11, 26)


def home_view(request):
    return render(request, 'index.html')


def login(request):
    response = LoginView.as_view(template_name='registration/login.html')(request)
    return response


def balance_sheet_view(request):
    # Retrieve accounts based on types
    assets = Account.objects.filter(account_type='asset').order_by('account_name')
    liabilities = Account.objects.filter(account_type='liability').order_by('account_name')
    equity_accounts = Account.objects.filter(account_type='equity')

    total_assets = sum(asset.total_value for asset in assets)
    total_liabilities = sum(liability.total_value for liability in liabilities)

    return render(request, 'balance_sheet.html', {
        'assets': assets,
        'liabilities': liabilities,
        'equity_accounts': equity_accounts,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_assets - total_liabilities,
    })

def transaction_history_view(request):
    transaction_qs = Transaction.objects.all().order_by("-transaction_date")

    paginator   = Paginator(transaction_qs, 50)     # 50 items per page
    page_number = request.GET.get("page")           # ?page=2

    try:
        transactions = paginator.page(page_number)
    except PageNotAnInteger:                        # page=None or garbage
        transactions = paginator.page(1)
    except EmptyPage:                               # page too high
        transactions = paginator.page(paginator.num_pages)

    return render(
        request,
        "transaction_history.html",
        {"transactions": transactions}              # this is now a *Page* object
    )


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

    # Retrieve the list of account names for the drop-down in alphabetical order
    account_names = [account.account_name for account in Account.objects.order_by('account_name')]

    return render(request, 'new_transaction.html', {'account_names': account_names})


def income_statement_view(request):
    # 1. window
    first_txn = Transaction.objects.order_by("transaction_date").first()
    today     = timezone.localdate()

    start_date = parse_date(request.GET.get("start_date"), first_txn.transaction_date.date() if first_txn else today)
    end_date   = parse_date(request.GET.get("end_date"), today)
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # 2. choose engine
    if start_date <= CUTOFF:
        revenue, expense = snapshot_details()
    else:
        revenue, expense = ledger_details(start_date, end_date)

    # 3. totals & weights
    total_rev = sum(d["total_value"] for d in revenue)
    total_exp = sum(d["total_value"] for d in expense)
    profit    = total_rev - total_exp

    for d in revenue:
        d["relative_weight"] = (d["total_value"] / total_rev * 100) if total_rev else 0
    for d in expense:
        d["relative_weight"] = (d["total_value"] / total_exp * 100) if total_exp else 0
    profit_weight = (profit / total_rev * 100) if total_rev else 0

    convenience = {
        # rolling periods, all-inclusive of ‘today’
        "Last&nbsp;week": (today - timedelta(days=7), today),
        "Last&nbsp;two weeks": (today - timedelta(days=14), today),
        "Last&nbsp;month": (today - timedelta(days=30), today),
        "Last&nbsp;½&nbsp;year": (today - timedelta(days=182), today),
        "Last&nbsp;year": (today - timedelta(days=365), today),
        "YTD": (date(today.year, 1, 1), today),
    }

    # current-year quarters
    for q in range(1, 5):
        q_start = date(today.year, 3 * q - 2, 1)
        q_end = date(today.year, 3 * q, calendar.monthrange(today.year, 3 * q)[1])
        # avoid future dates for Q3/Q4 early in the year
        convenience[f"Q{q}"] = (q_start, min(q_end, today))

    # “since inception” flavours
    inception_start = first_txn.transaction_date.date() if first_txn else today
    convenience["Since&nbsp;inception&nbsp;OLD"] = (inception_start, today)
    convenience["Since&nbsp;inception&nbsp;NEW"] = (CUTOFF + timedelta(days=1), today)

    # build a list that is trivial to loop over in the template
    ranges = [
        {"label": label,
         "start": s.isoformat(),
         "end": e.isoformat()}
        for label, (s, e) in convenience.items()
    ]

    return render(request, "income_statement.html", {
        "start_date":      start_date,
        "end_date":        end_date,
        "total_revenue":   total_rev,
        "total_expenses":  total_exp,
        "profit":          profit,
        "profit_weight":   profit_weight,
        "revenue_details": revenue,
        "expense_details": expense,
        "quick_ranges": ranges,
    })


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
