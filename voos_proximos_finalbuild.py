#!/usr/bin/env python3
"""
Script de Sincronização - MatchFly PSEO
Versão: Ingestão Cumulativa + Retenção 6 Meses + Supabase
- Merge com chave única estrita: FlightNumber + Date + Time (ex: RJ2379_2026-01-30_15:20)
- Dados persistentes no Supabase (tabela flights); sem arquivo JSON local.
- Fetch: baixa voos existentes do Supabase antes de processar (mantém histórico).
- Save: upsert apenas dos novos voos capturados nesta execução.
- Remove voos com scheduled_time anterior a 6 meses (na memória; histórico no banco).
"""

import sys
import os
import re
import requests
import pandas as pd
import numpy as np
import logging
import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client

# Configuração de Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações (CSV em data/; banco no Supabase)
REMOTE_CSV_URL = "https://raw.githubusercontent.com/jonechelon/gru-flight-reliability-monitor/main/voos_atrasados_gru.csv"
DATA_DIR = "data"
CSV_OUTPUT_NAME = "voos_atrasados_gru.csv"
SUPABASE_TABLE = "flights"
PK_COLUMNS = "data_captura,flight_number,scheduled_time"

# Retenção: voos com scheduled_time anterior a este limite são removidos
RETENTION_MONTHS = 6

# Prefixos de companhia comuns (2 letras/dígitos) a remover para unicidade (ex: RJ1070 → 1070)
FLIGHT_NUMBER_PREFIXES = frozenset([
    'LA', 'RJ', 'JJ', 'AD', 'G3', 'TP', 'KL', 'AF', 'LH', 'BA', 'AA', 'UA', 'DL',
    'EK', 'QR', 'AM', 'AC', 'IB', 'ET', 'LX', 'TK', 'AZ', 'U2', 'DY', 'FR',
])


def normalize_flight_number(code) -> str:
    """
    Normaliza o número do voo para evitar duplicatas (ex: RJ1070 e 1070 = mesmo voo).
    - Remove espaços.
    - Remove prefixos comuns de 2 caracteres (LA, RJ, AD, G3, etc.) se seguidos de números.
    - Fallback: extrai a parte numérica principal.
    """
    if code is None:
        return ""
    s = str(code).strip()
    if not s:
        return ""
    # Remove prefixo conhecido (2 chars) se o resto for numérico
    if len(s) > 2 and s[2:].replace(" ", "").isdigit():
        prefix = s[:2].upper()
        if prefix in FLIGHT_NUMBER_PREFIXES:
            rest = s[2:].strip()
            if rest.isdigit():
                return rest
            return s
    # Extração da parte numérica principal (padrão mais seguro)
    digits = re.sub(r"[^\d]", "", s)
    if digits:
        return digits
    return s


def parse_scheduled_time(scheduled_time: str):
    """
    Converte scheduled_time (string) em datetime para comparação.
    Aceita formatos como 'YYYY-MM-DD HH:MM', 'DD/MM/YYYY HH:MM', etc.
    """
    if not scheduled_time or not isinstance(scheduled_time, str):
        return None
    s = scheduled_time.strip()
    if not s:
        return None
    try:
        # ISO: 2026-01-21 14:30
        if '-' in s and ' ' in s:
            return datetime.datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
        if '-' in s and len(s) >= 10:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d")
        # DD/MM/YYYY ou DD/MM
        if '/' in s:
            parts = s.split()
            d_part = parts[0] if parts else s
            segs = d_part.split('/')
            if len(segs) == 3:
                return datetime.datetime.strptime(
                    f"{segs[2]}-{segs[1]}-{segs[0]}" + (" " + parts[1][:5] if len(parts) > 1 else " 00:00"),
                    "%Y-%m-%d %H:%M"
                )
            if len(segs) == 2:
                year = datetime.datetime.now().year
                return datetime.datetime.strptime(
                    f"{year}-{segs[1]}-{segs[0]} 00:00",
                    "%Y-%m-%d %H:%M"
                )
    except Exception:
        pass
    return None


