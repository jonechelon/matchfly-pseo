#!/usr/bin/env python3
"""
Migração única: flights-db.json → tabela flights no Supabase.
- Carrega .env (SUPABASE_URL, SUPABASE_KEY ou SUPABASE_SERVICE_ROLE_KEY).
- Lê data/flights-db.json e mapeia cada voo para as colunas da tabela.
- Faz upsert com on_conflict na PK (data_captura, flight_number, scheduled_time).
- Objeto inteiro é salvo em raw_data (JSONB) para redundância.

Uso: python scripts/migrate_to_supabase.py
"""

import json
import logging
import math
import os
import sys
from pathlib import Path

# Carrega .env antes de importar supabase (para variáveis já estarem definidas)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Caminho do JSON (relativo à raiz do projeto)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = PROJECT_ROOT / "data" / "flights-db.json"

# Chave primária composta da tabela flights
PK_COLUMNS = "data_captura,flight_number,scheduled_time"


def _safe_str(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() == "nan":
        return ""
    return s


def _parse_data_captura(record: dict) -> str:
    """Retorna data_captura no formato YYYY-MM-DD para a PK."""
    dc = record.get("Data_Captura") or record.get("data_captura") or ""
    dc = _safe_str(dc)
    if dc and "-" in dc and len(dc) >= 10:
        return dc[:10]
    return dc or "1970-01-01"


def _parse_scheduled_time(record: dict) -> str:
    """Retorna scheduled_time (HH:MM) para a PK."""
    st = record.get("scheduled_time") or record.get("Horario") or record.get("hora_partida") or ""
    st = _safe_str(st)
    if len(st) > 5:
        st = st[:5]
    return st or "00:00"


def _sanitize_value(val):
    """Remove NaN e Infinity de valores, retornando None ou o valor original."""
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def _sanitize_dict(d: dict) -> dict:
    """Recursivamente sanitiza um dict removendo NaN e Infinity."""
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _sanitize_dict(v)
        elif isinstance(v, list):
            result[k] = [_sanitize_dict(item) if isinstance(item, dict) else _sanitize_value(item) for item in v]
        else:
            result[k] = _sanitize_value(v)
    return result


def flight_record_to_row(record: dict) -> dict:
    """
    Mapeia um objeto de voo do JSON para uma linha da tabela flights.
    Inclui raw_data com o objeto inteiro.
    """
    data_captura = _parse_data_captura(record)
    flight_number = _safe_str(record.get("flight_number") or record.get("Numero_Voo") or "")
    scheduled_time = _parse_scheduled_time(record)

    row = {
        "data_captura": data_captura,
        "flight_number": flight_number,
        "scheduled_time": scheduled_time,
        "horario": _safe_str(record.get("Horario") or record.get("scheduled_time")),
        "companhia": _safe_str(record.get("Companhia") or record.get("airline")),
        "numero_voo": _safe_str(record.get("Numero_Voo") or record.get("flight_number")),
        "operado_por": _safe_str(record.get("Operado_Por") or ""),
        "status": _safe_str(record.get("status") or record.get("Status") or ""),
        "data_partida": _safe_str(record.get("data_partida") or record.get("Data_Partida") or ""),
        "hora_partida": _safe_str(record.get("Hora_Partida") or record.get("scheduled_time") or ""),
        "airline": _safe_str(record.get("airline") or record.get("Companhia") or ""),
        "delay_hours": float(record.get("delay_hours", 0)) if record.get("delay_hours") is not None else 0.0,
        "destination_iata": record.get("destination_iata") and _safe_str(record["destination_iata"]) or None,
        "destination": record.get("destination") and _safe_str(record["destination"]) or None,
        "destination_city": record.get("destination_city") and _safe_str(record["destination_city"]) or None,
        "raw_data": _sanitize_dict(record),
    }
    return row


def main():
    url = os.environ.get("SUPABASE_URL") or os.environ.get("SUPABASE_SERVICE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        logger.error("Defina SUPABASE_URL e SUPABASE_KEY (ou SUPABASE_SERVICE_ROLE_KEY) no .env ou ambiente.")
        sys.exit(1)

    if not JSON_PATH.exists():
        logger.error("Arquivo não encontrado: %s", JSON_PATH)
        sys.exit(1)

    logger.info("Carregando %s...", JSON_PATH)
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    flights = data.get("flights") or data.get("data") or []
    if not isinstance(flights, list):
        flights = []

    if not flights:
        logger.warning("Nenhum voo no JSON. Nada a migrar.")
        sys.exit(0)

    rows = []
    seen = set()
    for rec in flights:
        if not isinstance(rec, dict):
            continue
        row = flight_record_to_row(rec)
        pk = (row["data_captura"], row["flight_number"], row["scheduled_time"])
        if pk in seen:
            continue
        seen.add(pk)
        rows.append(row)

    logger.info("Conectando ao Supabase e fazendo upsert de %s registros...", len(rows))
    client = create_client(url, key)

    # Upsert em lotes para evitar payload muito grande (ex.: 500 por vez)
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        client.table("flights").upsert(batch, on_conflict=PK_COLUMNS).execute()
        logger.info("Upsert batch %s-%s/%s", i + 1, min(i + batch_size, len(rows)), len(rows))

    logger.info("Migração concluída: %s voos enviados para a tabela flights.", len(rows))


if __name__ == "__main__":
    main()
