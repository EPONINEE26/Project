from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('market', '0008_transferlisting_address_detail')]

    operations = [
        migrations.AlterField(
            model_name='commercialarea',
            name='effective_on',
            field=models.DateField('기준일', null=True, blank=True),
        ),
    ]
