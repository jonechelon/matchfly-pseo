#!/usr/bin/env python3
"""
Script de Sincronização - MatchFly PSEO
Versão: Ingestão Cumulativa + Retenção 6 Meses + Higiene de Duplicatas
- Merge com chave única estrita: FlightNumber + Date + Time (ex: RJ2379_2026-01-30_15:20)
- Número do voo normalizado (remove espaços) para evitar duplicatas
- Se o UID já existir: SOBRESCREVE com dados mais recentes (nunca duplica)
- Remove voos com scheduled_time anterior a 6 meses
"""

import sys
import os
import re
import requests
import pandas as pd
import json
import logging
import datetime

# Configuração de Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações (CSV e JSON em data/)
REMOTE_CSV_URL = "https://raw.githubusercontent.com/jonechelon/gru-flight-reliability-monitor/main/voos_atrasados_gru.csv"
DATA_DIR = "data"
CSV_OUTPUT_NAME = "voos_atrasados_gru.csv"
JSON_OUTPUT_PATH = "data/flights-db.json"

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


def load_existing_db(path_json: str) -> dict:
    """Carrega data/flights-db.json existente. Retorna {'flights': [], 'metadata': {}} se vazio ou inexistente."""
    if not os.path.exists(path_json):
        return {"flights": [], "metadata": {}}
    try:
        with open(path_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"⚠️ Não foi possível ler JSON existente: {e}. Iniciando do zero.")
        return {"flights": [], "metadata": {}}
    flights = data.get('flights') or data.get('data') or []
    if not isinstance(flights, list):
        flights = []
    return {"flights": flights, "metadata": data.get("metadata", {})}


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
    logger.info("🚀 MATCHFLY - SINCRONIZAÇÃO (INGESTÃO CUMULATIVA + 6 MESES)")
    
    base_dir = os.getcwd()
    os.makedirs(os.path.join(base_dir, DATA_DIR), exist_ok=True)
    path_csv = os.path.join(base_dir, DATA_DIR, CSV_OUTPUT_NAME)
    path_json = os.path.join(base_dir, JSON_OUTPUT_PATH)
    
    # 1. Download
    try:
        logger.info("⬇️ Baixando CSV...")
        response = requests.get(REMOTE_CSV_URL, timeout=30)
        response.raise_for_status()
        with open(path_csv, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        logger.error(f"🛑 Erro no download: {e}")
        sys.exit(1)

    # 2. Leitura e normalização do CSV
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

    # 3. Merge com banco existente (UID estrito: FlightNumber + Date + Time)
    # Se o UID já existir, SOBRESCREVE com os dados mais recentes. NÃO cria nova entrada.
    existing = load_existing_db(path_json)
    unique_db = {}
    for rec in existing["flights"]:
        if isinstance(rec, dict):
            uid = flight_unique_key(rec)
            unique_db[uid] = rec
    for rec in new_records:
        if isinstance(rec, dict):
            uid = flight_unique_key(rec)
            unique_db[uid] = rec  # sobrescreve: mesmo UID = update, nunca duplica

    merged_list = list(unique_db.values())
    logger.info(f"📦 Merge: {len(existing['flights'])} existentes + {len(new_records)} novos → {len(merged_list)} únicos (UID: flight+date+time)")

    # 4. Retenção 6 meses
    final_list = apply_retention_6_months(merged_list)

    # 5. Salvar JSON
    final_structure = {
        "flights": final_list,
        "metadata": {
            "generated_at": datetime.datetime.now().isoformat(),
            "count": len(final_list),
            "source": "voos_proximos_finalbuild.py (cumulative)",
            "retention_months": RETENTION_MONTHS,
        }
    }
    os.makedirs(os.path.dirname(path_json), exist_ok=True)
    with open(path_json, 'w', encoding='utf-8') as f:
        json.dump(final_structure, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ JSON salvo com {len(final_list)} voos (histórico cumulativo, retenção 6 meses).")


if __name__ == "__main__":
    main()
