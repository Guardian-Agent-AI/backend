from django.db import migrations


def create_plans(apps, schema_editor):
    Plan = apps.get_model('core', 'Plan')

    Plan.objects.create(
        name='Starter',
        price_monthly=9.99,
        max_devices=1,
        max_children=1,
        description='Essential protection for one child.',
        features='Real-time voice monitoring\nText chat analysis\nInstant parent alerts\nBasic threat reports',
        is_active=True,
    )
    Plan.objects.create(
        name='Family',
        price_monthly=19.99,
        max_devices=3,
        max_children=4,
        description='Full protection for the whole family.',
        features='Everything in Starter\nAI-powered context analysis\nCustom safety rules by age\nWeekly safety summary\nPriority email support',
        is_active=True,
    )
    Plan.objects.create(
        name='Premium',
        price_monthly=29.99,
        max_devices=99,
        max_children=99,
        description='Maximum protection, unlimited access.',
        features='Everything in Family\n24/7 priority support\nDetailed weekly reports\nUnlimited devices\nUnlimited child profiles\nEarly access to new features',
        is_active=True,
    )


def remove_plans(apps, schema_editor):
    Plan = apps.get_model('core', 'Plan')
    Plan.objects.filter(name__in=['Starter', 'Family', 'Premium']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_plans, remove_plans),
    ]
