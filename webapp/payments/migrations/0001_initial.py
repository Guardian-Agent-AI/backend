from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.PositiveIntegerField(help_text='Amount in cents')),
                ('currency', models.CharField(default='eur', max_length=3)),
                ('description', models.CharField(max_length=255)),
                ('stripe_checkout_session_id', models.CharField(blank=True, max_length=255)),
                ('stripe_payment_intent_id', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('succeeded', 'Succeeded'),
                        ('failed', 'Failed'),
                        ('canceled', 'Canceled'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
