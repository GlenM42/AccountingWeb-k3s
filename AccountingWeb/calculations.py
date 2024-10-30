from datetime import timedelta
import pandas as pd
from django.db.models import Q, Sum
from django.utils import timezone
from .models import Account, Transaction


def calculate_account_balance_over_time(account_name, days=7):
    """
    Calculate the balance of the given account over the past 'days' number of days.
    Args:
        account_name (str): The name of the account.
        days (int): Number of days to look back for transactions. Default is 7.
    Returns:
        list: Dates (as strings) over the given period.
        list: Corresponding balance values for each date.
    """
    # Get the account and its current balance
    account = Account.objects.filter(account_name=account_name).first()
    if not account:
        raise ValueError(f"Account '{account_name}' not found.")

    current_balance = account.total_value
    today = timezone.now()
    start_date = today - timedelta(days=days)

    # Determine if the account is a 'debit' or 'credit' type
    is_debit_account = account.debit_or_credit == 'debit'

    # Get all transactions involving the account within the date range
    transactions = (
        Transaction.objects.filter(
            Q(debit=account_name) | Q(credit=account_name),
            transaction_date__gte=start_date
        )
        .values('transaction_date__date')  # Group by date
        .annotate(
            debit_sum=Sum('dollar_amount', filter=Q(debit=account_name)),
            credit_sum=Sum('dollar_amount', filter=Q(credit=account_name))
        )
        .order_by('-transaction_date__date')
    )
    # Initialize rolling balance and snapshots
    rolling_balance = current_balance
    balance_snapshots = []

    # "Undo" transactions in reverse order to calculate past balances
    for txn in transactions:
        date = txn['transaction_date__date']
        debit_sum = txn['debit_sum'] or 0  # Handle None values
        credit_sum = txn['credit_sum'] or 0  # Handle None values

        # Calculate the net effect of the day's transactions on the balance
        if is_debit_account:
            # For debit accounts: Subtract outflows and add inflows
            rolling_balance += credit_sum - debit_sum
        else:
            # For credit accounts: Add outflows and subtract inflows
            rolling_balance += debit_sum - credit_sum

        # Add a snapshot for this date
        balance_snapshots.append({
            'date': date,
            'balance': float(rolling_balance)
        })

    # Add a snapshot for the current balance at today's date
    balance_snapshots.append({
        'date': today.date(),
        'balance': float(current_balance)
    })

    # Convert the snapshots to a DataFrame and sort by date for plotting
    df = pd.DataFrame(balance_snapshots).sort_values(by='date')

    return df['date'].astype(str).tolist(), df['balance'].tolist()
