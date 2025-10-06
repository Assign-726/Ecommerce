from django.db import migrations

SQL_CREATE_SIZE = r'''
CREATE TABLE IF NOT EXISTS "products_size" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" varchar(20) NOT NULL UNIQUE,
    "display_name" varchar(50) NOT NULL,
    "size_type" varchar(20) NOT NULL,
    "order" integer NOT NULL DEFAULT 0,
    "is_active" bool NOT NULL DEFAULT 1
);
'''

SQL_CREATE_PRODUCTSIZE = r'''
CREATE TABLE IF NOT EXISTS "products_productsize" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "quantity" integer NOT NULL DEFAULT 0,
    "product_id" bigint NOT NULL REFERENCES "products_product" ("id") ON DELETE CASCADE,
    "size_id" bigint NOT NULL REFERENCES "products_size" ("id") ON DELETE CASCADE,
    UNIQUE ("product_id", "size_id")
);
'''

class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL(SQL_CREATE_SIZE),
        migrations.RunSQL(SQL_CREATE_PRODUCTSIZE),
    ]
