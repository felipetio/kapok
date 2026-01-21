import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.factories import CountryFactory
from app.models import Community, Country, Land, Municipality, State


class LoadISADataCommandTest(TestCase):
    """Tests for the load_isa_data management command"""

    def setUp(self):
        """Set up test data"""
        # Load the sample ISA data from fixtures
        self.sample_data_path = Path(__file__).parent / "fixtures" / "sample_isa_data.json"
        with open(self.sample_data_path, encoding="utf-8") as f:
            self.sample_data = json.load(f)

    def test_basic_import(self):
        """Test basic import of ISA data"""
        out = StringIO()
        call_command("load_isa_data", str(self.sample_data_path), stdout=out)

        # Check that lands were created
        self.assertEqual(Land.objects.count(), 3)

        # Check specific lands
        land1 = Land.objects.get(source_id="4184")
        self.assertEqual(land1.name, "Acapuri de Cima")
        self.assertEqual(land1.category, "TI")
        self.assertEqual(land1.source_name, "ISA")
        self.assertIsNotNone(land1.source_updated_at)
        self.assertIsNotNone(land1.source_last_synced_at)
        self.assertIsNotNone(land1.source_raw_data)

        land2 = Land.objects.get(source_id="6296")
        self.assertEqual(land2.name, "Acapuri do Meio")

        land3 = Land.objects.get(source_id="3935")
        self.assertEqual(land3.name, "Acimã")

        # Check output
        output = out.getvalue()
        self.assertIn("Found 3 land records to process", output)
        self.assertIn("Lands created: 3", output)
        self.assertIn("Import completed!", output)

    def test_brazil_country_created(self):
        """Test that Brazil country is created automatically"""
        out = StringIO()
        call_command("load_isa_data", str(self.sample_data_path), stdout=out)

        # Check that Brazil was created
        brazil = Country.objects.get(code="BR")
        self.assertEqual(brazil.name, "Brazil")

        # Check output mentions Brazil creation
        output = out.getvalue()
        self.assertIn("Created Brazil country record", output)

    def test_brazil_country_reused(self):
        """Test that existing Brazil country is reused"""
        # Create Brazil using factory
        CountryFactory(code="BR", name="Brazil")

        out = StringIO()
        call_command("load_isa_data", str(self.sample_data_path), stdout=out)

        # Check that only one Brazil exists
        self.assertEqual(Country.objects.filter(code="BR").count(), 1)

        # Check output does NOT mention Brazil creation
        output = out.getvalue()
        self.assertNotIn("Created Brazil country record", output)

    def test_municipalities_created(self):
        """Test that municipalities and states are created correctly"""
        call_command("load_isa_data", str(self.sample_data_path), verbosity=0)

        # Check Brazil was created
        brazil = Country.objects.get(code="BR")

        # Check states created
        self.assertTrue(State.objects.filter(code="AM").exists())
        state_am = State.objects.get(code="AM")
        self.assertEqual(state_am.country, brazil)

        # Check municipalities created
        # Fonte Boa appears in 2 lands, Lábrea in 1
        self.assertEqual(Municipality.objects.count(), 2)

        fonte_boa = Municipality.objects.get(name="Fonte Boa", state=state_am)
        self.assertIsNotNone(fonte_boa)

        labrea = Municipality.objects.get(name="Lábrea", state=state_am)
        self.assertIsNotNone(labrea)

        # Check land-municipality relationships
        land1 = Land.objects.get(source_id="4184")
        self.assertEqual(land1.municipality, fonte_boa)

        land3 = Land.objects.get(source_id="3935")
        self.assertEqual(land3.municipality, labrea)

    def test_communities_created(self):
        """Test that communities (povos) are created and linked correctly"""
        call_command("load_isa_data", str(self.sample_data_path), verbosity=0)

        # Check communities created
        # Kokama appears in 2 lands, Apurinã in 1
        self.assertEqual(Community.objects.count(), 2)

        kokama = Community.objects.get(name="Kokama")
        self.assertEqual(kokama.slug, "kokama")

        apurina = Community.objects.get(name="Apurinã")
        self.assertEqual(apurina.slug, "apurina")

        # Check land-community relationships (many-to-many)
        land1 = Land.objects.get(source_id="4184")
        self.assertEqual(land1.communities.count(), 1)
        self.assertIn(kokama, land1.communities.all())

        land2 = Land.objects.get(source_id="6296")
        self.assertEqual(land2.communities.count(), 1)
        self.assertIn(kokama, land2.communities.all())

        land3 = Land.objects.get(source_id="3935")
        self.assertEqual(land3.communities.count(), 1)
        self.assertIn(apurina, land3.communities.all())

    def test_dry_run_mode(self):
        """Test that dry-run mode doesn't save to database"""
        out = StringIO()
        call_command("load_isa_data", str(self.sample_data_path), "--dry-run", stdout=out)

        # Check that nothing was saved
        self.assertEqual(Land.objects.count(), 0)
        self.assertEqual(Municipality.objects.count(), 0)
        self.assertEqual(Community.objects.count(), 0)
        self.assertEqual(State.objects.count(), 0)
        self.assertEqual(Country.objects.count(), 0)

        # Check output
        output = out.getvalue()
        self.assertIn("DRY RUN - No changes saved", output)
        self.assertIn("Found 3 land records to process", output)

    def test_update_existing_land(self):
        """Test updating existing land records"""
        # First import
        call_command("load_isa_data", str(self.sample_data_path), verbosity=0)
        self.assertEqual(Land.objects.count(), 3)

        # Modify the data and import again with --update
        modified_data = self.sample_data.copy()
        modified_data["content"]["info_geral"][0]["nome_ti"] = "Acapuri de Cima - Updated"

        # Write modified data to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(modified_data, f)
            temp_path = f.name

        try:
            out = StringIO()
            call_command("load_isa_data", temp_path, "--update", stdout=out)

            # Check that land was updated, not created
            self.assertEqual(Land.objects.count(), 3)
            land = Land.objects.get(source_id="4184")
            self.assertEqual(land.name, "Acapuri de Cima - Updated")

            # Check output
            output = out.getvalue()
            self.assertIn("Lands updated: 3", output)
            self.assertIn("Lands created: 0", output)
        finally:
            Path(temp_path).unlink()

    def test_skip_existing_without_update_flag(self):
        """Test that existing lands are skipped without --update flag"""
        # First import
        call_command("load_isa_data", str(self.sample_data_path), verbosity=0)
        initial_count = Land.objects.count()

        # Try to import again without --update
        out = StringIO()
        call_command("load_isa_data", str(self.sample_data_path), stdout=out)

        # Check that no new lands were created
        self.assertEqual(Land.objects.count(), initial_count)

        # Check output
        output = out.getvalue()
        self.assertIn("Lands created: 0", output)
        self.assertIn("Lands skipped: 3", output)

    def test_invalid_json_file(self):
        """Test error handling for invalid JSON file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            with self.assertRaises(CommandError) as context:
                call_command("load_isa_data", temp_path)
            self.assertIn("Invalid JSON file", str(context.exception))
        finally:
            Path(temp_path).unlink()

    def test_file_not_found(self):
        """Test error handling for non-existent file"""
        with self.assertRaises(CommandError) as context:
            call_command("load_isa_data", "/path/to/nonexistent/file.json")
        self.assertIn("File not found", str(context.exception))

    def test_direct_array_format(self):
        """Test import with direct array format (not wrapped in content)"""
        # Create a direct array format
        direct_array_data = self.sample_data["content"]["info_geral"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(direct_array_data, f)
            temp_path = f.name

        try:
            call_command("load_isa_data", temp_path, verbosity=0)
            self.assertEqual(Land.objects.count(), 3)
        finally:
            Path(temp_path).unlink()

    def test_missing_required_fields(self):
        """Test handling of records with missing ID or name"""
        # Create data with missing required fields
        invalid_data = {
            "content": {
                "info_geral": [
                    {"nome_ti": "Test Land"},  # Missing id
                    {"id": 9999},  # Missing nome_ti
                    {"id": 9998, "nome_ti": "Valid Land", "categoria": "TI"},
                ]
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_data, f)
            temp_path = f.name

        try:
            out = StringIO()
            call_command("load_isa_data", temp_path, stdout=out)

            # Only the valid land should be created
            self.assertEqual(Land.objects.count(), 1)
            land = Land.objects.get(source_id="9998")
            self.assertEqual(land.name, "Valid Land")

            # Check output
            output = out.getvalue()
            self.assertIn("Lands created: 1", output)
            self.assertIn("Lands skipped: 2", output)
        finally:
            Path(temp_path).unlink()

    def test_datetime_parsing(self):
        """Test that datetime fields are parsed correctly"""
        call_command("load_isa_data", str(self.sample_data_path), verbosity=0)

        land1 = Land.objects.get(source_id="4184")
        self.assertIsNotNone(land1.source_updated_at)
        # The sample data has: "2025-10-20 19:23:06"
        self.assertEqual(land1.source_updated_at.year, 2025)
        self.assertEqual(land1.source_updated_at.month, 10)
        self.assertEqual(land1.source_updated_at.day, 20)

    def test_source_raw_data_preserved(self):
        """Test that complete raw data is preserved in JSONField"""
        call_command("load_isa_data", str(self.sample_data_path), verbosity=0)

        land1 = Land.objects.get(source_id="4184")
        self.assertIsNotNone(land1.source_raw_data)

        # Check that important fields are in the raw data
        self.assertEqual(land1.source_raw_data["id"], 4184)
        self.assertEqual(land1.source_raw_data["nome_ti"], "Acapuri de Cima")
        self.assertEqual(land1.source_raw_data["categoria"], "TI")
        self.assertIn("povo", land1.source_raw_data)
        self.assertIn("municipio", land1.source_raw_data)

    def test_statistics_output(self):
        """Test that command outputs correct statistics"""
        out = StringIO()
        call_command("load_isa_data", str(self.sample_data_path), stdout=out)

        output = out.getvalue()

        # Check all statistics are present
        self.assertIn("Found 3 land records to process", output)
        self.assertIn("Import completed!", output)
        self.assertIn("Lands created: 3", output)
        self.assertIn("Lands updated: 0", output)
        self.assertIn("Lands skipped: 0", output)
        self.assertIn("Municipalities created: 2", output)
        self.assertIn("Communities created: 2", output)

    def test_unique_constraint_enforcement(self):
        """Test that unique constraints are enforced (source_name + source_id)"""
        call_command("load_isa_data", str(self.sample_data_path), verbosity=0)

        # Try to create a duplicate land manually
        with self.assertRaises(Exception):  # IntegrityError or similar
            Land.objects.create(
                name="Duplicate",
                category="TI",
                source_id="4184",
                source_name="ISA",
            )

    def test_land_without_municipality(self):
        """Test handling of land without municipality data"""
        data_without_muni = {
            "content": {
                "info_geral": [
                    {
                        "id": 9999,
                        "nome_ti": "Test Land Without Municipality",
                        "categoria": "TI",
                        "municipio": [],  # Empty municipality list
                    }
                ]
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data_without_muni, f)
            temp_path = f.name

        try:
            call_command("load_isa_data", temp_path, verbosity=0)
            land = Land.objects.get(source_id="9999")
            self.assertIsNone(land.municipality)
        finally:
            Path(temp_path).unlink()

    def test_land_without_communities(self):
        """Test handling of land without community data"""
        data_without_communities = {
            "content": {
                "info_geral": [
                    {
                        "id": 9998,
                        "nome_ti": "Test Land Without Communities",
                        "categoria": "TI",
                        "povo": {"data": []},  # Empty communities list
                    }
                ]
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data_without_communities, f)
            temp_path = f.name

        try:
            call_command("load_isa_data", temp_path, verbosity=0)
            land = Land.objects.get(source_id="9998")
            self.assertEqual(land.communities.count(), 0)
        finally:
            Path(temp_path).unlink()

    @patch("app.management.commands.load_isa_data.urlopen")
    def test_download_from_url(self, mock_urlopen):
        """Test downloading data from ISA URL (mocked)"""
        # Mock the urlopen response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.sample_data).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        mock_urlopen.return_value = mock_response

        # Call command without file argument (should download from URL)
        out = StringIO()
        call_command("load_isa_data", stdout=out)

        # Check that urlopen was called with correct URL
        mock_urlopen.assert_called_once_with("https://mapa.eco.br/data/sisarp/v1/tis.json")

        # Check that data was imported correctly
        self.assertEqual(Land.objects.count(), 3)
        self.assertEqual(Municipality.objects.count(), 2)
        self.assertEqual(Community.objects.count(), 2)

        # Check output
        output = out.getvalue()
        self.assertIn("Downloading data from: https://mapa.eco.br/data/sisarp/v1/tis.json", output)
        self.assertIn("Found 3 land records to process", output)
        self.assertIn("Lands created: 3", output)

    @patch("app.management.commands.load_isa_data.urlopen")
    def test_download_url_failure(self, mock_urlopen):
        """Test error handling when URL download fails"""
        # Mock the urlopen to raise an exception
        mock_urlopen.side_effect = Exception("Network error")

        # Call command without file argument
        with self.assertRaises(CommandError) as context:
            call_command("load_isa_data")

        self.assertIn("Failed to download data from URL", str(context.exception))
        mock_urlopen.assert_called_once_with("https://mapa.eco.br/data/sisarp/v1/tis.json")

    @patch("app.management.commands.load_isa_data.urlopen")
    def test_download_url_with_dry_run(self, mock_urlopen):
        """Test downloading from URL with dry-run mode"""
        # Mock the urlopen response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.sample_data).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        mock_urlopen.return_value = mock_response

        # Call command with --dry-run
        out = StringIO()
        call_command("load_isa_data", "--dry-run", stdout=out)

        # Check that nothing was saved
        self.assertEqual(Land.objects.count(), 0)
        self.assertEqual(Municipality.objects.count(), 0)
        self.assertEqual(Community.objects.count(), 0)

        # Check output
        output = out.getvalue()
        self.assertIn("Downloading data from: https://mapa.eco.br/data/sisarp/v1/tis.json", output)
        self.assertIn("DRY RUN - No changes saved", output)

    @patch("app.management.commands.load_isa_data.urlopen")
    def test_download_url_with_update(self, mock_urlopen):
        """Test downloading from URL with --update flag"""
        # First import from file
        call_command("load_isa_data", str(self.sample_data_path), verbosity=0)
        self.assertEqual(Land.objects.count(), 3)

        # Modify data for update
        modified_data = self.sample_data.copy()
        modified_data["content"]["info_geral"][0]["nome_ti"] = "Acapuri de Cima - Updated via URL"

        # Mock the urlopen response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(modified_data).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        mock_urlopen.return_value = mock_response

        # Call command with --update
        out = StringIO()
        call_command("load_isa_data", "--update", stdout=out)

        # Check that land was updated
        self.assertEqual(Land.objects.count(), 3)
        land = Land.objects.get(source_id="4184")
        self.assertEqual(land.name, "Acapuri de Cima - Updated via URL")

        # Check output
        output = out.getvalue()
        self.assertIn("Lands updated: 3", output)
        self.assertIn("Lands created: 0", output)
