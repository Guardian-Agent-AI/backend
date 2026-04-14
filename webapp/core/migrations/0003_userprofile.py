import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0002_seed_plans'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Subscriber',
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(
                    max_length=17,
                    validators=[django.core.validators.RegexValidator(
                        regex=r'^\+?1?\d{9,15}$',
                        message='Enter a valid phone number (e.g. +1234567890).',
                    )],
                )),
                ('children_count', models.PositiveIntegerField(default=1)),
                ('signed_up_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('plan', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='core.plan',
                )),
            ],
        ),
    ]
