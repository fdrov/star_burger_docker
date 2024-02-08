# Generated by Django 3.2 on 2022-06-03 22:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0051_auto_20220604_0021'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderproduct',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ordered_items', to='foodcartapp.order', verbose_name='Номер заказа'),
        ),
        migrations.AlterField(
            model_name='orderproduct',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ordered_items', to='foodcartapp.product', verbose_name='Товар'),
        ),
    ]
