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
        logger.info(f"📁 Diretório criado: {directory}")

def main():
    logger.info("=" * 70)
    logger.info("🚀 MATCHFLY - SINCRONIZAÇÃO DE DADOS (CORREÇÃO DE FORMATO)")
    logger.info("=" * 70)
    
    base_dir = os.getcwd()
    path_csv = os.path.join(base_dir, FIXED_CSV_NAME)
    path_json = os.path.join(base_dir, JSON_OUTPUT_PATH)
    
    # 1. Download do CSV
    try:
        logger.info(f"⬇️ Baixando dados de: {REMOTE_CSV_URL}")
        response = requests.get(REMOTE_CSV_URL, timeout=30)
        response.raise_for_status()
        
        with open(path_csv, 'wb') as f:
            f.write(response.content)
        logger.info("✅ CSV atualizado com sucesso!")
        
    except Exception as e:
        logger.error(f"🛑 Erro fatal no download: {e}")
        sys.exit(1)

    # 2. Conversão para JSON (Formato Compatível com Generator v2.0)
    try:
        logger.info("🔄 Convertendo CSV para JSON estruturado...")
        ensure_directory(path_json)
        
        # Lê o CSV baixado
        df = pd.read_csv(path_csv)
        
        # Converte para lista de dicionários
        flights_list = df.to_dict(orient='records')
        
        # CRIA A ESTRUTURA ESPERADA PELO GENERATOR.PY
        # O generator espera um objeto com a chave 'flights'
        final_structure = {
            "flights": flights_list,
            "metadata": {
                "generated_at": datetime.datetime.now().isoformat(),
                "count": len(flights_list),
                "source": "gru-flight-reliability-monitor"
            }
        }
        
        # Salva como JSON
        with open(path_json, 'w', encoding='utf-8') as f:
            json.dump(final_structure, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ JSON gerado corretamente: {path_json}")
        logger.info(f"📊 Total de voos processados: {len(flights_list)}")
        
    except Exception as e:
        logger.error(f"🛑 Erro na conversão JSON: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
