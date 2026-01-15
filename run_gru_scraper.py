#!/usr/bin/env python3
"""
Script runner para o GRU Flight Scraper.
Facilita a execução do scraper a partir da raiz do projeto.
"""

import sys
from pathlib import Path

# Adiciona src ao path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from scrapers.gru_flights_scraper import main

if __name__ == "__main__":
    main()

