from django.db import migrations


def update_plans(apps, schema_editor):
    Plan = apps.get_model('core', 'Plan')

    Plan.objects.filter(name='Starter').update(price_monthly=25.00)
    Plan.objects.filter(name='Family').update(price_monthly=50.00)
    Plan.objects.filter(name='Premium').update(
        name='Ultra',
        price_monthly=100.00,
        description='Maximum protection, unlimited access.',
    )


def revert_plans(apps, schema_editor):
    Plan = apps.get_model('core', 'Plan')

    Plan.objects.filter(name='Starter').update(price_monthly=9.99)
    Plan.objects.filter(name='Family').update(price_monthly=19.99)
    Plan.objects.filter(name='Ultra').update(
        name='Premium',
        price_monthly=29.99,
        description='Maximum protection, unlimited access.',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_userprofile'),
    ]

    operations = [
        migrations.RunPython(update_plans, revert_plans),
    ]