def date_yyyy_mm_dd_from_record(record: dict) -> str:
    """
    Extrai a data (YYYY-MM-DD) do registro para a chave única.
    """
    st = record.get('scheduled_time') or record.get('scheduled_time_iso') or ""
    dt = parse_scheduled_time(st)
    if dt:
        return dt.strftime("%Y-%m-%d")
    s = str(st).strip()
    if "-" in s and len(s) >= 10:
        return s[:10]
    return ""


def time_hh_mm_from_record(record: dict) -> str:
    """
    Extrai o horário (HH:MM) do registro para a chave única.
    """
    st = record.get('scheduled_time') or record.get('scheduled_time_iso') or ""
    dt = parse_scheduled_time(st)
    if dt:
        return dt.strftime("%H:%M")
    s = str(st).strip()
    # Fallback: tentar extrair HH:MM (ex: "2026-01-30 15:20" ou "15:20")
    if " " in s and len(s) >= 16:
        return s[11:16]  # "YYYY-MM-DD HH:MM"
    if re.match(r"\d{1,2}:\d{2}", s):
        return s[:5].zfill(5) if len(s) >= 5 else "00:00"
    return "00:00"


def flight_number_for_uid(record: dict) -> str:
    """
    Número do voo normalizado para UID: strip + remove espaços (sem alterar prefixo).
    Ex: "RJ 2379" -> "RJ2379"
    """
    raw = record.get('flight_number') or record.get('numero_voo') or ""
    return str(raw).strip().replace(" ", "").upper() or ""


def flight_unique_key(record: dict) -> str:
    """
    Chave única estrita: FlightNumber + Date + Time.
    Exemplo: "RJ2379_2026-01-30_15:20"
    Se o UID já existir no merge, SOBRESCREVE com os dados mais recentes (não duplica).
    """
    num = flight_number_for_uid(record)
    date_part = date_yyyy_mm_dd_from_record(record)
    time_part = time_hh_mm_from_record(record)
    return f"{num}_{date_part}_{time_part}"


