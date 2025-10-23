from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from django.db.models import Sum

from AccountingWeb.crypto import new_dek, new_salt, derive_kek_from_password, aesgcm_encrypt, aesgcm_decrypt, enc_str, \
    enc_decimal, dec_str, dec_decimal
from AccountingWeb.models import Account, Transaction, UserSecret

ORPHAN_META = {
    "DC-Savings Account":         "asset",
    "DC-Checking Account":        "asset",
    "Vanguard Brokerage Account": "asset",
    "Vanguard Money Fund":        "asset",
    "Savings Accounts":           "asset",
    "General Asset Account":      "asset",
    "Gift Income":                "revenue",
    "Salary Income":              "revenue",
    "Revenue-XO":                 "revenue",
    "Investment Income":          "revenue",
    "Equity":                     "equity",
    "FCU-CC-Balance":             "liability",
    "Apple Card":                 "liability",
}

def parse_date(iso, fallback):
    """Parse YYYY-MM-DD safely or return *fallback*."""
    try:
        return datetime.strptime(iso, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return fallback


def snapshot_details(user, dek):
    """
    Return two lists of dicts:
      revenue = [{'account_name': str, 'total_value': Decimal}, ...]
      expense = [{'account_name': str, 'total_value': Decimal}, ...]
    Values are decrypted in memory; ordering is done in Python.
    """
    # Pull querysets
    rev_qs = Account.objects.filter(owner=user, account_type="revenue")
    exp_qs = Account.objects.filter(owner=user, account_type="expense")

    # Decrypt accounts to attach .total_value (Decimal)
    rev_accounts = decrypt_accounts(rev_qs, dek)
    exp_accounts = decrypt_accounts(exp_qs, dek)

    # Shape like .values("account_name", "total_value") would
    revenue = [{"account_name": a.account_name, "total_value": a.total_value}
               for a in rev_accounts]
    expense = [{"account_name": a.account_name, "total_value": a.total_value}
               for a in exp_accounts]

    # Sort descending by total_value to match .order_by("-total_value")
    revenue.sort(key=lambda d: d["total_value"], reverse=True)
    expense.sort(key=lambda d: d["total_value"], reverse=True)

    return revenue, expense

def _dec_amount(tx: Transaction, dek: bytes) -> Decimal:
    amt = dec_decimal(dek, getattr(tx, "dollar_amount_ct", None),
                           getattr(tx, "dollar_amount_iv", None))
    return amt if amt is not None else Decimal("0")

def ledger_details(user, start_date, end_date, dek: bytes):
    """
    Summarise revenue / expense movements **inside** the window.
    • Skips assets, liabilities, equity.
    • Flags orphaned accounts with is_deleted=True (for red rows).
    Returns (revenue_list, expense_list) where each item is:
      {"account_name": str, "total_value": Decimal, "is_deleted": bool}
    """
    # 1) Pull raw transactions (no DB-side sum on encrypted data)
    txns = (Transaction.objects
            .filter(owner=user, transaction_date__date__range=(start_date, end_date))
            .only('debit', 'credit', 'transaction_date', 'dollar_amount_ct', 'dollar_amount_iv')
            .order_by('transaction_date'))

    # 2) Aggregate in Python by account name and side
    book = defaultdict(lambda: {"debit": Decimal("0"), "credit": Decimal("0")})
    for tx in txns:
        amt = _dec_amount(tx, dek)
        if tx.debit:   # in case of blanks
            book[tx.debit]["debit"]   += amt
        if tx.credit:
            book[tx.credit]["credit"] += amt

    # 3) Build metadata (what type each account is)
    acc_meta = {a.account_name: a.account_type
                for a in Account.objects.filter(owner=user).all()}
    acc_meta.update(ORPHAN_META)

    live_names = set(acc_meta) - set(ORPHAN_META)
    revenue, expense = [], []

    # 4) Classify and compute net
    for name, sides in book.items():
        net = sides["credit"] - sides["debit"]  # credits increase revenue; debits increase expense
        acct_type = acc_meta.get(name)
        is_deleted = name not in live_names

        if acct_type == "revenue":
            revenue.append({"account_name": name, "total_value": net, "is_deleted": is_deleted})
        elif acct_type == "expense":
            # show expenses as positive totals
            expense.append({"account_name": name, "total_value": -net, "is_deleted": is_deleted})
        # skip assets / liabilities / equity

    revenue.sort(key=lambda d: d["total_value"], reverse=True)
    expense.sort(key=lambda d: d["total_value"], reverse=True)
    return revenue, expense

def ensure_user_secret(user, password: str):
    if hasattr(user, 'secret'):
        return
    dek = new_dek()
    salt_b64 = new_salt()
    kek = derive_kek_from_password(password, salt_b64)
    wrapped_b64, iv_b64 = aesgcm_encrypt(kek, dek)
    UserSecret.objects.create(
        user=user, kdf='argon2id', salt_b64=salt_b64,
        dek_wrapped_b64=wrapped_b64, dek_iv_b64=iv_b64
    )

def unlock_user_dek(user, password: str) -> bytes:
    sec = user.secret
    kek = derive_kek_from_password(password, sec.salt_b64)
    return aesgcm_decrypt(kek, sec.dek_wrapped_b64, sec.dek_iv_b64)

def rewrap_dek(user, old_password: str, new_password: str):
    sec = user.secret
    old_kek = derive_kek_from_password(old_password, sec.salt_b64)
    dek = aesgcm_decrypt(old_kek, sec.dek_wrapped_b64, sec.dek_iv_b64)
    new_salt_b64 = new_salt()
    new_kek = derive_kek_from_password(new_password, new_salt_b64)
    wrapped_b64, iv_b64 = aesgcm_encrypt(new_kek, dek)
    sec.salt_b64 = new_salt_b64
    sec.dek_wrapped_b64 = wrapped_b64
    sec.dek_iv_b64 = iv_b64
    sec.save(update_fields=["salt_b64", "dek_wrapped_b64", "dek_iv_b64"])

def get_dek_from_session(request) -> bytes | None:
    b64 = request.session.get("dek_b64")
    if not b64:
        return None
    from .crypto import b64d
    return b64d(b64)

def encrypt_transaction_fields(tx: Transaction, dek: bytes):
    # description
    ct, iv = enc_str(dek, tx.description)
    tx.description_ct, tx.description_iv = ct, iv
    # amount
    ct, iv = enc_decimal(dek, tx.dollar_amount)
    tx.dollar_amount_ct, tx.dollar_amount_iv = ct, iv

def decrypt_transaction_fields(tx: Transaction, dek: bytes):
    tx.description = dec_str(dek, tx.description_ct, tx.description_iv)
    tx.dollar_amount = dec_decimal(dek, tx.dollar_amount_ct, tx.dollar_amount_iv)

def decrypt_tx_queryset(qs, dek: bytes):
    return [decrypt_transaction_fields(tx, dek) for tx in qs]

def backfill_user_transactions_to_encrypted(user, dek: bytes) -> int:
    """
    Encrypt legacy plaintext fields into *_ct/_iv for a single user.
    Returns number of rows updated.
    """
    qs = Transaction.objects.filter(owner=user, description_ct__isnull=True, dollar_amount_ct__isnull=True)
    count = 0
    for tx in qs.select_for_update():
        encrypt_transaction_fields(tx, dek)
        # Optionally null out plaintext now (or do it in a follow-up migration)
        # tx.description = None
        # tx.dollar_amount = None
        tx.save(update_fields=[
            "description_ct","description_iv",
            "dollar_amount_ct","dollar_amount_iv",
            # "description","dollar_amount",
        ])
        count += 1
    return count

def decrypt_account_fields(acct: Account, dek: bytes) -> Account:
    """
    Populate a transient .total_value (Decimal) on an Account instance
    from its encrypted fields. If missing, default to 0.
    """
    total = dec_decimal(dek, getattr(acct, "total_value_ct", None),
                             getattr(acct, "total_value_iv", None))
    acct.total_value = total if total is not None else Decimal("0")
    return acct

def decrypt_accounts(queryset, dek: bytes):
    """
    Return a list of accounts with .total_value populated (Decimal).
    """
    return [decrypt_account_fields(a, dek) for a in queryset]
