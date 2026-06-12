"""
Management command to purge expired/used OTP records.

Run periodically (e.g., daily via cron) to prevent table bloat:
    python manage.py cleanup_otps
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import EmailOTP


class Command(BaseCommand):
    help = 'Delete expired and used OTP records older than the retention period.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete OTPs older than this many days (default: 7)',
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options['days'])
        deleted_count, _ = EmailOTP.objects.filter(
            created_at__lt=cutoff,
        ).delete()
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {deleted_count} expired OTP record(s).')
        )
