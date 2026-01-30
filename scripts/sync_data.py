import pandas as pd
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np

try:
    from zoneinfo import ZoneInfo
    BR_TIMEZONE = ZoneInfo("America/Sao_Paulo")
except Exception:
    # Fallback para UTC-3 fixo se ZoneInfo falhar (ex: Python < 3.9)
    BR_TIMEZONE = timezone(timedelta(hours=-3))

ROOT_DIR = Path(__file__).resolve().parent.parent

def sync_csv_to_json():
    csv_path = ROOT_DIR / "data" / "voos_atrasados_gru.csv"
    json_path = ROOT_DIR / "data" / "flights-db.json"

    if not csv_path.exists():
        print(f"⚠️ CSV não encontrado: {csv_path}")
        return

    print(f"📥 Lendo CSV: {csv_path}")
    try:
        # Lê tudo como string (dtype=str) para evitar floats
        df = pd.read_csv(csv_path, dtype=str)
        
        # GARANTIA TOTAL DE STRING: Converte qualquer NaN/Float para string vazia
        df = df.fillna('')
        df = df.astype(str)

        # 1. Renomeia colunas
        rename_map = {
            'Numero_Voo': 'flight_number',
            'Companhia': 'airline',
            'Status': 'status',
            'Horario': 'scheduled_time',
            'Data_Partida': 'data_partida',
            'Data_Captura': 'created_at'
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        
        # 2. Garante Data (Fallback) — data de HOJE no Brasil (não no servidor UTC)
        if 'data_partida' not in df.columns:
            df['data_partida'] = ''
        
        today_str = datetime.now(BR_TIMEZONE).strftime('%d/%m')
        
        # Remove espaços e força data de hoje se vazio
        df['data_partida'] = df['data_partida'].str.strip()
        df.loc[df['data_partida'] == '', 'data_partida'] = today_str
        df.loc[df['data_partida'] == 'nan', 'data_partida'] = today_str

        # 3. Cálculo de Delay
        def calculate_delay(row):
            status = str(row.get('status', '')).lower()
            if 'cancel' in status:
                return 0.0
            if 'atras' in status:
                return 1.0
            return 0.0

        df['delay_hours'] = df.apply(calculate_delay, axis=1)

        # 4. Limpeza Final (Remove linhas onde voo é vazio)
        df = df[df['flight_number'].str.strip() != '']
        
        # Converte para lista de dicionários
        flights_list = df.to_dict(orient='records')
        
        # Salva (timestamp em BRT para consistência)
        final_payload = {
            "flights": flights_list,
            "updated_at": datetime.now(BR_TIMEZONE).isoformat()
        }

        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(final_payload, f, indent=4, ensure_ascii=False)
            
        print(f"✅ Sucesso! {len(flights_list)} voos processados (Tudo convertido para String).")

    except Exception as e:
        print(f"❌ Erro fatal no sync: {e}")
        exit(1)

if __name__ == "__main__":
    sync_csv_to_json()
