# Generated migration to rename type field to customer_type

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0002_listitem_created_by_listitem_updated_by_and_more'),
        ('sales', '0002_invoice_composite_id_invoice_global_discount_percent_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='customer',
            old_name='type',
            new_name='customer_type',
        ),
        migrations.AlterField(
            model_name='customer',
            name='customer_type',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'list_type__code': 'customer_type'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='customers',
                to='common.listitem'
            ),
        ),
    ]

