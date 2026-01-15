"""
Configuração de logging profissional para o scraper GRU Próximos.
"""
import logging
import os
from pathlib import Path
from .config import LOG_DIR, SCRAPER_LOG_PATH, LOG_ENCODING

def setup_logger(name: str = "gru_proximos_scraper") -> logging.Logger:
    """
    Configura e retorna um logger profissional com handlers para arquivo e console.
    
    Args:
        name: Nome do logger
        
    Returns:
        Logger configurado com handlers para arquivo (DEBUG) e console (INFO)
    """
    logger = logging.getLogger(name)
    
    # Evita adicionar handlers duplicados se o logger já foi configurado
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Handler para arquivo (todos os níveis)
    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = logging.FileHandler(SCRAPER_LOG_PATH, encoding=LOG_ENCODING)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Handler para console (apenas INFO e acima)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
