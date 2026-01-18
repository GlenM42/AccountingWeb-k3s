# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AccountingWeb is a Django-based double-entry bookkeeping system with transparent encryption. Users can track revenue, expenses, assets, liabilities, and equity through a web interface. All sensitive financial data (amounts, descriptions, account balances) is encrypted at rest using AES-256-GCM.

**Key Technologies:**
- Django 5.0.3 on Python 3.12
- MySQL (production)
- uv for dependency management
- Docker + K8s for deployment
- Argon2id for password derivation, AES-GCM for field-level encryption

## Development Commands

### Local Development

```bash
# Install dependencies
uv sync

# Run migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Start development server
uv run python manage.py runserver

# Collect static files
uv run python manage.py collectstatic

# Django shell
uv run python manage.py shell
```

### Docker

```bash
# Build image
docker build -t accountingweb:local .

# Run container (requires environment variables)
docker run --rm \
  --name accountingweb \
  -p 127.0.0.1:8000:8000 \
  -e DB_ENGINE=django.db.backends.sqlite3 \
  -e DB_NAME=db.sqlite3 \
  -e SECRET_KEY=your-secret-key \
  -e DEBUG=True \
  accountingweb:local

# Docker Compose (recommended)
docker compose up -d
```

### Custom Management Commands

```bash
# Migrate existing user data from plaintext to encrypted fields
uv run python manage.py migrate_root_data --username <username> [--password <password>] [--scrub-plaintext]
```

## Architecture

### Data Model

**Three core models with user-scoped isolation:**

1. **UserSecret** (1:1 with User)
   - Stores wrapped DEK (Data Encryption Key) using KEK derived from password
   - Fields: `salt_b64`, `dek_wrapped_b64`, `dek_iv_b64`, `kdf` (argon2id)

2. **Account**
   - Chart of accounts (assets, liabilities, equity, revenue, expense)
   - Fields: `account_name`, `account_type`, `debit_or_credit`
   - Encrypted: `total_value_ct` (current balance), `total_value_iv`
   - All accounts scoped by `owner` FK

3. **Transaction**
   - Double-entry bookkeeping records (debit + credit)
   - Fields: `transaction_date`, `debit`, `credit` (account names as strings)
   - Encrypted: `description_ct`, `dollar_amount_ct`, and their IVs
   - All transactions scoped by `owner` FK

**Important:** Account names in transactions are stored as strings (denormalized), not FKs.

### Encryption System

**Located in:** [AccountingWeb/crypto.py](AccountingWeb/crypto.py)

**Key hierarchy:**
1. User password → KEK (Key Encryption Key) via Argon2id
2. KEK wraps DEK (Data Encryption Key, random 256-bit)
3. DEK encrypts all financial data (AES-256-GCM)
4. DEK cached in Django session after login (`request.session['dek_b64']`)

**Field encryption helpers:**
- `enc_str(dek, plaintext)` → `(ciphertext_b64, iv_b64)`
- `dec_str(dek, ct_b64, iv_b64)` → plaintext string
- `enc_decimal(dek, value)` / `dec_decimal(dek, ct_b64, iv_b64)` for amounts

**Session management:**
- `unlock_user_dek(user, password)` derives KEK and unwraps DEK
- `@require_unlocked` decorator checks for cached DEK in session
- Sessions expire on browser close

### URL Structure

| Route | View | Purpose |
|---|---|---|
| `/` | `home_view` | Landing page |
| `/login/` | `UnlockingLoginView` | Custom login that unwraps DEK |
| `/balance_sheet/` | `balance_sheet_view` | Assets/Liabilities/Equity display |
| `/income_statement/` | `income_statement_view` | Revenue/Expenses with date ranges |
| `/transaction_history/` | `transaction_history_view` | Paginated transaction list |
| `/new_transaction/` | `new_transaction_view` | Form to create transactions |
| `/summary/` | `summary_view` | Account balance charts |
| `/summary/get-graph-data/` | `get_graph_data` | AJAX endpoint for chart data |
| `/me/unlock/` | `unlock_data` | POST endpoint for session DEK unlock |

### Financial Calculations

**Located in:** [AccountingWeb/calculations.py](AccountingWeb/calculations.py) and [AccountingWeb/utils.py](AccountingWeb/utils.py)

