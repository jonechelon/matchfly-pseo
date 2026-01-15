import json
import os
import tempfile
import unittest
from pathlib import Path

from src.generator import FlightPageGenerator, get_iata_code, is_domestic_flight


class FlightPageGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        # Isolated temp directory for each test
        self.tmpdir = tempfile.TemporaryDirectory()
        base = Path(self.tmpdir.name)

        self.output_dir = base / "public"
        self.voo_dir = self.output_dir / "voo"
        self.data_file = base / "flights-db.json"

        # Minimal template required by Jinja2
        template_dir = base / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        self.template_file = template_dir / "tier2-anac400.html"
        self.template_file.write_text(
            """<!DOCTYPE html><html><body>
            <h1>{{ flight_number }}</h1>
            <p>Status: {{ status }}</p>
            <a href=\"{{ affiliate_link }}\">CTA</a>
            </body></html>""",
            encoding="utf-8",
        )

        self.affiliate_link = "https://example.com/offer?ref=test"
        self.base_url = "https://example.com"

        self.generator = FlightPageGenerator(
            data_file=str(self.data_file),
            template_file=str(self.template_file),
            output_dir=str(self.output_dir),
            voo_dir=str(self.voo_dir),
            affiliate_link=self.affiliate_link,
            base_url=self.base_url,
        )

    def test_default_base_url_is_matchfly_org(self) -> None:
        """Default base_url should point to the public MatchFly domain."""
        generator = FlightPageGenerator(
            data_file=str(self.data_file),
            template_file=str(self.template_file),
            output_dir=str(self.output_dir),
            voo_dir=str(self.voo_dir),
            affiliate_link=self.affiliate_link,
        )
        self.assertEqual(generator.base_url, "https://matchfly.org")

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    # 1. Affiliate link validation (maps to setup_and_validate)
    def test_setup_and_validate_uses_fallback_when_affiliate_link_missing_or_blank(self) -> None:
        """When affiliate link is missing, setup should succeed with a fallback link."""
        gen_missing = FlightPageGenerator(
            data_file=str(self.data_file),
            template_file=str(self.template_file),
            output_dir=str(self.output_dir),
            voo_dir=str(self.voo_dir),
            affiliate_link="",
            base_url=self.base_url,
        )
        # Should succeed with fallback link
        self.assertTrue(gen_missing.setup_and_validate())
        self.assertEqual(gen_missing.affiliate_link, "https://www.compensair.com/")

        gen_blank = FlightPageGenerator(
            data_file=str(self.data_file),
            template_file=str(self.template_file),
            output_dir=str(self.output_dir),
            voo_dir=str(self.voo_dir),
            affiliate_link="   ",
            base_url=self.base_url,
        )
        # Should succeed with fallback link
        self.assertTrue(gen_blank.setup_and_validate())
        self.assertEqual(gen_blank.affiliate_link, "https://www.compensair.com/")

    # 2. Page generation for filtered flights
    def test_generate_pages_creates_files_for_filtered_flights_only(self) -> None:
        # Prepare directories and pass validation
        self.assertTrue(self.generator.setup_and_validate())

        flights_payload = {
            "metadata": {"scraped_at": "2026-01-11T10:00:00Z"},
            "flights": [
                {
                    "flight_number": "LA3090",
                    "airline": "LATAM",
                    "status": "Cancelado",
                    "delay_hours": 0,
                    "origin": "gru",
                },
                {
                    # Should be filtered out (on time)
                    "flight_number": "LA1234",
                    "airline": "LATAM",
                    "status": "Confirmado",
                    "delay_hours": 0,
                    "origin": "gru",
                },
                {
                    "flight_number": "G31447",
                    "airline": "GOL",
                    "status": "Atrasado",
                    "delay_hours": 3,
                    "origin": "gru",
                },
            ],
        }
        self.data_file.write_text(json.dumps(flights_payload), encoding="utf-8")

        data = self.generator.load_flight_data()
        self.assertIsNotNone(data)
        flights = data["flights"]
        metadata = data["metadata"]

        for flight in flights:
            if self.generator.should_generate_page(flight):
                self.generator.generate_page_resilient(flight, metadata)

        # Only 2 flights should pass the filter
        self.assertEqual(len(self.generator.success_files), 2)

        expected_files = {
            "voo-latam-la3090-gru-cancelado.html",
            "voo-gol-g31447-gru-atrasado.html",
        }
        self.assertSetEqual(self.generator.success_files, expected_files)

        # Files exist on disk and contain key information
        for filename in expected_files:
            path = self.voo_dir / filename
            self.assertTrue(path.exists(), f"Expected file {filename} to be created")
            content = path.read_text(encoding="utf-8")
            self.assertIn("CTA", content)
            # Verify that the deep link to AirHelp funnel was generated
            self.assertIn("funnel.airhelp.com/claims/new/trip-details", content)
            self.assertIn("departureAirportIata=gru", content)
            # Verify affiliate tracking parameters are present
            self.assertIn("a_aid=69649260287c5", content)
            self.assertIn("utm_medium=affiliate", content)

    # 3. Orphan file cleanup (maps to manage_orphans)
    def test_manage_orphans_removes_files_not_in_success_set(self) -> None:
        self.assertTrue(self.generator.setup_and_validate())

        # Create three files, but only two are in success_files
        self.voo_dir.mkdir(parents=True, exist_ok=True)
        kept_1 = self.voo_dir / "voo-latam-la3090-gru-cancelado.html"
        kept_2 = self.voo_dir / "voo-gol-g31447-gru-atrasado.html"
        orphan = self.voo_dir / "old-orphan.html"

        for p in (kept_1, kept_2, orphan):
            p.write_text("dummy", encoding="utf-8")

        self.generator.success_files.update({kept_1.name, kept_2.name})

        self.generator.manage_orphans()

        self.assertTrue(kept_1.exists())
        self.assertTrue(kept_2.exists())
        self.assertFalse(orphan.exists())
        self.assertEqual(self.generator.stats["orphans_removed"], 1)

    # 4. Sitemap generation
    def test_generate_sitemap_includes_home_and_flight_urls(self) -> None:
        self.assertTrue(self.generator.setup_and_validate())

        # Pretend we have generated one successful page
        self.generator.success_pages.append(
            {
                "filename": "voo-latam-la3090-gru-cancelado.html",
                "slug": "voo-latam-la3090-gru-cancelado",
                "flight_number": "LA3090",
                "airline": "LATAM",
                "status": "Cancelado",
                "delay_hours": 0,
                "scheduled_time": "2026-01-11 10:00:00",
                "url": "/voo/voo-latam-la3090-gru-cancelado.html",
            }
        )

        self.generator.generate_sitemap()

        sitemap_path = self.output_dir / "sitemap.xml"
        self.assertTrue(sitemap_path.exists())

        from xml.etree import ElementTree as ET

        tree = ET.parse(sitemap_path)
        root = tree.getroot()

        # Handle default namespace in tag names
        def strip_ns(tag: str) -> str:
            return tag.split("}", 1)[-1] if "}" in tag else tag

        self.assertEqual(strip_ns(root.tag), "urlset")

        # Collect <loc> values
        locs = []
        for url in root:
            if strip_ns(url.tag) != "url":
                continue
            for child in url:
                if strip_ns(child.tag) == "loc":
                    locs.append(child.text)

        expected_home = f"{self.base_url}/"
        expected_flight = f"{self.base_url}/voo/voo-latam-la3090-gru-cancelado.html"

        self.assertIn(expected_home, locs)
        self.assertIn(expected_flight, locs)
        self.assertGreaterEqual(len(locs), 2)

    # 5. IATA code mapping with case-insensitive search
    def test_get_iata_code_case_insensitive_and_strip(self) -> None:
        """Test that IATA code mapping works with any case and extra spaces."""
        # Uppercase
        self.assertEqual(get_iata_code("PARIS"), "CDG")
        self.assertEqual(get_iata_code("RIO DE JANEIRO"), "GIG")
        
        # Lowercase
        self.assertEqual(get_iata_code("paris"), "CDG")
        self.assertEqual(get_iata_code("rio de janeiro"), "GIG")
        
        # Mixed case
        self.assertEqual(get_iata_code("Paris"), "CDG")
        self.assertEqual(get_iata_code("Rio De Janeiro"), "GIG")
        
        # With extra spaces
        self.assertEqual(get_iata_code("  Paris  "), "CDG")
        self.assertEqual(get_iata_code("  Miami  "), "MIA")
        
        # International destinations
        self.assertEqual(get_iata_code("lisboa"), "LIS")
        self.assertEqual(get_iata_code("MADRID"), "MAD")
        self.assertEqual(get_iata_code("Buenos Aires"), "EZE")
        self.assertEqual(get_iata_code("NOVA YORK"), "JFK")
        self.assertEqual(get_iata_code("orlando"), "MCO")
        
        # National destinations
        self.assertEqual(get_iata_code("brasília"), "BSB")
        self.assertEqual(get_iata_code("FORTALEZA"), "FOR")
        self.assertEqual(get_iata_code("Porto Alegre"), "POA")
        self.assertEqual(get_iata_code("CURITIBA"), "CWB")
        self.assertEqual(get_iata_code("  florianópolis  "), "FLN")
        self.assertEqual(get_iata_code("FOZ DO IGUAÇU"), "IGU")
        self.assertEqual(get_iata_code("Porto Seguro"), "BPS")
        
        # Fallback for unmapped cities (returns empty string)
        self.assertEqual(get_iata_code("Cidade Inexistente"), "")
        self.assertEqual(get_iata_code(""), "")
        self.assertEqual(get_iata_code("   "), "")

    def test_is_domestic_flight(self) -> None:
        """Test domestic flight detection."""
        # Domestic flights
        self.assertTrue(is_domestic_flight("GIG"))
        self.assertTrue(is_domestic_flight("BSB"))
        self.assertTrue(is_domestic_flight("GRU"))
        
        # International flights
        self.assertFalse(is_domestic_flight("CDG"))
        self.assertFalse(is_domestic_flight("EZE"))
        self.assertFalse(is_domestic_flight("MIA"))
        
        # Empty or unmapped
        self.assertFalse(is_domestic_flight(""))


if __name__ == "__main__":
    unittest.main()
