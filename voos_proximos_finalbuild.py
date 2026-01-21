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
    logger.info("🚀 MATCHFLY - SINCRONIZAÇÃO & NORMALIZAÇÃO DE DADOS")
    
    base_dir = os.getcwd()
    path_csv = os.path.join(base_dir, FIXED_CSV_NAME)
    path_json = os.path.join(base_dir, JSON_OUTPUT_PATH)
    
    # 1. Download
    try:
        response = requests.get(REMOTE_CSV_URL, timeout=30)
        response.raise_for_status()
        with open(path_csv, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        logger.error(f"🛑 Erro no download: {e}")
        sys.exit(1)

    # 2. Conversão e Correção de Colunas
    try:
        ensure_directory(path_json)
        df = pd.read_csv(path_csv)
        
        # --- ETAPA CRUCIAL: NORMALIZAÇÃO DE CABEÇALHOS ---
        # Converte tudo para minúsculo e remove espaços
        df.columns = df.columns.str.lower().str.strip()
        
        # Mapa de tradução (De -> Para)
        # Ajusta nomes comuns para o padrão exigido pelo generator.py
        column_mapping = {
            'voo': 'flight_number',
            'flight': 'flight_number',
            'numero': 'flight_number',
            
            'companhia': 'airline',
            'company': 'airline',
            'cia': 'airline',
            
            'situacao': 'status',
            'estado': 'status',
            
            'origem': 'origin',
            'destino': 'destination',
            
            'partida_prevista': 'scheduled_time',
            'horario': 'scheduled_time'
        }
        
        # Aplica a renomeação
        df.rename(columns=column_mapping, inplace=True)
        
        # Garante que colunas obrigatórias existam (mesmo que vazias) para não quebrar
        required = ['flight_number', 'airline', 'status']
        for col in required:
            if col not in df.columns:
                logger.warning(f"⚠️ Coluna '{col}' não encontrada. Criando padrão...")
                df[col] = "DESCONHECIDO" if col != 'status' else "Atrasado"

        # Atualiza timestamp para "enganar" filtro de tempo (caso ainda exista)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df['scraped_at'] = now_str 

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
            
        logger.info(f"✅ JSON normalizado gerado com {len(flights_list)} voos")
        
    except Exception as e:
        logger.error(f"🛑 Erro na conversão: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
