# Generated migration to rename print_cost to price_omr

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0011_contract_royalties_type_product_language_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='printrun',
            old_name='print_cost',
            new_name='price_omr',
        ),
    ]

