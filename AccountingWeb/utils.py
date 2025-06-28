from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from django.db.models import Sum
from AccountingWeb.models import Account, Transaction

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


def snapshot_details():
    """Return revenue_details, expense_details from Account.total_value."""
    revenue = list(
        Account.objects.filter(account_type="revenue")
               .order_by("-total_value")
               .values("account_name", "total_value")
    )
    expense = list(
        Account.objects.filter(account_type="expense")
               .order_by("-total_value")
               .values("account_name", "total_value")
    )
    return revenue, expense


def ledger_details(start_date, end_date):
    """
    Summarise revenue / expense movements **inside** the window.
    • Skips assets, liabilities, equity.
    • Flags orphaned accounts with is_deleted=True (for red rows).
    """
    # 1. Gather movements
    rows = (Transaction.objects
            .filter(transaction_date__date__range=(start_date, end_date))
            .values("debit", "credit")
            .annotate(amount=Sum("dollar_amount")))

    book = defaultdict(lambda: {"debit": Decimal("0"), "credit": Decimal("0")})
    for r in rows:
        book[r["debit"]]["debit"]   += r["amount"]
        book[r["credit"]]["credit"] += r["amount"]

    acc_meta = {a.account_name: a.account_type for a in Account.objects.all()}
    acc_meta.update(ORPHAN_META)

    live_names = set(acc_meta) - set(ORPHAN_META)
    revenue, expense = [], []

    # 2. Classify each name
    for name, sides in book.items():
        net = sides["credit"] - sides["debit"]

        acct_type = acc_meta.get(name)
        is_deleted = name not in live_names

        # live accounts
        if acct_type == "revenue":
            revenue.append({"account_name": name, "total_value": net, "is_deleted": is_deleted})
        elif acct_type == "expense":
            expense.append({"account_name": name, "total_value": -net, "is_deleted": is_deleted})
        # skip everything else (assets / liabilities / equity)

    revenue.sort(key=lambda d: d["total_value"], reverse=True)
    expense.sort(key=lambda d: d["total_value"], reverse=True)
    return revenue, expense