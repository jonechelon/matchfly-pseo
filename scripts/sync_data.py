import pandas as pd
import json
import os
from pathlib import Path

# Configuração de caminhos
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
# Tenta ler o arquivo com sufixo (1) se existir, senão o padrão
CSV_PATH_1 = DATA_DIR / "voos_atrasados_gru (1).csv"
CSV_PATH_DEFAULT = DATA_DIR / "voos_atrasados_gru.csv"
JSON_PATH = DATA_DIR / "flights-db.json"

def sync_data():
    csv_path = CSV_PATH_1 if CSV_PATH_1.exists() else CSV_PATH_DEFAULT
    print(f"📂 Lendo CSV de: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Erro ao ler CSV: {e}")
        return

    print(f"📊 Total de linhas brutas: {len(df)}")

    # 1. Garante que Data_Captura seja data (trata erros)
    df['Data_Captura_DT'] = pd.to_datetime(df['Data_Captura'], errors='coerce')

    # 2. Ordena: Mais recentes primeiro
    df = df.sort_values('Data_Captura_DT', ascending=False)

    # 3. Deduplica apenas se for o MESMO voo na MESMA data (ex: duplicata de log)
    # Permite histórico: mesmo voo em dias diferentes (27/01 e 31/01) entram no JSON
    df = df.dropna(subset=['Numero_Voo'])
    df_clean = df.drop_duplicates(subset=['Numero_Voo', 'Data_Captura'], keep='first')

    print(f"✨ Total após deduplicação (histórico por data): {len(df_clean)}")
    print(f"🗑️  Removidos {len(df) - len(df_clean)} duplicatas (mesmo voo+data).")

    # 4. Limpeza final para JSON
    if 'Data_Captura_DT' in df_clean.columns:
        df_clean = df_clean.drop(columns=['Data_Captura_DT'])

    df_clean = df_clean.fillna("")

    # Salva JSON
    data = df_clean.to_dict(orient='records')
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON atualizado: {JSON_PATH}")

if __name__ == "__main__":
    sync_data()
