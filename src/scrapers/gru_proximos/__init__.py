"""
Pacote do scraper GRU Próximos - Versão Modular.
"""
# Importações condicionais para evitar erros quando playwright não está disponível
try:
    from .scraper_engine import ScraperEngine
except ImportError:
    ScraperEngine = None  # type: ignore

from .data_processor import FlightDataProcessor
from .validators import FlightValidator, CompanyIdentifier, DestinationExtractor
from .logger_config import setup_logger
from .config import *

__all__ = [
    'ScraperEngine',
    'FlightDataProcessor',
    'FlightValidator',
    'CompanyIdentifier',
    'DestinationExtractor',
    'setup_logger',
]