def _safe_str(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() == "nan":
        return ""
    return s


def _data_captura_from_record(record: dict) -> str:
    st = record.get("scheduled_time") or record.get("scheduled_time_iso") or ""
    dt = parse_scheduled_time(st)
    if dt:
        return dt.strftime("%Y-%m-%d")
    dc = record.get("Data_Captura") or record.get("data_captura") or ""
    if isinstance(dc, str) and "-" in dc and len(dc) >= 10:
        return dc[:10]
    return dc or "1970-01-01"


def _scheduled_time_hhmm_from_record(record: dict) -> str:
    st = record.get("scheduled_time") or record.get("scheduled_time_iso") or ""
    dt = parse_scheduled_time(st)
    if dt:
        return dt.strftime("%H:%M")
    s = str(st).strip()
    if " " in s and len(s) >= 16:
        return s[11:16]
    if re.match(r"\d{1,2}:\d{2}", s):
        return s[:5].zfill(5) if len(s) >= 5 else "00:00"
    return record.get("Horario") or "00:00"


def _is_nullish(val):
    """True se o valor for NaN/NaT/pd.NA/None, inaceitável para JSON/JSONB no Postgres."""
    if val is None:
        return True
    try:
        if pd.isna(val):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(val, float) and (val != val or np.isnan(val)):
        return True
    return False


def sanitize_row_for_supabase(row: dict) -> dict:
    """
    Substitui NaN/NaT/pd.NA por None em todos os campos e dentro de raw_data.
    Evita erro Postgres: invalid input syntax for type json, Token "NaN" is invalid.
    """
    if not isinstance(row, dict):
        return row
    out = {}
    for k, v in row.items():
        if isinstance(v, dict):
            out[k] = sanitize_row_for_supabase(v)
        elif isinstance(v, list):
            out[k] = [
                sanitize_row_for_supabase(x) if isinstance(x, dict) else (None if _is_nullish(x) else x)
                for x in v
            ]
        else:
            out[k] = None if _is_nullish(v) else v
    return out


def flight_record_to_row(record: dict) -> dict:
    """Mapeia um dict de voo (formato interno) para uma linha da tabela Supabase flights."""
    data_captura = _data_captura_from_record(record)
    flight_number = flight_number_for_uid(record)
    if not flight_number:
        flight_number = _safe_str(record.get("flight_number") or record.get("Numero_Voo") or "")
    scheduled_time = _scheduled_time_hhmm_from_record(record)
    return {
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
        "raw_data": record,
    }


def row_to_flight_record(row: dict) -> dict:
    """Converte uma linha Supabase (snake_case) em dict de voo para merge. Preferência por raw_data."""
    if isinstance(row.get("raw_data"), dict):
        return row["raw_data"]
    return {
        "Data_Captura": row.get("data_captura"),
        "Horario": row.get("horario") or row.get("scheduled_time"),
        "Companhia": row.get("companhia") or row.get("airline"),
        "Numero_Voo": row.get("numero_voo") or row.get("flight_number"),
        "Operado_Por": row.get("operado_por"),
        "Status": row.get("status"),
        "Data_Partida": row.get("data_partida"),
        "Hora_Partida": row.get("hora_partida"),
        "flight_number": row.get("flight_number"),
        "airline": row.get("airline"),
        "status": row.get("status"),
        "scheduled_time": row.get("scheduled_time"),
        "data_partida": row.get("data_partida"),
        "delay_hours": row.get("delay_hours"),
        "destination_iata": row.get("destination_iata"),
        "destination": row.get("destination"),
        "destination_city": row.get("destination_city"),
    }


def fetch_existing_flights_from_supabase(client) -> list:
    """Baixa todos os voos da tabela flights. Retorna lista de dict (formato de voo para merge)."""
    try:
        resp = client.table(SUPABASE_TABLE).select("*").execute()
        rows = resp.data or []
        return [row_to_flight_record(r) for r in rows if isinstance(r, dict)]
    except Exception as e:
        logger.warning("⚠️ Não foi possível buscar voos existentes no Supabase: %s. Iniciando do zero.", e)
        return []


def apply_retention_6_months(flights: list) -> list:
    """Remove voos cuja scheduled_time seja anterior a 6 meses atrás."""
    cutoff = datetime.datetime.now() - datetime.timedelta(days=RETENTION_MONTHS * 31)
    kept = []
    removed = 0
    for rec in flights:
        st = parse_scheduled_time(rec.get('scheduled_time'))
        if st is None:
            kept.append(rec)
            continue
        if st >= cutoff:
            kept.append(rec)
        else:
            removed += 1
    if removed:
        logger.info(f"🗑️ Retenção 6 meses: removidos {removed} voos antigos; mantidos {len(kept)}.")
    return kept


def main():
    logger.info("🚀 MATCHFLY - SINCRONIZAÇÃO (SUPABASE + INGESTÃO CUMULATIVA + 6 MESES)")
    
    base_dir = os.getcwd()
    os.makedirs(os.path.join(base_dir, DATA_DIR), exist_ok=True)
    path_csv = os.path.join(base_dir, DATA_DIR, CSV_OUTPUT_NAME)

    # 0. Conexão Supabase
    url = os.environ.get("SUPABASE_URL") or os.environ.get("SUPABASE_SERVICE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        logger.error("🛑 Defina SUPABASE_URL e SUPABASE_KEY (ou SUPABASE_SERVICE_ROLE_KEY) no .env ou GitHub Secrets.")
        sys.exit(1)
    supabase = create_client(url, key)
    logger.info("✅ Conectado ao Supabase")

    # 1. Fetch voos existentes (histórico no site)
    existing_flights = fetch_existing_flights_from_supabase(supabase)
    logger.info("📥 Voos existentes no banco: %s", len(existing_flights))

    # 2. Download CSV
    try:
        logger.info("⬇️ Baixando CSV...")
        response = requests.get(REMOTE_CSV_URL, timeout=30)
        response.raise_for_status()
        with open(path_csv, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        logger.error(f"🛑 Erro no download: {e}")
        sys.exit(1)

    # 3. Leitura e normalização do CSV
    try:
        try:
            df = pd.read_csv(path_csv, sep=None, engine='python')
        except Exception:
            df = pd.read_csv(path_csv, sep=';')

        df.columns = df.columns.str.strip().str.lower()
        logger.info(f"📋 Colunas detectadas: {list(df.columns)}")
        
        col_date = next((c for c in df.columns if 'data_partida' in c), None)
        if not col_date:
            col_date = next((c for c in df.columns if 'data_captura' in c), None)
        col_time = next((c for c in df.columns if 'hora_partida' in c), None)
        if not col_time:
            col_time = next((c for c in df.columns if 'horario' in c), None)
            
        def make_iso_timestamp(row):
            try:
                d_str = str(row[col_date]).strip()
                t_str = str(row[col_time]).strip()
                if len(d_str) <= 5 and '/' in d_str:
                    parts = d_str.split('/')
                    d_iso = f"2026-{parts[1]}-{parts[0]}"
                else:
                    d_iso = d_str
                return f"{d_iso} {t_str}"
            except Exception:
                return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        if col_date and col_time:
            logger.info(f"🕒 Combinando colunas '{col_date}' + '{col_time}' para ordenação...")
            df['scheduled_time_iso'] = df.apply(make_iso_timestamp, axis=1)
        else:
            logger.warning("⚠️ Colunas de data/hora não encontradas para combinação.")
            df['scheduled_time_iso'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        rename_map = {
            'numero_voo': 'flight_number',
            'numero': 'flight_number',
            'voo': 'flight_number',
            'companhia': 'airline',
            'operadora': 'airline',
            'status': 'status',
            'situacao': 'status',
            'origem': 'origin',
            'destino': 'destination',
            'scheduled_time_iso': 'scheduled_time'
        }
        df.rename(columns=rename_map, inplace=True)
        
        if 'flight_number' not in df.columns:
            for col in df.columns:
                if 'num' in col:
                    df.rename(columns={col: 'flight_number'}, inplace=True)
                    break
        
        required = ['flight_number', 'airline', 'status']
        for col in required:
            if col not in df.columns:
                df[col] = "DESCONHECIDO"
            else:
                df[col] = df[col].fillna("DESCONHECIDO")
        if 'origin' not in df.columns:
            df['origin'] = 'GRU'

        new_records = df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"🛑 Erro ao processar CSV: {e}")
        sys.exit(1)

    # 4. Merge com voos existentes (UID estrito: FlightNumber + Date + Time)
    # Se o UID já existir, SOBRESCREVE com os dados mais recentes. NÃO cria nova entrada.
    unique_db = {}
    for rec in existing_flights:
        if isinstance(rec, dict):
            uid = flight_unique_key(rec)
            unique_db[uid] = rec
    new_uids = set()
    for rec in new_records:
        if isinstance(rec, dict):
            uid = flight_unique_key(rec)
            unique_db[uid] = rec
            new_uids.add(uid)

    merged_list = list(unique_db.values())
    logger.info("📦 Merge: %s existentes + %s novos → %s únicos (UID: flight+date+time)",
                len(existing_flights), len(new_records), len(merged_list))

    # 5. Retenção 6 meses (em memória; histórico permanece no banco)
    final_list = apply_retention_6_months(merged_list)

    # 6. Upsert apenas dos novos voos capturados nesta execução
    to_upsert = [rec for rec in final_list if isinstance(rec, dict) and flight_unique_key(rec) in new_uids]
    if to_upsert:
        rows = [flight_record_to_row(rec) for rec in to_upsert]
        rows = [sanitize_row_for_supabase(row) for row in rows]
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            supabase.table(SUPABASE_TABLE).upsert(batch, on_conflict=PK_COLUMNS).execute()
        logger.info("✅ Upsert no Supabase: %s voos (novos desta execução).", len(rows))
    else:
        logger.info("✅ Nenhum voo novo para enviar ao Supabase.")


if __name__ == "__main__":
    main()
