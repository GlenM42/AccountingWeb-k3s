# AccountingWeb/migrations/00xx_drop_plain_total_value.py
from django.db import migrations

SQL_DROP = """
SET @exists := (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'accounts'
    AND COLUMN_NAME = 'total_value'
);
SET @stmt := IF(@exists = 1, 'ALTER TABLE `accounts` DROP COLUMN `total_value`', 'SELECT 1');
PREPARE x FROM @stmt; EXECUTE x; DEALLOCATE PREPARE x;
"""

SQL_REVERSE = """
ALTER TABLE `accounts` ADD COLUMN `total_value` DECIMAL(10,2) NOT NULL DEFAULT 0;
"""

class Migration(migrations.Migration):
    dependencies = [
        ('AccountingWeb', '0006_account_total_value_ct_account_total_value_iv_and_more'),
    ]
    operations = [
        migrations.RunSQL(SQL_DROP, reverse_sql=SQL_REVERSE),
    ]
