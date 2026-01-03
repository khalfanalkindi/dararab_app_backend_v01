# Generated migration to add price and price_omr fields to Product model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0012_rename_print_cost_to_price_omr'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Price ($)'),
        ),
        migrations.AddField(
            model_name='product',
            name='price_omr',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Price (OMR)'),
        ),
    ]

