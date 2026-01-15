import json
import unittest
from unittest import mock

from src.scrapers.gru_flights_scraper import GRUFlightScraper


HAS_CURL_CFFI = __import__("importlib").util.find_spec("curl_cffi") is not None
HAS_BS4 = __import__("importlib").util.find_spec("bs4") is not None


@unittest.skipUnless(
    HAS_CURL_CFFI,
    "curl_cffi não está instalado neste ambiente de teste",
)
class GRUFlightScraperTests(unittest.TestCase):
    # 5a. API discovery picks first valid JSON endpoint
    def test_discover_api_endpoint_returns_first_valid_json_endpoint(self) -> None:
        scraper = GRUFlightScraper()

        # Limit endpoints to two for predictable behaviour
        scraper.API_ENDPOINTS = [
            "/pt-br/api/voos/partidas",
            "/pt-br/api/voos/chegadas",
        ]

        def fake_get(url, timeout=0, **_kwargs):  # type: ignore[override]
            # First endpoint returns 404, second returns valid JSON
            response = mock.Mock()
            if url.endswith("/pt-br/api/voos/partidas"):
                response.status_code = 404
                # Any JSON call here should fail
                response.json.side_effect = json.JSONDecodeError("no json", "", 0)
            else:
                response.status_code = 200
                response.json.return_value = [{"flightNumber": "LA3090"}]
            return response

        with mock.patch("src.scrapers._gru_scraper_legacy.time.sleep", return_value=None), \
            mock.patch.object(scraper.session, "get", side_effect=fake_get):
            endpoint = scraper.discover_api_endpoint()

        self.assertIsNotNone(endpoint)
        self.assertTrue(endpoint.endswith("/pt-br/api/voos/chegadas"))

    @unittest.skipUnless(HAS_BS4, "bs4 (BeautifulSoup) não está instalado neste ambiente de teste")
    def test_fetch_flights_prefers_sharepoint_asmx_and_filters_status(self) -> None:
        scraper = GRUFlightScraper()
        # ASMX retorna XML com JSON dentro da tag <string>
        payload = json.dumps(
            [
                {
                    "NumVoo": ["LA3090"],
                    "Cias": [{"Nome": "LATAM"}],
                    "Observacao": "Atrasado",
                    "Horario": "10:00",
                    "HorarioConfirmado": "12:30",  # 150 min
                },
                {
                    "NumVoo": ["G31447"],
                    "Cias": [{"Nome": "GOL"}],
                    "Observacao": "Embarque",
                    "Horario": "11:00",
                    "HorarioConfirmado": "11:05",
                },
            ]
        )
        xml = f'<?xml version="1.0" encoding="utf-8"?><string xmlns="http://tempuri.org/">{payload}</string>'

        with mock.patch.object(scraper, "_post_sharepoint_json", return_value=xml) as mock_post, \
            mock.patch.object(scraper, "_ensure_waf_session", return_value=None) as mock_bootstrap, \
            mock.patch.object(scraper, "fetch_voos_html") as mock_html, \
            mock.patch.object(scraper, "discover_api_endpoint") as mock_discover:
            result = scraper.fetch_flights()

        mock_post.assert_called_once()
        mock_bootstrap.assert_called_once()
        mock_html.assert_not_called()
        mock_discover.assert_not_called()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["numero"], "LA3090")
        self.assertEqual(result[0]["status"], "Atrasado")
        self.assertEqual(result[0]["delay_min"], 150)
        # compat legado
        self.assertEqual(result[0]["flight_number"], "LA3090")
        self.assertEqual(result[0]["airline"], "LATAM")


if __name__ == "__main__":
    unittest.main()
