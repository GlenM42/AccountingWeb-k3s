from datetime import timedelta
from decimal import Decimal

import pandas as pd
from django.db.models import Q, Sum
from django.utils import timezone

from .crypto import dec_decimal
from .models import Account, Transaction


def _decrypt_account_total(account, dek: bytes) -> Decimal:
    """
    Return Decimal current balance for an Account from encrypted fields.
    """
    total = dec_decimal(dek, getattr(account, "total_value_ct", None),
                             getattr(account, "total_value_iv", None))
    return total if total is not None else Decimal("0")


def _decrypt_txn_amount(txn, dek: bytes) -> Decimal:
    """
    Return Decimal amount for a Transaction.
    Works whether the project still has plaintext dollar_amount
    or has migrated to dollar_amount_ct/iv.
    """
    # Encrypted path
    if hasattr(txn, "dollar_amount_ct"):
        amt = dec_decimal(dek, getattr(txn, "dollar_amount_ct", None),
                               getattr(txn, "dollar_amount_iv", None))
        if amt is not None:
            return amt
    # Fallback to plaintext if present
    if hasattr(txn, "dollar_amount") and txn.dollar_amount is not None:
        return Decimal(txn.dollar_amount)
    return Decimal("0")


def calculate_account_balance_over_time(user, account_name, days=7, dek: bytes | None = None):
    """
    Calculate the balance of the given account over the past 'days' number of days.
    Returns (dates: [str], values: [float]).
    """
    if not dek:
        raise ValueError("Data encryption key (dek) is required for graph calculations.")

    # Get the account and its current (decrypted) balance
    account = Account.objects.filter(owner=user, account_name=account_name).first()
    if not account:
        raise ValueError(f"Account '{account_name}' not found.")

    current_balance = _decrypt_account_total(account, dek)

    today = timezone.now()
    start_date = today - timedelta(days=days)

    # debit-or-credit nature of the account
    is_debit_account = account.debit_or_credit == 'debit'

    # Pull raw transactions (no DB-side sums on encrypted data)
    txns = (
        Transaction.objects
        .filter(owner=user)
        .filter(Q(debit=account_name) | Q(credit=account_name),
                transaction_date__gte=start_date)
        .order_by('-transaction_date')  # newest → oldest
        .only('debit', 'credit', 'transaction_date',
            'dollar_amount_ct', 'dollar_amount_iv')  # fields may vary; safe to include
    )

    # Aggregate per calendar date in Python
    # structure: {date: {"debit_sum": Decimal, "credit_sum": Decimal}}
    per_day = {}

    for t in txns:
        d = t.transaction_date.date()
        per_day.setdefault(d, {"debit_sum": Decimal("0"), "credit_sum": Decimal("0")})
        amt = _decrypt_txn_amount(t, dek)

        if t.debit == account_name:
            per_day[d]["debit_sum"] += amt
        if t.credit == account_name:
            per_day[d]["credit_sum"] += amt

    # Build rolling snapshots by "undoing" newer days first
    rolling_balance = current_balance
    snapshots = []

    # Iterate newest → oldest (to undo correctly)
    for d in sorted(per_day.keys(), reverse=True):
        debit_sum = per_day[d]["debit_sum"]
        credit_sum = per_day[d]["credit_sum"]

        if is_debit_account:
            # For debit accounts: Subtract outflows (debits) and add inflows (credits)
            rolling_balance += credit_sum - debit_sum
        else:
            # For credit accounts: Add outflows (credits) and subtract inflows (debits)
            rolling_balance += debit_sum - credit_sum

        snapshots.append({"date": d, "balance": float(rolling_balance)})

    # Include today's current balance snapshot (after undoing history)
    snapshots.append({"date": today.date(), "balance": float(current_balance)})

    df = pd.DataFrame(snapshots).sort_values(by='date')
    return df['date'].astype(str).tolist(), df['balance'].tolist()
