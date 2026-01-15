"""
GRU Airport Flight Scraper (Playwright)
======================================
Implementação ultra-eficiente baseada em automação real:
- Abre https://www.gru.com.br/pt/passageiro/voos com Playwright (headless)
- Intercepta a resposta da API SharePoint ASMX GetVoos via page.on("response")
- Extrai JSON contido na tag <string> do XML (SharePoint)
- Filtra voos com Observacao contendo "Atrasado" ou "Cancelado"
- Calcula atraso em minutos (HorarioConfirmado - Horario)
- Salva em data/flights-db.json no formato esperado por src/generator.py

Sons (macOS):
- Se a API não for detectada em 20-30s: Basso.aiff
- Se houver voos salvos: Glass.aiff
"""

from __future__ import annotations

import html as _html
import json
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # type: ignore
    from playwright.sync_api import sync_playwright  # type: ignore
except ImportError:  # pragma: no cover
    sync_playwright = None  # type: ignore[assignment]
    PlaywrightTimeoutError = Exception  # type: ignore[assignment]


@dataclass
class _CaptureState:
    xml_text: Optional[str] = None
    api_seen: bool = False


class GRUFlightScraper:
    VOOS_URL = "https://www.gru.com.br/pt/passageiro/voos"
    API_MATCH_SUBSTR = "WebServiceCustom.asmx/GetVoos"

    OUTPUT_DEFAULT = "data/flights-db.json"

    # User-Agent iPhone (menos visado pelo WAF, conforme testes)
    IPHONE_UA = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.2 Mobile/15E148 Safari/604.1"
    )

    def __init__(self, output_file: str = OUTPUT_DEFAULT):
        self.output_file = Path(output_file)
        self._cap = _CaptureState()
        # Compat com logs/ajustes solicitados: variável dedicada ao XML capturado
        self.captured_xml: Optional[str] = None
        self._last_main_status: Optional[int] = None

    # -------------------------
    # macOS sounds
    # -------------------------
    def _sound(self, ok: bool) -> None:
        path = "/System/Library/Sounds/Glass.aiff" if ok else "/System/Library/Sounds/Basso.aiff"
        try:
            os.system(f"afplay {path}")
        except Exception:
            pass

    # -------------------------
    # Interceptação assíncrona
    # -------------------------
    def _capture_data(self, response: Any) -> None:
        try:
            url = str(getattr(response, "url", "") or "")
            if self.API_MATCH_SUBSTR not in url:
                return
            self._cap.api_seen = True
            txt = response.text()
            if txt and "<string" in txt.lower():
                self._cap.xml_text = txt
                self.captured_xml = txt
        except Exception:
            return

    def _fetch_xml_via_playwright(self, *, timeout_ms: int = 30_000) -> Optional[str]:
        if sync_playwright is None:  # pragma: no cover
            raise ImportError(
                "Playwright não está instalado. Instale com `pip install -r requirements.txt` "
                "e rode `playwright install chromium`."
            )

        self._cap = _CaptureState()
        self.captured_xml = None

        # Workaround de permissões TMPDIR (macOS/CI): usa diretório temporário próprio
        with tempfile.TemporaryDirectory(prefix="playwright_tmp_") as temp_dir:
            old_tmpdir = os.environ.get("TMPDIR")
            os.environ["TMPDIR"] = temp_dir
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=False)
                    context = browser.new_context(user_agent=self.IPHONE_UA)
                    page = context.new_page()
                    # Stealth removido para manter o log limpo (e evitar erro de 'module')

                    print("📡 Aguardando resposta do servidor do aeroporto...")

                    # Intercepção de resposta: espera explicitamente pela chamada do SharePoint
                    try:
                        with page.expect_response(
                            lambda r: self.API_MATCH_SUBSTR in (getattr(r, "url", "") or ""),
                            timeout=60_000,
                        ) as resp_info:
                            main_resp = page.goto(self.VOOS_URL, wait_until="domcontentloaded", timeout=60_000)
                            # Simulação humana: scroll para disparar carregamento/API em alguns casos
                            try:
                                page.mouse.wheel(0, 1000)
                            except Exception:
                                pass

                        resp = resp_info.value
                        try:
                            self._cap.api_seen = True
                            xml_text = resp.text()
                        except Exception:
                            xml_text = None
                    except PlaywrightTimeoutError:
                        main_resp = page.goto(self.VOOS_URL, wait_until="domcontentloaded", timeout=60_000)
                        xml_text = None

                    try:
                        self._last_main_status = int(main_resp.status) if main_resp is not None else None
                    except Exception:
                        self._last_main_status = None

                    # Paciência no i5: dá tempo do site processar a tabela
                    # Mantém janela total de 20-30s antes de fechar.
                    page.wait_for_timeout(20_000)

                    # Timeout total solicitado para o GRU: 60s (SharePoint pode demorar)
                    # Se o expect_response capturou o XML, salva agora.
                    if xml_text and "<string" in str(xml_text).lower():
                        self.captured_xml = xml_text
                        self._cap.xml_text = xml_text
                        # Debug temporário: primeiros 500 caracteres do XML capturado
                        try:
                            preview = str(xml_text)[:500]
                            print(f"🧾 XML (primeiros 500 chars): {preview}")
                        except Exception:
                            pass
                        print("✅ Pacote de dados capturado!")

                    context.close()
                    browser.close()
            finally:
                if old_tmpdir is None:
                    os.environ.pop("TMPDIR", None)
                else:
                    os.environ["TMPDIR"] = old_tmpdir

        return self.captured_xml or self._cap.xml_text

    # -------------------------
    # SharePoint XML -> JSON
    # -------------------------
    def _extract_json_from_sharepoint_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        if not (xml_text or "").strip():
            return []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        def _localname(tag: Any) -> str:
            s = str(tag)
            return s.split("}", 1)[-1] if "}" in s else s

        # SharePoint ASMX: <string xmlns="http://tempuri.org/">JSON_AQUI</string>
        json_raw: Optional[str] = None
        if _localname(root.tag).lower() == "string":
            # Ação solicitada: usar root.text
            json_raw = root.text
        else:
            # Fallback: encontra a primeira tag <string> (ignorando namespace)
            for el in root.iter():
                if _localname(el.tag).lower() == "string":
                    json_raw = el.text
                    break

        if not json_raw:
            return []

        json_text = _html.unescape(str(json_raw)).strip()
        if not json_text:
            return []

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return []

        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        return []

    # -------------------------
    # Filtro + atraso (min)
    # -------------------------
    def _parse_hhmm_today(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        s = str(value).strip()
        if not re.fullmatch(r"\d{1,2}:\d{2}", s):
            return None
        try:
            h_s, m_s = s.split(":")
            now = datetime.now()
            return now.replace(hour=int(h_s), minute=int(m_s), second=0, microsecond=0)
        except Exception:
            return None

    def _delay_minutes(self, horario: Any, confirmado: Any) -> Optional[int]:
        a = self._parse_hhmm_today(horario)
        b = self._parse_hhmm_today(confirmado)
        if not a or not b:
            return None
        mins = int(round((b - a).total_seconds() / 60.0))
        return mins if mins > 0 else None

    def _to_generator_record(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        obs = str(item.get("Observacao") or item.get("observacao") or "").strip()
        if ("atrasado" not in obs.lower()) and ("cancelado" not in obs.lower()):
            return None

        # Mapeamento (baseado na captura real):
        # - flight_number: NumVoo[0] (lista com 1 item)
        # - airline: Cias[0].Nome (lista de dicts)
        # - scheduled_time: Horario
        # - actual_time: HorarioConfirmado
        num_voo = item.get("NumVoo")
        flight_number: str = ""
        if isinstance(num_voo, list) and num_voo:
            flight_number = str(num_voo[0]).strip()
        elif num_voo is not None:
            flight_number = str(num_voo).strip()

        # Fallbacks de emergência
        if not flight_number:
            flight_number_raw = item.get("Voo") or item.get("NumeroVoo")
            flight_number = str(flight_number_raw).strip() if flight_number_raw is not None else ""
        if not flight_number:
            return None

        airline: str = ""
        cias = item.get("Cias")
        if isinstance(cias, list) and cias:
            first = cias[0]
            if isinstance(first, dict):
                airline = str(first.get("Nome") or "").strip()
            else:
                airline = str(first).strip()

        # Fallbacks de emergência
        if not airline:
            airline_raw = item.get("Companhia") or item.get("EmpresaAerea")
            airline = str(airline_raw).strip() if airline_raw is not None else ""
        if not airline:
            # Filtro de qualidade: exige Companhia
            return None

        horario = item.get("Horario")
        confirmado = item.get("HorarioConfirmado")

        delay_min = self._delay_minutes(horario, confirmado)
        delay_hours = round(((delay_min or 0) / 60.0), 2)

        # Campos exigidos por src/generator.py:
        # required_fields = ['flight_number', 'airline', 'status']
        return {
            "flight_number": str(flight_number),
            "airline": str(airline),
            "status": obs or "Unknown",
            "scheduled_time": str(horario) if horario is not None else None,
            "actual_time": str(confirmado) if confirmado is not None else None,
            "delay_hours": delay_hours,
            # Extras úteis/compat:
            "delay_min": delay_min,
            "origin": "GRU",
            "numero": str(flight_number),
            "companhia": str(airline),
            "horario": str(horario) if horario is not None else None,
        }

    def _filter_flights(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in raw:
            rec = self._to_generator_record(item)
            if rec is not None:
                out.append(rec)
        return out

    def _save(self, flights: List[Dict[str, Any]]) -> None:
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "flights": flights,
            "metadata": {
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "source": "playwright_intercept:GetVoos",
            },
        }
        self.output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def run(self) -> None:
        print("🔎 Buscando tags: Voo e Companhia...")
        xml_text = self._fetch_xml_via_playwright(timeout_ms=30_000)
        if not xml_text:
            self._save([])
            self._sound(False)
            # LOG solicitado quando a lista final é vazia e o GetVoos não foi detectado
            if not self._cap.api_seen:
                print("❌ Erro: Site carregou, mas a API GetVoos não foi detectada.")
            else:
                # Caso raro: API foi vista mas não conseguimos capturar o XML
                print("❌ Erro: API GetVoos foi vista, mas o XML não foi capturado.")
            return

        raw = self._extract_json_from_sharepoint_xml(xml_text)
        flights = self._filter_flights(raw)
        self._save(flights)

        # Sucesso: só toca Glass se salvou voos reais (número + companhia)
        self._sound(bool(flights))
        print("🎯 MatchFly: Dados limpos e mapeados com sucesso!")


def main() -> None:
    GRUFlightScraper(output_file="data/flights-db.json").run()


if __name__ == "__main__":
    main()

