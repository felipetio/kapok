"""Management command to create INSTITUTIONAL users."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import IndigenousUser, Land


class Command(BaseCommand):
    help = "Create INSTITUTIONAL tier user for organization leaders"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Username for the new user")
        parser.add_argument("email", type=str, help="Email for the new user")
        parser.add_argument("full_name", type=str, help="Full name of the user")
        parser.add_argument("land_id", type=str, help="UUID of the Land")
        parser.add_argument("--phone", type=str, default="", help="Phone number (optional)")
        parser.add_argument("--password", type=str, default=None, help="Password (will prompt if not provided)")

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        full_name = options["full_name"]
        land_id = options["land_id"]
        phone = options.get("phone", "")
        password = options.get("password")

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f"User with username '{username}' already exists.")

        # Validate land exists
        try:
            land = Land.objects.get(id=land_id)
        except Land.DoesNotExist:
            raise CommandError(f"Land with ID '{land_id}' does not exist.")

        # Prompt for password if not provided
        if not password:
            password = input(f"Enter password for {username}: ")
            if not password:
                raise CommandError("Password cannot be empty.")

        # Create User
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        # Create IndigenousUser with INSTITUTIONAL tier
        indigenous_user = IndigenousUser.objects.create(
            user=user,
            land=land,
            full_name=full_name,
            phone=phone,
            verification_tier="INSTITUTIONAL",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created INSTITUTIONAL user: {indigenous_user.full_name} "
                f"({username}) for land '{land.name}'"
            )
        )
