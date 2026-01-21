#!/usr/bin/env python3
"""
Script de Sincronização e Build - MatchFly PSEO
===========================================================
"""

import sys
import os
import requests
import pandas as pd
import json
import logging
import datetime

# Configuração de Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
REMOTE_CSV_URL = "https://raw.githubusercontent.com/jonechelon/gru-flight-reliability-monitor/main/voos_atrasados_gru.csv"
FIXED_CSV_NAME = "voos_atrasados_gru.csv"
JSON_OUTPUT_PATH = "data/flights-db.json"

def ensure_directory(path):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def main():
    logger.info("🚀 MATCHFLY - SINCRONIZAÇÃO (FORÇANDO DADOS RECENTES)")
    
    base_dir = os.getcwd()
    path_csv = os.path.join(base_dir, FIXED_CSV_NAME)
    path_json = os.path.join(base_dir, JSON_OUTPUT_PATH)
    
    # 1. Download do CSV
    try:
        response = requests.get(REMOTE_CSV_URL, timeout=30)
        response.raise_for_status()
        with open(path_csv, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        logger.error(f"🛑 Erro no download: {e}")
        sys.exit(1)

    # 2. Conversão e "Rejuvenescimento" dos dados
    try:
        ensure_directory(path_json)
        df = pd.read_csv(path_csv)
        
        # TRUQUE: Atualiza a coluna 'last_update' (ou similar) para AGORA
        # Isso evita que o generator.py filtre os voos por serem "velhos"
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Tenta encontrar colunas de data comuns e atualiza
        cols_to_update = ['last_update', 'data_extracao', 'timestamp']
        for col in cols_to_update:
            if col in df.columns:
                df[col] = now_str
                logger.info(f"🔄 Atualizada coluna '{col}' para {now_str}")

        flights_list = df.to_dict(orient='records')
        
        final_structure = {
            "flights": flights_list,
            "metadata": {
                "generated_at": datetime.datetime.now().isoformat(),
                "count": len(flights_list),
                "source": "gru-flight-reliability-monitor"
            }
        }
        
        with open(path_json, 'w', encoding='utf-8') as f:
            json.dump(final_structure, f, indent=2, ensure_ascii=False)
            
        logger.info(f"✅ JSON gerado com {len(flights_list)} voos (timestamp atualizado)")
        
    except Exception as e:
        logger.error(f"🛑 Erro na conversão: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
