import json
from datetime import datetime
from urllib.request import urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from django.utils.timezone import is_naive, make_aware, now

from app.models import Community, Country, Land, Municipality, State


class Command(BaseCommand):
    help = "Load ISA (Instituto Socioambiental) indigenous lands data from JSON file or URL"

    """
    Load ISA (Instituto Socioambiental) indigenous lands data from JSON.

    USAGE:
        Download from ISA (default):
            python manage.py load_isa_data

        Import from local file:
            python manage.py load_isa_data sample_isa_data.json

        Dry run (test without saving):
            python manage.py load_isa_data --dry-run

        Update existing records:
            python manage.py load_isa_data --update

    DATA TRANSFORMATION:
        Land fields:
            - id → source_id (stored as string)
            - nome_ti → name
            - categoria → category
            - data_alteracao → source_updated_at
            - Complete JSON → source_raw_data
            - Hardcoded → source_name = "ISA"

        Municipality:
            - nome_municipio → name
            - uf → state.code
            - Creates State records automatically if they don't exist

        Community (Povo):
            - povo → name
            - Auto-generates slug from name

    EXPECTED JSON STRUCTURE:
        Format 1 (wrapped): {"content": {"info_geral": [...]}}
        Format 2 (direct): [{"id": 4184, "nome_ti": "...", ...}]

    NOTES:
        - Brazil country is created automatically if it doesn't exist
        - States are created automatically but may need country linkage
        - Duplicate municipalities are handled via unique_together constraint
        - Use --dry-run to test imports before committing to database
    """

    ISA_DATA_URL = "https://mapa.eco.br/data/sisarp/v1/tis.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            type=str,
            nargs="?",
            default=None,
            help="Path to the JSON file containing ISA data (optional, defaults to downloading from ISA)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without saving to database",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing records based on source_id",
        )

    def handle(self, *args, **options):
        json_file = options["json_file"]
        dry_run = options["dry_run"]
        update_existing = options["update"]

        # Load data from file or URL
        if json_file:
            self.stdout.write(f"Loading data from file: {json_file}")
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                raise CommandError(f"File not found: {json_file}")
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON file: {e}")
        else:
            self.stdout.write(f"Downloading data from: {self.ISA_DATA_URL}")
            try:
                with urlopen(self.ISA_DATA_URL) as response:
                    data = json.loads(response.read().decode("utf-8"))
            except Exception as e:
                raise CommandError(f"Failed to download data from URL: {e}")

        # Extract the info_geral array from the content
        if isinstance(data, dict) and "content" in data:
            if "info_geral" in data["content"]:
                lands_data = data["content"]["info_geral"]
            else:
                lands_data = data["content"]
        elif isinstance(data, list):
            lands_data = data
        else:
            raise CommandError("Unexpected JSON structure. Expected 'content.info_geral' array or a list.")

        self.stdout.write(f"Found {len(lands_data)} land records to process")

        stats = {
            "lands_created": 0,
            "lands_updated": 0,
            "lands_skipped": 0,
            "municipalities_created": 0,
            "communities_created": 0,
        }

        with transaction.atomic():
            # Ensure Brazil country exists (inside transaction for dry-run support)
            self.ensure_brazil_exists()

            for land_data in lands_data:
                try:
                    result = self.process_land(land_data, update_existing, dry_run)
                    stats["lands_created"] += result["land_created"]
                    stats["lands_updated"] += result["land_updated"]
                    stats["lands_skipped"] += result["land_skipped"]
                    stats["municipalities_created"] += result["municipalities_created"]
                    stats["communities_created"] += result["communities_created"]
                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(f"Error processing land '{land_data.get('nome_ti', 'unknown')}': {e}")
                    )
                    continue

            if dry_run:
                self.stdout.write(self.style.WARNING("\n=== DRY RUN - No changes saved ==="))
                transaction.set_rollback(True)

        # Print statistics
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Import completed!"))
        self.stdout.write(f"Lands created: {stats['lands_created']}")
        self.stdout.write(f"Lands updated: {stats['lands_updated']}")
        self.stdout.write(f"Lands skipped: {stats['lands_skipped']}")
        self.stdout.write(f"Municipalities created: {stats['municipalities_created']}")
        self.stdout.write(f"Communities created: {stats['communities_created']}")

    def ensure_brazil_exists(self):
        """Ensure Brazil country exists in the database"""
        brazil, created = Country.objects.get_or_create(code="BR", defaults={"name": "Brazil"})
        if created:
            self.stdout.write(self.style.SUCCESS("Created Brazil country record"))
        return brazil

    def process_land(self, land_data, update_existing, dry_run):
        """Process a single land record and related data"""
        result = {
            "land_created": 0,
            "land_updated": 0,
            "land_skipped": 0,
            "municipalities_created": 0,
            "communities_created": 0,
        }

        land_id = land_data.get("id")
        land_name = land_data.get("nome_ti")

        if not land_id or not land_name:
            self.stdout.write(self.style.WARNING("Skipping land with missing ID or name"))
            result["land_skipped"] = 1
            return result

        source_id = str(land_id)

        # Check if land already exists (always check to avoid duplicates)
        existing_land = Land.objects.filter(source_id=source_id, source_name="ISA").first()

        if existing_land and not update_existing:
            self.stdout.write(self.style.WARNING(f"Skipping existing land: {land_name} (use --update to update)"))
            result["land_skipped"] = 1
            return result

        # Process municipality
        municipality = None
        if land_data.get("municipio") and len(land_data["municipio"]) > 0:
            # Use the first municipality in the list
            muni_data = land_data["municipio"][0]
            municipality, created = self.get_or_create_municipality(muni_data)
            if created:
                result["municipalities_created"] = 1

        # Process communities (povos)
        communities = []
        if land_data.get("povo") and land_data["povo"].get("data"):
            for povo_data in land_data["povo"]["data"]:
                community, created = self.get_or_create_community(povo_data)
                communities.append(community)
                if created:
                    result["communities_created"] += 1

        # Transform and prepare land data
        land_fields = {
            "name": land_name,
            "category": land_data.get("categoria", "TI"),
            "municipality": municipality,
            "source_id": source_id,
            "source_name": "ISA",
            "source_updated_at": self.parse_datetime(land_data.get("data_alteracao")),
            "source_last_synced_at": now(),
            "source_raw_data": land_data,
        }

        # Create or update land
        if existing_land:
            for key, value in land_fields.items():
                setattr(existing_land, key, value)
            existing_land.save()
            land = existing_land
            result["land_updated"] = 1
            action = "Updated"
        else:
            land = Land.objects.create(**land_fields)
            result["land_created"] = 1
            action = "Created"

        # Set communities relationship
        if communities:
            land.communities.set(communities)

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"{action} land: {land_name} (ID: {source_id})"))

        return result

    def get_or_create_municipality(self, muni_data):
        """Get or create a municipality from ISA data"""
        muni_name = muni_data.get("nome_municipio")
        state_code = muni_data.get("uf")

        if not muni_name or not state_code:
            return None, False

        # Get Brazil country
        brazil = Country.objects.get(code="BR")

        # Get or create state
        state, _ = State.objects.get_or_create(code=state_code, defaults={"name": state_code, "country": brazil})

        # Get or create municipality
        municipality, created = Municipality.objects.get_or_create(
            name=muni_name, state=state, defaults={"code": state_code}
        )

        return municipality, created

    def get_or_create_community(self, povo_data):
        """Get or create a community (povo) from ISA data"""
        community_name = povo_data.get("povo")

        if not community_name:
            return None, False

        # Generate slug from name
        base_slug = slugify(community_name)

        # Try to get existing community by slug first to avoid duplicates
        try:
            community = Community.objects.get(slug=base_slug)
            return community, False
        except Community.DoesNotExist:
            pass

        # Try to create with name, handling potential slug conflicts
        try:
            community, created = Community.objects.get_or_create(name=community_name, defaults={"slug": base_slug})
            return community, created
        except IntegrityError:
            # Slug conflict with a different name - make slug unique
            counter = 1
            unique_slug = f"{base_slug}-{counter}"
            while Community.objects.filter(slug=unique_slug).exists():
                counter += 1
                unique_slug = f"{base_slug}-{counter}"

            community = Community.objects.create(name=community_name, slug=unique_slug)
            return community, True

    def parse_datetime(self, datetime_str):
        """Parse datetime string from ISA data and make it timezone-aware"""
        if not datetime_str:
            return None

        try:
            # Try parsing ISO format first
            dt = parse_datetime(datetime_str)
            if dt:
                # Make timezone-aware if naive
                if is_naive(dt):
                    dt = make_aware(dt)
                return dt

            # Try parsing custom format: "2025-10-20 19:23:06"
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            # Make timezone-aware if naive
            if is_naive(dt):
                dt = make_aware(dt)
            return dt
        except (ValueError, TypeError):
            return None

    def convert_boolean(self, value):
        """Convert Sim/Não/null to boolean"""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() == "sim"
        return None
