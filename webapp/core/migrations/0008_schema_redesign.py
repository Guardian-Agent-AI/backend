"""
Migration 0008 — Schema redesign for Guardian Agent v2

Summary of changes:
- Plan: adds max_children field
- UserProfile: adds stripe_customer_id + onboarded_at; drops children_count
- Child: adds date_of_birth + avatar fields
- Device: drops profile FK; makes child required; adds os + agent_version;
          renames last_seen → last_seen_at; expands device_type choices
- GameSession: adds db_index on started_at
- AlertEvent: removed (replaced by Incident)
- ChatMessage: removed (raw chat stays on-device per product spec)
- Incident: new model — severity + category + summary + reviewed_by_parent etc.
- Alert: new model — per-incident notification record (email/push/sms)
- WeeklyReport: new model — weekly digest tracking per user
"""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def _assign_child_to_devices(apps, schema_editor):
    """
    Data migration: before dropping Device.profile, make sure every device has
    a child assigned.  Devices that cannot be linked (no children exist for that
    profile) are deleted — this is acceptable in a dev environment.
    """
    Device = apps.get_model('core', 'Device')
    Child = apps.get_model('core', 'Child')

    for device in Device.objects.filter(child__isnull=True).select_related('profile'):
        first_child = Child.objects.filter(parent=device.profile).first()
        if first_child:
            device.child = first_child
            device.save(update_fields=['child'])
        else:
            device.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alertevent_child_communitypeaktimestat_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Plan ──────────────────────────────────────────────────────────────
        migrations.AddField(
            model_name='plan',
            name='max_children',
            field=models.PositiveIntegerField(default=1),
        ),

        # ── UserProfile ───────────────────────────────────────────────────────
        migrations.AddField(
            model_name='userprofile',
            name='stripe_customer_id',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='onboarded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='children_count',
        ),

        # ── Child ─────────────────────────────────────────────────────────────
        migrations.AddField(
            model_name='child',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='child',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='avatars/'),
        ),

        # ── Device – prep: drop ChatMessage first (it FKs Device + AlertEvent) ─
        migrations.DeleteModel(
            name='ChatMessage',
        ),

        # ── Device – add new fields before removing the profile FK ────────────
        migrations.AddField(
            model_name='device',
            name='os',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='device',
            name='agent_version',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.RenameField(
            model_name='device',
            old_name='last_seen',
            new_name='last_seen_at',
        ),
        migrations.AlterField(
            model_name='device',
            name='device_type',
            field=models.CharField(
                choices=[
                    ('pc',      'PC'),
                    ('console', 'Console'),
                    ('tablet',  'Tablet'),
                    ('phone',   'Phone'),
                    ('other',   'Other'),
                ],
                default='pc',
                max_length=20,
            ),
        ),

        # ── Device – data migration then schema change ─────────────────────────
        migrations.RunPython(_assign_child_to_devices, migrations.RunPython.noop),

        # Make child required (NOT NULL) now that every row has a child
        migrations.AlterField(
            model_name='device',
            name='child',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='devices',
                to='core.child',
            ),
        ),

        # Drop the old profile FK (now redundant — reach parent via child.parent)
        migrations.RemoveField(
            model_name='device',
            name='profile',
        ),

        # ── GameSession – index on started_at ────────────────────────────────
        migrations.AlterField(
            model_name='gamesession',
            name='started_at',
            field=models.DateTimeField(db_index=True),
        ),

        # ── AlertEvent – remove ───────────────────────────────────────────────
        migrations.DeleteModel(
            name='AlertEvent',
        ),

        # ── Incident – new model ──────────────────────────────────────────────
        migrations.CreateModel(
            name='Incident',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('severity', models.CharField(
                    choices=[
                        ('low',      'Low'),
                        ('medium',   'Medium'),
                        ('high',     'High'),
                        ('critical', 'Critical'),
                    ],
                    default='medium',
                    max_length=20,
                )),
                ('category', models.CharField(
                    choices=[
                        ('meeting_request',           'Meeting Request'),
                        ('personal_info_request',     'Personal Info Request'),
                        ('social_media_solicitation', 'Social Media Solicitation'),
                        ('photo_video_request',       'Photo/Video Request'),
                        ('grooming_language',         'Grooming Language'),
                        ('secrecy_request',           'Secrecy Request'),
                        ('threats_bullying',          'Threats / Bullying'),
                        ('gift_bribery',              'Gift / Bribery'),
                        ('other',                     'Other'),
                    ],
                    default='other',
                    max_length=50,
                )),
                ('category_label', models.CharField(blank=True, max_length=200)),
                ('summary', models.TextField()),
                ('raw_context', models.TextField(blank=True)),
                ('game_name', models.CharField(max_length=200)),
                ('detected_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('reviewed_by_parent', models.BooleanField(default=False)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('is_false_positive', models.BooleanField(default=False)),
                ('child', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='incidents',
                    to='core.child',
                )),
                ('device', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='incidents',
                    to='core.device',
                )),
                ('session', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='incidents',
                    to='core.gamesession',
                )),
            ],
            options={
                'ordering': ['-detected_at'],
            },
        ),

        # ── Alert – new model ─────────────────────────────────────────────────
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alert_type', models.CharField(
                    choices=[('email', 'Email'), ('push', 'Push'), ('sms', 'SMS')],
                    default='email',
                    max_length=20,
                )),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed')],
                    default='pending',
                    max_length=20,
                )),
                ('message_preview', models.TextField(blank=True)),
                ('incident', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='alerts',
                    to='core.incident',
                )),
            ],
        ),

        # ── WeeklyReport – new model ──────────────────────────────────────────
        migrations.CreateModel(
            name='WeeklyReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_start', models.DateField()),
                ('week_end', models.DateField()),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('email_status', models.CharField(
                    choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed')],
                    default='pending',
                    max_length=20,
                )),
                ('report_data', models.JSONField(default=dict)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='weekly_reports',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-week_start'],
            },
        ),

        # ── CommunityThreatStat – update choices reference ────────────────────
        migrations.AlterField(
            model_name='communitythreatstat',
            name='category',
            field=models.CharField(
                choices=[
                    ('meeting_request',           'Meeting Request'),
                    ('personal_info_request',     'Personal Info Request'),
                    ('social_media_solicitation', 'Social Media Solicitation'),
                    ('photo_video_request',       'Photo/Video Request'),
                    ('grooming_language',         'Grooming Language'),
                    ('secrecy_request',           'Secrecy Request'),
                    ('threats_bullying',          'Threats / Bullying'),
                    ('gift_bribery',              'Gift / Bribery'),
                    ('other',                     'Other'),
                ],
                max_length=50,
                unique=True,
            ),
        ),
    ]
