#!/usr/bin/env python3
"""
Script de Sincronização e Build - MatchFly PSEO
===========================================================
"""

import sys
import os
import shutil
import requests
import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurações de URL
REMOTE_CSV_URL = "https://raw.githubusercontent.com/jonechelon/gru-flight-reliability-monitor/main/voos_atrasados_gru.csv"
FIXED_FILENAME = "voos_atrasados_gru.csv"

# Configuração de Logger simples local para evitar dependência de arquivo externo que possa pedir Playwright
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_remote_csv(url, dest_path):
    """Baixa o CSV do repositório de dados."""
    try:
        logger.info(f"⬇️ Iniciando download de: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status() 
        
        with open(dest_path, 'wb') as f:
            f.write(response.content)
            
        file_size = os.path.getsize(dest_path) / 1024
        logger.info(f"✅ Download concluído! Tamanho: {file_size:.2f} KB")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao baixar CSV remoto: {e}")
        return False

def main():
    logger.info("=" * 70)
    logger.info("🚀 MATCHFLY - SINCRONIZAÇÃO DE DADOS (VERSÃO DOWNLOAD)")
    logger.info("=" * 70)
    
    # Caminhos
    base_dir = os.getcwd()
    path_fixed = os.path.join(base_dir, FIXED_FILENAME)
    
    # Execução: Download dos dados
    success = download_remote_csv(REMOTE_CSV_URL, path_fixed)

    if not success:
        logger.error("🛑 Falha crítica: Não foi possível obter dados.")
        sys.exit(1)

    # Validação
    if os.path.exists(path_fixed):
        with open(path_fixed, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        logger.info(f"✅ Arquivo pronto com {len(lines)} linhas.")
    else:
        logger.error("❌ Arquivo não encontrado após download.")
        sys.exit(1)

if __name__ == "__main__":
    main()
