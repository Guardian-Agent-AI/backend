from django.db import migrations


def update_plans(apps, schema_editor):
    Plan = apps.get_model('core', 'Plan')

    # Delete all existing plans
    Plan.objects.all().delete()

    # Free plan
    Plan.objects.create(
        name='Free',
        price_monthly=0.00,
        max_devices=1,
        max_children=1,
        description='Try Guardian Agent at no cost.',
        features='1 hour monitoring per day\nVoice chat monitoring\nText chat analysis\nAll games supported\nDashboard alerts only',
        is_active=True,
    )
    # Basic plan
    Plan.objects.create(
        name='Basic',
        price_monthly=5.00,
        max_devices=1,
        max_children=1,
        description='Full protection for one device.',
        features='Unlimited monitoring\nVoice chat monitoring\nText chat analysis\nAll games supported\nAlerts to 1 phone number\n1 device',
        is_active=True,
    )
    # Family plan
    Plan.objects.create(
        name='Family',
        price_monthly=7.50,
        max_devices=4,
        max_children=4,
        description='Protect the whole family.',
        features='Unlimited monitoring\nVoice chat monitoring\nText chat analysis\nAll games supported\nAlerts to 2 phone numbers\nUp to 4 devices',
        is_active=True,
    )


def revert_plans(apps, schema_editor):
    Plan = apps.get_model('core', 'Plan')
    Plan.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_alter_userprofile_phone_number'),
    ]

    operations = [
        migrations.RunPython(update_plans, revert_plans),
    ]