**Income Statement logic:**
- Pre-CUTOFF date (2023-11-26): Uses `snapshot_details()` (legacy account balance snapshot)
- Post-CUTOFF: Uses `ledger_details()` (transaction-based revenue/expense aggregation)
- Both methods filter by date range and decrypt amounts

**Balance reconstruction:**
- `calculate_account_balance_over_time(account_name, user, days, dek)` in calculations.py
- Queries all transactions affecting account over past N days
- Reconstructs rolling balance by chronologically reversing transactions
- Returns (dates, values) for Chart.js rendering

### Django Admin

**Located in:** [AccountingWeb/admin.py](AccountingWeb/admin.py)

**OwnerScopedMixin:**
- Custom mixin enforcing user-level data isolation
- Scopes all querysets to `owner=request.user`
- Even superusers only see their own financial data

**Admin classes:**
- `AccountAdmin`: Manage accounts (encrypted fields read-only)
- `TransactionAdmin`: Manage transactions (encrypted fields read-only)
- `UserSecretAdmin`: View user encryption metadata

### Templates & Static Files

**Templates:** [templates/](templates/)
- Uses HTML5 UP Stellar theme (responsive, jQuery-based)
- Template inheritance from base layouts
- Django humanize filters for number formatting (`intcomma`, `floatformat`)

**Key templates:**
- `balance_sheet.html`: Three-column layout (assets/liabilities/equity)
- `income_statement.html`: Revenue/expense breakdown with date picker
- `summary.html`: Interactive Chart.js graphs with day-range slider
- `new_transaction.html`: Transaction entry form

**Static files:** [static/html5up-stellar/](static/html5up-stellar/)
- CSS/JS assets from HTML5 UP theme
- Images, icons, favicon
- Chart.js loaded from CDN in summary.html

## Important Patterns

### Creating Transactions

When creating transactions in code:
1. Retrieve both debit and credit Account objects
2. Decrypt current balances using DEK
3. Calculate new balances (debit += amount, credit += amount)
4. Encrypt new balances and transaction fields
5. Save transaction and update both accounts atomically
6. See [AccountingWeb/views.py:312-390](AccountingWeb/views.py#L312-L390) for reference implementation

### Accessing Encrypted Data

Always check for DEK in session:
```python
if 'dek_b64' not in request.session:
    return redirect('unlock_data')

dek = base64.b64decode(request.session['dek_b64'])
```

Use helper functions from crypto.py:
```python
from AccountingWeb.crypto import dec_str, dec_decimal

description = dec_str(dek, obj.description_ct, obj.description_iv)
amount = dec_decimal(dek, obj.dollar_amount_ct, obj.dollar_amount_iv)
```

### Multi-Tenant Isolation

All queries must filter by owner:
```python
accounts = Account.objects.filter(owner=request.user)
transactions = Transaction.objects.filter(owner=request.user)
```

Django admin enforces this via `OwnerScopedMixin`.

## Environment Variables

Required for production:
- `DB_ENGINE`: e.g., `django.db.backends.mysql`
- `DB_NAME`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`
- `SECRET_KEY`: Django secret key
- `DEBUG`: `True` or `False`

Optional:
- `CSRF_TRUSTED_ORIGINS`: Comma-separated list for HTTPS behind proxy

## Deployment

**Docker entrypoint:** [entrypoint.sh](entrypoint.sh)
1. Runs migrations (`python manage.py migrate --no-input`)
2. Collects static files (`python manage.py collectstatic --no-input`)
3. Starts gunicorn with 4 workers on port 8000

**Kubernetes manifests:** [k8s/](k8s/)
- `03-secret.yml`: Django secrets (base64 encoded)
- `10-deployment.yaml`: Main deployment with resource limits
- `20-django-service.yaml`: ClusterIP service
- `30-django-ingress.yaml`: Ingress configuration

## Testing

No automated tests currently exist. Manual testing workflow:
1. Create test user via Django admin
2. Log in to unwrap DEK
3. Create accounts via admin or UI
4. Create transactions via `/new_transaction/`
5. Verify balance sheet, income statement, and transaction history
6. Test encryption by inspecting database (should see base64 ciphertext)

## Security Considerations

- Never commit `.env` files or credentials
- DEK is cached in session; cleared on logout
- Argon2id parameters: time_cost=2, memory_cost=102400, parallelism=8
- All sensitive fields encrypted with AES-256-GCM (authenticated encryption)
- Session cookies configured for HTTPS-only in production
- Admin interface restricts users to their own data only
