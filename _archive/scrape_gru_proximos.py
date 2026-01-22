#!/usr/bin/env python3
"""
Script de Sincronização e Build - MatchFly PSEO
===========================================================

Objetivo:
1. Baixar a versão mais recente dos dados do repositório 'gru-flight-reliability-monitor'.
2. Garantir que o site tenha o arquivo 'voos_atrasados_gru.csv' atualizado antes do build.
3. Manter histórico com timestamp para logs.

REQUISITOS:
- requests: pip install requests
- pandas: pip install pandas
"""

import sys
import os
import shutil
import requests
import datetime

# Adiciona o diretório raiz ao path para imports (mantido para compatibilidade)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports locais (mantidos caso precise do processador para formatação futura)
from src.scrapers.gru_proximos.data_processor import FlightDataProcessor
from src.scrapers.gru_proximos.logger_config import setup_logger

# Configurações de URL
REMOTE_CSV_URL = "https://raw.githubusercontent.com/jonechelon/gru-flight-reliability-monitor/main/voos_atrasados_gru.csv"
FIXED_FILENAME = "voos_atrasados_gru.csv"

def download_remote_csv(url, dest_path, logger):
    """Baixa o CSV do repositório de dados."""
    try:
        logger.info(f"⬇️ Iniciando download de: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status() # Lança erro se status != 200
        
        with open(dest_path, 'wb') as f:
            f.write(response.content)
            
        file_size = os.path.getsize(dest_path) / 1024
        logger.info(f"✅ Download concluído! Tamanho: {file_size:.2f} KB")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao baixar CSV remoto: {e}")
        return False

def main():
    """
    Função principal de sincronização.
    """
    # Setup logging
    logger = setup_logger()
    
    logger.info("=" * 70)
    logger.info("🚀 MATCHFLY - SINCRONIZAÇÃO DE DADOS (PIPELINE)")
    logger.info("=" * 70)
    logger.info("")
    
    # 1. Preparação dos nomes de arquivo
    processor = FlightDataProcessor(logger=logger)
    timestamp_filename = processor.create_csv_filename() # voos_monitorados_YYYY...
    
    # Caminhos absolutos
    base_dir = os.getcwd()
    path_timestamp = os.path.abspath(timestamp_filename)
    path_fixed = os.path.join(base_dir, FIXED_FILENAME)
    
    logger.info(f"📂 Diretório de trabalho: {base_dir}")
    logger.info(f"🎯 Alvo Primário (Site): {FIXED_FILENAME}")
    logger.info(f"🕒 Alvo Histórico (Log): {os.path.basename(timestamp_filename)}")
    logger.info("")

    # 2. Execução: Download dos dados (Primary Method)
    logger.info("📡 TENTATIVA 1: Sincronizar com Repositório de Dados...")
    success = download_remote_csv(REMOTE_CSV_URL, path_fixed, logger)

    if success:
        # Cria a cópia com timestamp para manter o histórico de logs
        try:
            shutil.copy2(path_fixed, path_timestamp)
            logger.info(f"✅ Cópia de histórico criada: {os.path.basename(timestamp_filename)}")
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível criar cópia de histórico: {e}")
            
    else:
        # FALLBACK: Se o download falhar, tentamos rodar o scraper localmente?
        # Por enquanto, vamos falhar o build para avisar que há algo errado na conexão.
        logger.error("🛑 Falha crítica: Não foi possível obter dados atualizados.")
        logger.error("   Verifique se o arquivo existe no repositório 'gru-flight-reliability-monitor'.")
        sys.exit(1) # Encerra com erro para o GitHub Actions saber

    # 3. Validação Final
    if os.path.exists(path_fixed):
        logger.info(f"\n" + "=" * 70)
        logger.info("📊 STATUS DO PIPELINE")
        logger.info("=" * 70)
        
        # Leitura simples para contar linhas (verificação de sanidade)
        try:
            with open(path_fixed, 'r', encoding='utf-8') as f:
                row_count = sum(1 for line in f) - 1 # Remove header
            logger.info(f"   • Arquivo Atualizado: Sim")
            logger.info(f"   • Total de Registros: {row_count}")
            logger.info(f"   • Caminho: {path_fixed}")
        except:
            logger.warning("   • Arquivo existe mas não pôde ser lido.")
            
        logger.info("=" * 70)
        logger.info("✅ Dados prontos para o build do site!")
        logger.info("=" * 70)
    else:
        logger.error("❌ Arquivo final não encontrado. O build do site falhará.")
        sys.exit(1)

if __name__ == "__main__":
    main()
