from decimal import Decimal
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.contrib.auth.views import LoginView as DjangoLoginView

from .calculations import calculate_account_balance_over_time
from .crypto import b64e, enc_str, enc_decimal, decrypt_tx, dec_decimal
from .models import Account, Transaction
from .utils import parse_date, snapshot_details, ledger_details, ensure_user_secret, unlock_user_dek, \
    get_dek_from_session, decrypt_accounts
import calendar
from datetime import date, timedelta

CUTOFF = date(2023, 11, 26)

@method_decorator(csrf_protect, name="dispatch")
class UnlockingLoginView(DjangoLoginView):
    template_name = 'registration/login.html'  # keep your template

    def form_valid(self, form):
        """
        After Django authenticates the user, use the very same password
        to derive the KEK, unwrap the DEK, and cache it in the session.
        """
        response = super().form_valid(form)
        user = self.request.user
        pw = form.cleaned_data.get('password')

        # Make sure the user has a wrapped DEK; create one if first login.
        ensure_user_secret(user, pw)

        # Unwrap the DEK and cache it for the session
        dek = unlock_user_dek(user, pw)
        self.request.session['dek_b64'] = b64e(dek)

        # Optional: expire on browser close (tightens exposure window)
        self.request.session.set_expiry(0)

        return response

def logout_view(request):
    # Belt & suspenders: drop DEK from session at logout
    request.session.pop('dek_b64', None)
    return DjangoLoginView.as_view()(request)  # or use LogoutView in urls and a signal (see below)


def require_unlocked(viewfunc):
    @wraps(viewfunc)
    def _wrapped(request, *args, **kwargs):
        if not get_dek_from_session(request):
            # For HTML views, redirect with a message.
            if request.method == 'GET':
                messages.info(request, "Please unlock your data to continue.")
                return redirect('home')
            # For POST/JSON, use a proper 403.
            return JsonResponse({"ok": False, "error": "Data is locked"}, status=403)
        return viewfunc(request, *args, **kwargs)
    return _wrapped


def home_view(request):
    return render(request, 'index.html')


def login(request):
    response = LoginView.as_view(template_name='registration/login.html')(request)
    return response

@login_required
def balance_sheet_view(request):
    dek = get_dek_from_session(request)
    if not dek:
        return redirect("login")

    # Filter by user
    q = Account.objects.filter(owner=request.user)

    # Retrieve accounts based on types
    assets_qs = q.filter(account_type='asset').order_by('account_name')
    liabilities_qs = q.filter(account_type='liability').order_by('account_name')
    equity_qs = q.filter(account_type='equity')

    # Decrypt so each Account has a transient .total_value (Decimal)
    assets      = decrypt_accounts(assets_qs, dek)
    liabilities = decrypt_accounts(liabilities_qs, dek)
    equity_accounts = decrypt_accounts(equity_qs, dek)

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

@login_required
def transaction_history_view(request):
    # Filter by user
    transaction_qs = Transaction.objects.all().filter(owner=request.user).order_by("-transaction_date")

    dek = get_dek_from_session(request)

    if not dek:
        return redirect('login')

    transaction_qs = [decrypt_tx(t, dek) for t in transaction_qs] # Decrypt what we have
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


