# yourapp/management/commands/encrypt_root_data.py
from getpass import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction as dbtx

from AccountingWeb.models import Account, Transaction
from AccountingWeb.utils import ensure_user_secret, unlock_user_dek
from AccountingWeb.crypto import enc_str, enc_decimal

User = get_user_model()

class Command(BaseCommand):
    help = (
        "Encrypt all plaintext fields for a given user (e.g., 'root') into the "
        "encrypted columns, without changing ownership. Idempotent. "
        "Use --scrub-plaintext after verifying decryption in the UI."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="User to encrypt (e.g., 'root').")
        parser.add_argument("--password", help="Password for that user (prompted if omitted).")
        parser.add_argument("--scrub-plaintext", action="store_true",
                            help="After encrypting, blank description and set dollar/total_value to NULL.")

    def handle(self, *args, **opts):
        username = opts["username"]
        password = opts.get("password") or getpass(f"Password for {username}: ")
        scrub = bool(opts["scrub_plaintext"])

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found")

        # Make sure user has a DEK wrapped and unlock it
        ensure_user_secret(user, password)
        dek = unlock_user_dek(user, password)

        self.stdout.write(self.style.NOTICE(
            f"Encrypting data for '{username}' (scrub={scrub})"
        ))

        with dbtx.atomic():
            # Accounts: encrypt total_value -> total_value_ct/iv
            acc_qs = Account.objects.select_for_update().filter(owner=user)
            acc_count = acc_qs.count()
            enc_acc = 0
            for acc in acc_qs:
                if acc.total_value is not None:
                    ct, iv = enc_decimal(dek, acc.total_value)
                    # only write if missing or changed (idempotent)
                    if (acc.total_value_ct != ct) or (acc.total_value_iv != iv):
                        acc.total_value_ct = ct
                        acc.total_value_iv = iv
                        enc_acc += 1
                    if scrub:
                        acc.total_value = None
                    acc.save(update_fields=["total_value_ct", "total_value_iv", "total_value"] if scrub
                                        else ["total_value_ct", "total_value_iv"])

            # Transactions: encrypt description & amount
            tx_qs = Transaction.objects.select_for_update().filter(owner=user)
            tx_count = tx_qs.count()
            enc_desc = enc_amt = 0
            for tx in tx_qs:
                # description
                if (not tx.description_ct or not tx.description_iv):
                    # we allow empty-string descriptions; encrypt that too
                    ct, iv = enc_str(dek, tx.description or '')
                    tx.description_ct = ct
                    tx.description_iv = iv
                    enc_desc += 1
                # amount
                if (tx.dollar_amount is not None) and (not tx.dollar_amount_ct or not tx.dollar_amount_iv):
                    ct, iv = enc_decimal(dek, tx.dollar_amount)
                    tx.dollar_amount_ct = ct
                    tx.dollar_amount_iv = iv
                    enc_amt += 1

                if scrub:
                    tx.description = ''      # keep empty if field is non-nullable
                    tx.dollar_amount = None

                tx.save()

        self.stdout.write(self.style.SUCCESS(
            f"Done. Accounts encrypted: {enc_acc}/{acc_count}. "
            f"Transactions encrypted: desc {enc_desc}, amount {enc_amt} (of {tx_count} rows)."
        ))

        if scrub:
            self.stdout.write(self.style.WARNING(
                "Plaintext scrubbed. Verify: login as this user, open history/accounts pages, "
                "ensure values show correctly via decryption."
            ))
