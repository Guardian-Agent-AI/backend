"""
Management command: seed_mock_data
-----------------------------------
Creates realistic mock children, game sessions, incidents, and system-wide
community stats for the first superuser (or a specified email).

Usage:
    python manage.py seed_mock_data
    python manage.py seed_mock_data --email parent@example.com
    python manage.py seed_mock_data --clear   # wipe existing mock data first

This script is intentionally idempotent — safe to run multiple times.
"""
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import (
    Child, CommunityPeakTimeStat, CommunityThreatStat,
    GameSession, Incident, UserProfile,
)

GAMES = [
    "Fortnite", "Roblox", "Minecraft", "Valorant", "FIFA 25",
    "Rocket League", "Among Us", "Call of Duty: Warzone",
]

INCIDENT_TEMPLATES = [
    dict(
        category="social_media_solicitation",
        severity="medium",
        game_name="Roblox",
        summary=(
            "Guardian Alert: A social media solicitation was detected on Roblox. "
            "Another player asked Emma to add them on Snapchat. "
            "They are attempting to move the conversation off-platform."
        ),
        days_ago=1.5,
    ),
    dict(
        category="personal_info_request",
        severity="medium",
        game_name="Minecraft",
        summary=(
            "Guardian Alert: A personal information request was detected on Minecraft. "
            "A player asked 'what school do you go to?' "
            "Personal details were directly solicited."
        ),
        days_ago=4.0,
    ),
    dict(
        category="meeting_request",
        severity="high",
        game_name="Fortnite",
        summary=(
            "Guardian Alert: A meeting request was detected in your child's chat on Fortnite. "
            "Another player suggested 'we should hang out sometime.' "
            "An in-person meetup was proposed."
        ),
        days_ago=6.5,
    ),
]

THREAT_STAT_DATA = [
    ("social_media_solicitation", 312),
    ("personal_info_request",     247),
    ("meeting_request",           189),
    ("grooming_language",         143),
    ("secrecy_request",            98),
    ("photo_video_request",        76),
    ("threats_bullying",           54),
    ("gift_bribery",               38),
    ("other",                      22),
]

PEAK_TIME_DATA = [
    (0,   14),
    (3,    6),
    (6,   19),
    (9,   48),
    (12,  93),
    (15, 178),
    (18, 294),
    (21, 251),
]

SESSION_PLANS = [
    ("Fortnite",      0.3,  45),
    ("Fortnite",      0.5,  30),
    ("Roblox",        1.0,  60),
    ("Minecraft",     1.5,  90),
    ("Valorant",      2.2,  50),
    ("Fortnite",      2.8,  40),
    ("Roblox",        3.1,  75),
    ("FIFA 25",       3.6,  35),
    ("Fortnite",      4.0,  55),
    ("Minecraft",     4.5,  80),
    ("Rocket League", 5.0,  45),
    ("Valorant",      5.5,  60),
    ("Fortnite",      6.0,  30),
    ("Roblox",        6.5,  90),
]


class Command(BaseCommand):
    help = "Seed mock children, sessions, incidents, and community stats for dashboard preview."

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, help="Target user email (defaults to first superuser)")
        parser.add_argument("--clear", action="store_true", help="Remove existing mock data before seeding")

    def handle(self, *args, **options):
        now = timezone.now()

        email = options.get("email")
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise CommandError(f"No user with email '{email}'.")
        else:
            user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            if not user:
                raise CommandError("No users found. Create a user first.")

        profile, _ = UserProfile.objects.get_or_create(user=user)
        self.stdout.write(f"Seeding data for: {user.email}")

        if options["clear"]:
            profile.children.all().delete()
            CommunityThreatStat.objects.all().delete()
            CommunityPeakTimeStat.objects.all().delete()
            self.stdout.write("  Cleared existing mock data.")

        emma, _ = Child.objects.get_or_create(parent=profile, name="Emma", defaults={"age": 11})
        noah, _ = Child.objects.get_or_create(parent=profile, name="Noah",  defaults={"age": 14})
        self.stdout.write(f"  Children: Emma ({emma.id}), Noah ({noah.id})")

        created_sessions = 0
        for game, days_ago, minutes in SESSION_PLANS:
            started = now - timedelta(days=days_ago) - timedelta(minutes=random.randint(0, 30))
            ended   = started + timedelta(minutes=minutes)
            GameSession.objects.get_or_create(
                child=emma,
                game_name=game,
                started_at=started,
                defaults={"ended_at": ended},
            )
            created_sessions += 1

        for game, days_ago, minutes in SESSION_PLANS[:6]:
            started = now - timedelta(days=days_ago + 0.2) - timedelta(minutes=random.randint(0, 20))
            ended   = started + timedelta(minutes=minutes + random.randint(-10, 20))
            GameSession.objects.get_or_create(
                child=noah,
                game_name=game,
                started_at=started,
                defaults={"ended_at": ended},
            )
        self.stdout.write(f"  Sessions created: {created_sessions}+")

        created_incidents = 0
        for tpl in INCIDENT_TEMPLATES:
            ts = now - timedelta(days=tpl["days_ago"])
            Incident.objects.get_or_create(
                child=emma,
                category=tpl["category"],
                game_name=tpl["game_name"],
                detected_at=ts,
                defaults={
                    "severity": tpl["severity"],
                    "summary": tpl["summary"],
                },
            )
            created_incidents += 1

        Incident.objects.get_or_create(
            child=noah,
            category="social_media_solicitation",
            game_name="Valorant",
            detected_at=now - timedelta(days=2),
            defaults={
                "severity": "medium",
                "summary": (
                    "Guardian Alert: A social media solicitation was detected on Valorant. "
                    "A player asked Noah to add them on Discord. "
                    "They are attempting to move the conversation off-platform."
                ),
            },
        )
        self.stdout.write(f"  Incidents created: {created_incidents}+")

        for category, count in THREAT_STAT_DATA:
            CommunityThreatStat.objects.update_or_create(
                category=category, defaults={"count": count},
            )
        self.stdout.write(f"  CommunityThreatStat seeded: {len(THREAT_STAT_DATA)} categories")

        for hour_start, count in PEAK_TIME_DATA:
            CommunityPeakTimeStat.objects.update_or_create(
                hour_start=hour_start, defaults={"count": count},
            )
        self.stdout.write(f"  CommunityPeakTimeStat seeded: {len(PEAK_TIME_DATA)} time slots")

        self.stdout.write(self.style.SUCCESS("Done! Visit /dashboard/ to preview."))
