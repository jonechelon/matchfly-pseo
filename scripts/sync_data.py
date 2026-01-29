"""
Converte o CSV baixado (data/voos_atrasados_gru.csv) no JSON que o gerador espera
(data/flights-db.json). Estrutura obrigatória: {"flights": [...], ...}.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

# Caminhos relativos à raiz do projeto (funciona ao rodar de scripts/ ou da raiz)
ROOT_DIR = Path(__file__).resolve().parent.parent


def sync_csv_to_json():
    csv_path = ROOT_DIR / "data" / "voos_atrasados_gru.csv"
    json_path = ROOT_DIR / "data" / "flights-db.json"

    # Se não tiver CSV, não faz nada (evita quebrar em ambiente limpo)
    if not csv_path.exists():
        print(f"⚠️ Arquivo CSV não encontrado: {csv_path}. Pulando sincronização.")
        return

    print(f"📥 Lendo CSV atualizado: {csv_path}")
    try:
        # Lê o CSV como string para preservar formatação
        df = pd.read_csv(csv_path, dtype=str)

        # Mapeamento de colunas (PT -> EN)
        rename_map = {
            "Numero_Voo": "flight_number",
            "Companhia": "airline",
            "Status": "status",
            "Horario": "scheduled_time",
            "Data_Partida": "data_partida",
            "Data_Captura": "created_at",
        }

        # Renomeia as colunas (apenas as que existem)
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # Garante que display_time existe
        if "display_time" not in df.columns and "scheduled_time" in df.columns:
            df["display_time"] = df["scheduled_time"]

        # Limpeza básica
        if "flight_number" in df.columns:
            df = df.dropna(subset=["flight_number"])

        # Lógica de delay_hours (Necessário para o Generator)
        def calculate_delay(row):
            status = str(row.get("status", "")).lower()
            if "cancelado" in status:
                return 0.0
            if "atrasado" in status:
                return 1.0  # Valor padrão para indicar atraso > 1h
            return 0.0

        if "delay_hours" not in df.columns:
            df["delay_hours"] = df.apply(calculate_delay, axis=1)

        # Converte para lista de dicionários
        flights_list = df.to_dict(orient="records")

        # Estrutura Final Obrigatória: Objeto com chave "flights"
        final_payload = {
            "flights": flights_list,
            "updated_at": datetime.now().isoformat(),
        }

        # Salva no JSON
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(final_payload, f, indent=4, ensure_ascii=False)

        print(f"✅ Sucesso! {len(flights_list)} voos sincronizados para {json_path}")

    except Exception as e:
        print(f"❌ Erro crítico ao converter CSV para JSON: {e}")
        exit(1)  # Falha o pipeline para não gerar site vazio


if __name__ == "__main__":
    sync_csv_to_json()
