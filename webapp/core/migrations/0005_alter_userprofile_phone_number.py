from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_update_plans'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='phone_number',
            field=models.CharField(
                blank=True,
                default='',
                max_length=17,
                validators=[django.core.validators.RegexValidator(
                    message='Enter a valid phone number (e.g. +1234567890).',
                    regex='^\\+?1?\\d{9,15}$',
                )],
            ),
        ),
    ]