@login_required
def new_transaction_view(request):
    if request.method == 'POST':
        dek = get_dek_from_session(request)
        if not dek:
            return redirect("login")

        debit_account_name = request.POST['debit_account']
        credit_account_name = request.POST['credit_account']
        dollar_amount = Decimal(request.POST.get('dollar_amount', 0))
        description = request.POST['description']

        # --- Encrypt the transaction fields ---
        desc_ct, desc_iv = enc_str(dek, description)
        amt_ct, amt_iv = enc_decimal(dek, dollar_amount)

        # Insert the transaction
        tx = Transaction(
            owner=request.user,
            debit=debit_account_name,
            credit=credit_account_name,

            # encrypted values:
            description_ct = desc_ct,
            description_iv = desc_iv,
            dollar_amount_ct = amt_ct,
            dollar_amount_iv = amt_iv,
        )
        tx.save()

        # Update the debit account
        debit_account_obj = Account.objects.get(owner=request.user, account_name=debit_account_name)

        current_debit_total = dec_decimal(dek, debit_account_obj.total_value_ct, debit_account_obj.total_value_iv)
        if current_debit_total is None:
            current_debit_total = Decimal("0")

        if debit_account_obj.debit_or_credit == 'debit':
            new_debit_total = current_debit_total + dollar_amount
        else:  # If it's a credit account
            new_debit_total = current_debit_total - dollar_amount

        d_ct, d_iv = enc_decimal(dek, new_debit_total)
        debit_account_obj.total_value_ct = d_ct
        debit_account_obj.total_value_iv = d_iv
        debit_account_obj.save(update_fields=["total_value_ct", "total_value_iv"])

        # Update the credit account
        credit_account_obj = Account.objects.get(owner=request.user, account_name=credit_account_name)

        current_credit_total = dec_decimal(dek, credit_account_obj.total_value_ct, credit_account_obj.total_value_iv)
        if current_credit_total is None:
            current_credit_total = Decimal("0")

        if credit_account_obj.debit_or_credit == 'credit':
            new_credit_total = current_credit_total + dollar_amount
        else:  # If it's a debit account
            new_credit_total = current_credit_total - dollar_amount

        c_ct, c_iv = enc_decimal(dek, new_credit_total)
        credit_account_obj.total_value_ct = c_ct
        credit_account_obj.total_value_iv = c_iv
        credit_account_obj.save(update_fields=["total_value_ct", "total_value_iv"])

        return redirect('transaction_history')  # Redirect to the transaction history

    # Retrieve the list of account names for the drop-down in alphabetical order
    account_names = [account.account_name for account in Account.objects.filter(owner=request.user).order_by('account_name')]

    return render(request, 'new_transaction.html', {'account_names': account_names})


@login_required
def income_statement_view(request):
    dek = get_dek_from_session(request)
    if not dek:
        return redirect("login")

    # Filter by user
    q = Transaction.objects.filter(owner=request.user)

    # 1. window
    first_txn = q.order_by("transaction_date").first()
    today     = timezone.localdate()

    start_date = parse_date(request.GET.get("start_date"), first_txn.transaction_date.date() if first_txn else today)
    end_date   = parse_date(request.GET.get("end_date"), today)
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # 2. choose engine
    if start_date <= CUTOFF:
        revenue, expense = snapshot_details(request.user, dek)
    else:
        revenue, expense = ledger_details(request.user, start_date, end_date, dek)

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


@login_required
def get_graph_data(request):
    if request.method == 'POST':
        dek = get_dek_from_session(request)
        if not dek:
            return redirect("login")

        data = json.loads(request.body)
        account_name = data.get('account')
        days = data.get('days', 30)

        # Calculate the graph data for the selected account
        dates, values = calculate_account_balance_over_time(request.user, account_name, days, dek)

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


@login_required
def summary_view(request):
    # Filter by user
    q = Account.objects.filter(owner=request.user)

    account_names = q.values_list('account_name', flat=True)
    context = {'account_names': account_names}
    return render(request, 'summary.html', context)


def favicon_redirect(request):
    return redirect('/static/html5up-stellar/images/favicon.ico')


def apple_icon_redirect(request):
    return redirect('/static/html5up-stellar/images/apple-touch-icon.png')


def apple_icon_precomposed_redirect(request):
    return redirect('/static/html5up-stellar/images/apple-touch-icon-precomposed.png')

@login_required
@require_POST
def unlock_data(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    pw = (request.POST.get("password") or "").strip()
    if not pw:
        return JsonResponse({"ok": False, "error": "Password required"}, status=400)

    # Ensure per-user secret exists, then unlock
    ensure_user_secret(request.user, pw)
    try:
        dek = unlock_user_dek(request.user, pw)
    except Exception:
        return JsonResponse({"ok": False, "error": "Wrong password"}, status=403)

    # Backfill legacy plaintext -> encrypted for THIS user (idempotent)
    from .utils import backfill_user_transactions_to_encrypted
    backfill_user_transactions_to_encrypted(request.user, dek)

    # Cache DEK for this session
    request.session["dek_b64"] = b64e(dek)
    request.session.modified = True
    return JsonResponse({"ok": True})
