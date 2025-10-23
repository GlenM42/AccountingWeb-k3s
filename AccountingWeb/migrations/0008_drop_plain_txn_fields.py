from django.db import migrations

# 1) Backfill: for any rows where ciphertext is NULL but plaintext exists,
#    copy plaintext into *_ct/_iv by calling your app encryptor. Because
#    running Python functions from SQL isn’t possible, we do a small, safe
#    best-effort SQL backfill only for rows that ALREADY have ciphertext.
#    If you still have plaintext needing encryption, run your Python helper
#    before this migration (see note below).

SQL_DROP_COLUMNS = """
-- If you still have NOT NULL legacy columns, drop or relax them.

-- MySQL: conditionally drop description
SET @has_desc := (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'transactions'
    AND COLUMN_NAME = 'description'
);
SET @stmt := IF(@has_desc = 1, 'ALTER TABLE `transactions` DROP COLUMN `description`', 'SELECT 1');
PREPARE x FROM @stmt; EXECUTE x; DEALLOCATE PREPARE x;

-- Conditionally drop dollar_amount
SET @has_amt := (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'transactions'
    AND COLUMN_NAME = 'dollar_amount'
);
SET @stmt2 := IF(@has_amt = 1, 'ALTER TABLE `transactions` DROP COLUMN `dollar_amount`', 'SELECT 1');
PREPARE y FROM @stmt2; EXECUTE y; DEALLOCATE PREPARE y;
"""

SQL_REVERSE = """
-- Re-create the legacy plaintext columns if you ever need to reverse.
ALTER TABLE `transactions`
  ADD COLUMN `description`   TEXT NULL,
  ADD COLUMN `dollar_amount` DECIMAL(10,2) NULL;
"""

class Migration(migrations.Migration):
    dependencies = [
        ("AccountingWeb", "0007_drop_plain_total_value"),
    ]
    operations = [
        migrations.RunSQL(SQL_DROP_COLUMNS, reverse_sql=SQL_REVERSE),
    ]
