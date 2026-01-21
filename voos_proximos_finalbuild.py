#!/usr/bin/env python3
"""
Script de Sincronização e Build - MatchFly PSEO
===========================================================
"""

import sys
import os
import requests
import pandas as pd # Usaremos pandas para converter CSV -> JSON
import logging

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
    logger.info("🚀 MATCHFLY - SINCRONIZAÇÃO DE DADOS (CSV + JSON)")
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

    # 2. Conversão para JSON (Para compatibilidade com src/generator.py)
    try:
        logger.info("🔄 Convertendo CSV para JSON...")
        ensure_directory(path_json)
        
        # Lê o CSV baixado
        df = pd.read_csv(path_csv)
        
        # Salva como JSON (formato de lista de registros, padrão web)
        df.to_json(path_json, orient='records', force_ascii=False, indent=2)
        
        logger.info(f"✅ JSON gerado: {path_json} ({len(df)} registros)")
        
    except Exception as e:
        logger.warning(f"⚠️ Erro na conversão JSON (o site pode não atualizar se depender disso): {e}")

if __name__ == "__main__":
    main()
