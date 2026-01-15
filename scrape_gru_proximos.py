#!/usr/bin/env python3
"""
Script de Scraping GRU - Embarque Próximo (Versão Modular)
===========================================================

Funcionalidades:
1. Foco em voos com status "Embarque Próximo" ou "Imediato Embarque"
2. Gera arquivo CSV com timestamp (voos_monitorados_YYYYMMDD_HHMMSS.csv)
3. User-Agent rotativo para evitar bloqueio
4. Tratamento de erros com logging profissional
5. Otimizado para execução frequente
6. Validação rigorosa de sincronização horizontal (garante alinhamento de dados)

REQUISITOS:
- Playwright instalado: pip install playwright && playwright install chromium
- pandas instalado: pip install pandas
"""

import sys
import os

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scrapers.gru_proximos.scraper_engine import ScraperEngine
from src.scrapers.gru_proximos.data_processor import FlightDataProcessor
from src.scrapers.gru_proximos.logger_config import setup_logger
from src.scrapers.gru_proximos.config import (
    MAX_LOAD_MORE_CLICKS, DEFAULT_HEADLESS, WAIT_BETWEEN_CLICKS_MS
)


def main():
    """
    Função principal do scraper modular.
    """
    # Setup logging profissional
    logger = setup_logger()
    
    logger.info("=" * 70)
    logger.info("🚀 SCRAPER GRU - EMBARQUE PRÓXIMO (VERSÃO MODULAR)")
    logger.info("=" * 70)
    logger.info("")
    
    # Cria nome do arquivo CSV com timestamp
    processor = FlightDataProcessor(logger=logger)
    csv_file_path = processor.create_csv_filename()
    logger.info("📂 Arquivo CSV: voos_monitorados_YYYYMMDD_HHMMSS.csv (novo arquivo a cada execução)")
    logger.info(f"   Arquivo atual: {os.path.basename(csv_file_path)}")
    logger.info(f"   Diretório: {os.path.abspath('logs_voos_proximos')}")
    logger.info(f"   Diretório de trabalho atual: {os.getcwd()}")
    logger.info("")
    
    # Scraping
    engine = ScraperEngine(
        headless=DEFAULT_HEADLESS,
        max_clicks=MAX_LOAD_MORE_CLICKS,
        logger=logger
    )
    flights = engine.scrape()
    
    if not flights:
        logger.warning("\n⚠️  Nenhum voo com status 'Embarque Próximo' encontrado no scraping")
        logger.info(f"📄 Arquivo CSV: {os.path.abspath(csv_file_path)}")
        return
    
    logger.info(f"\n" + "=" * 70)
    logger.info("💾 SALVANDO: Processando CSV (novo arquivo com timestamp)")
    logger.info("=" * 70)
    
    # Salva voos em novo arquivo CSV (com limpeza de dados e deduplicação)
    flights_count = processor.save_to_csv(flights, csv_file_path)
    
    logger.info(f"\n" + "=" * 70)
    logger.info("📊 RESUMO FINAL")
    logger.info("=" * 70)
    logger.info(f"   • Total de voos encontrados com status 'Embarque Próximo': {len(flights)}")
    logger.info(f"   • Voos salvos no CSV: {flights_count}")
    logger.info(f"📄 Arquivo CSV: {os.path.abspath(csv_file_path)}")
    logger.info(f"📄 Log de erros: {os.path.abspath('logs_voos_proximos/scraper.log')}")
    logger.info("=" * 70)
    logger.info("✅ Scraping concluído!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
