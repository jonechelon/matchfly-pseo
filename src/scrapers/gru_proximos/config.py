"""
Configurações e constantes para o scraper GRU Próximos.
"""
import os
from pathlib import Path

# ============================================================================
# TIMEOUTS (em milissegundos)
# ============================================================================
PAGE_LOAD_TIMEOUT = 60_000
ELEMENT_WAIT_TIMEOUT = 5_000
INITIAL_PAGE_WAIT = 2_000
CLICK_WAIT_OBLIGATORY = 3_000
CLICK_WAIT_ADDITIONAL = 300  # Convertido de time.sleep(0.3)
SCROLL_WAIT = 500
FINAL_RENDER_WAIT = 5_000
OFFLINE_STABILIZATION_WAIT = 2_000

# ============================================================================
# CONFIGURAÇÕES DE SCRAPING
# ============================================================================
MAX_LOAD_MORE_CLICKS = 5
WAIT_BETWEEN_CLICKS_MS = 1_000
DEFAULT_HEADLESS = True

# ============================================================================
# URLs
# ============================================================================
VOOS_URL = "https://www.gru.com.br/pt/passageiro/voos"

# ============================================================================
# SELETORES CSS
# ============================================================================
LOAD_MORE_SELECTORS = [
    "button:has-text('Carregar mais')",
    "button:has-text('carregar mais')",
    "a:has-text('Carregar mais')",
    "[class*='load-more']",
    "[class*='carregar']",
    "button:has-text('Carregar')",
    "a:has-text('Carregar')",
]

# ============================================================================
# DIRETÓRIOS E ARQUIVOS
# ============================================================================
LOG_DIR = 'logs_voos_proximos'
CSV_FILE_NAME_TEMPLATE = "voos_monitorados_{}.csv"
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error_log.txt")
SCRAPER_LOG_PATH = os.path.join(LOG_DIR, "scraper.log")
DISCARD_LOG_PATH = os.path.join(LOG_DIR, "discarded_flights.log")  # Log de descartes para análise

# Garante que o diretório existe
os.makedirs(LOG_DIR, exist_ok=True)

# ============================================================================
# ENCODING
# ============================================================================
CSV_ENCODING = 'utf-8-sig'  # BOM para Excel
LOG_ENCODING = 'utf-8'

# ============================================================================
# COLUNAS DO CSV
# ============================================================================
CSV_COLUMNS = [
    "databusca",  # Primeira coluna: timestamp da busca
    "Data",
    "Horario_Previsto",
    "Horario_Estimado",
    "Voo",
    "Companhia",
    "Destino",
    "Status",
    "Alerta_1H",
    "Alerta_2H",
    "Status_Monitoramento",
]

# ============================================================================
# COMPANHIAS AÉREAS
# ============================================================================
# Lista de companhias conhecidas (para filtro de destino incorreto)
COMPANHIAS_CONHECIDAS = {
    "LATAM", "TAM", "GOL", "AZUL", "EMIRATES", "TURKISH", "TURKISH AIRLINES",
    "BRITISH", "BRITISH AIRWAYS", "AIR FRANCE", "AIRFRANCE", "KLM", "LUFTHANSA",
    "AMERICAN", "AMERICAN AIRLINES", "DELTA", "UNITED", "TAP", "TAP AIR PORTUGAL"
}

# Mapeamento de prefixos IATA para companhias aéreas
PREFIX_TO_COMPANY = {
    # Brasileiras
    "TP": "TAP",
    "AD": "AZUL",
    "G3": "GOL",
    "LA": "LATAM",
    "JJ": "LATAM",
    "LP": "LATAM",
    "AR": "AEROLINEAS ARGENTINAS",
    
    # Norte-Americanas
    "AA": "AMERICAN AIRLINES",
    "DL": "DELTA",
    "UA": "UNITED",
    
    # Europeias
    "AF": "AIR FRANCE",
    "KL": "KLM",
    "LH": "LUFTHANSA",
    "LX": "SWISS",
    "IB": "IBERIA",
    "BA": "BRITISH AIRWAYS",
    "TK": "TURKISH AIRLINES",
    
    # Oriente Médio e Ásia
    "QR": "QATAR AIRWAYS",
    "EK": "EMIRATES",
    "EY": "ETIHAD",
    "SQ": "SINGAPORE AIRLINES",
    
    # América Latina
    "CM": "COPA",
    "AV": "AVIANCA",
    "AM": "AEROMÉXICO",
    
    # Outras
    "ET": "ETHIOPIAN AIRLINES",
    "WJ": "JETSMART",
    "JA": "JETSMART",
    
    # Regionais e de 1 letra (para resgatar voos como A6509)
    "A6": "AIRFAST",  # Regional brasileira
    "A": "AVIANCA",   # Avianca regional (ex: A6509 para Bogotá)
    "B": "AZUL",      # Azul regional
    "C": "COPA"       # Copa regional
}

# ============================================================================
# VALIDAÇÃO DE DESTINOS
# ============================================================================
# Lista negra rigorosa de palavras que NUNCA são cidades/aeroportos
NON_CITY_WORDS = {
    "YOUTUBE", "INSTAGRAM", "FACEBOOK", "TWITTER", "DETALHES", "DETALHE", "VER MAIS", "AENA", 
    "TERMINAL", "VOLTAR", "CIA", "SKY", "EMBARQUE", "EMBARQUE PRÓXIMO", "EMBARQUE PROXIMO",
    "VOLTAR PARA À PÁGINA INICIAL", "VOLTAR PARA A PÁGINA INICIAL", "VOLTAR PARA A PAGINA INICIAL",
    "AEROPORTO", "PÁGINA INICIAL", "PAGINA INICIAL", "INICIAL", "PÁGINA", "PAGINA", "N/A", "GRU"
}

# Mantém DESTINOS_INVALIDOS para compatibilidade (usa NON_CITY_WORDS)
DESTINOS_INVALIDOS = NON_CITY_WORDS

# Lista de códigos IATA válidos conhecidos (para validação de tamanho)
VALID_IATA_CODES = {
    "SDU", "CGH", "GIG", "REC", "BSB", "FOR", "POA", "SSA",
    "BEL", "CNF", "FLN", "MAO", "PVH", "RBR", "AJU", "IOS",
    "CWB", "VIX", "THE", "IMP", "SLZ", "BVB", "JPA", "NAT",
    "CGB", "UDI", "GYN", "PMW", "BPS", "CPV", "FEN", "JDO",
    # Códigos internacionais comuns
    "CDG", "LIS", "MAD", "LHR", "FRA", "FCO", "BCN", "AMS",
    "MIA", "JFK", "MCO", "LAX", "YYZ", "MEX", "PTY", "EZE",
    "SCL", "LIM", "BOG", "MVD"
}

# Códigos IATA inválidos (que parecem códigos mas não são aeroportos)
INVALID_IATA_CODES = {"CIA", "SKY", "API", "CSS", "HTML", "JPG", "PNG", "SVG", "TAP", "N/A"}

# Dicionário de aeroportos (sigla IATA -> nome completo da cidade)
AIRPORT_DICT = {
    # Nacionais
    'SSA': 'Salvador', 'FOR': 'Fortaleza', 'CNF': 'Belo Horizonte', 'POA': 'Porto Alegre',
    'REC': 'Recife', 'CWB': 'Curitiba', 'BSB': 'Brasília', 'GIG': 'Rio de Janeiro (Galeão)',
    'SDU': 'Rio de Janeiro (Santos Dumont)', 'MAO': 'Manaus', 'NAT': 'Natal', 'MCZ': 'Maceió',
    'VIX': 'Vitória', 'FLN': 'Florianópolis', 'BEL': 'Belém', 'SLZ': 'São Luís',
    'CGB': 'Cuiabá', 'CGR': 'Campo Grande', 'GYN': 'Goiânia', 'PMW': 'Palmas',
    'AJU': 'Aracaju', 'THE': 'Teresina', 'PVH': 'Porto Velho', 'BVB': 'Boa Vista',
    'MCP': 'Macapá', 'RBR': 'Rio Branco', 'JPA': 'João Pessoa', 'PNZ': 'Petrolina',
    'IOS': 'Ilhéus', 'BPS': 'Porto Seguro', 'LDB': 'Londrina', 'MGF': 'Maringá',
    'NVT': 'Navegantes', 'XAP': 'Chapecó', 'RAO': 'Ribeirão Preto', 'SJP': 'São José do Rio Preto',
    'IMP': 'Imperatriz', 'UDI': 'Uberlândia', 'Pessoa': 'João Pessoa',  # Correção para o erro de corte
    # Internacionais Comuns em GRU
    'EZE': 'Buenos Aires', 'AEP': 'Buenos Aires', 'MIA': 'Miami', 'LHR': 'Londres',
    'MAD': 'Madrid', 'CDG': 'Paris', 'JFK': 'Nova York', 'DXB': 'Dubai',
    'LIS': 'Lisboa', 'FRA': 'Frankfurt', 'SCL': 'Santiago', 'BOG': 'Bogotá',  # Adicionado Bogotá
    'Bogotá': 'Bogotá', 'Bogota': 'Bogotá'  # CORREÇÃO 2: Permite busca direta por nome
}

# ============================================================================
# CIDADES CONHECIDAS (Keyword Matching)
# ============================================================================
# Lista exaustiva de cidades de destino (nacionais e internacionais) que operam em GRU
# Usado para reconhecimento de padrão - busca simples por keyword
KNOWN_CITIES = [
    # Nacionais
    "Brasília", "BSB", "Rio de Janeiro", "Galeão", "GIG", "Santos Dumont", "SDU",
    "Belo Horizonte", "CNF", "São Paulo", "CGH", "Salvador", "SSA",
    "Fortaleza", "FOR", "Recife", "REC", "Curitiba", "CWB", "Porto Alegre", "POA",
    "Manaus", "MAO", "Natal", "NAT", "Maceió", "MCZ", "Vitória", "VIX",
    "Florianópolis", "FLN", "Belém", "BEL", "São Luís", "SLZ", "Cuiabá", "CGB",
    "Campo Grande", "CGR", "Goiânia", "GYN", "Palmas", "PMW", "Aracaju", "AJU",
    "Teresina", "THE", "Porto Velho", "PVH", "Boa Vista", "BVB", "Macapá", "MCP",
    "Rio Branco", "RBR", "João Pessoa", "JPA", "Petrolina", "PNZ", "Ilhéus", "IOS",
    "Porto Seguro", "BPS", "Londrina", "LDB", "Maringá", "MGF", "Navegantes", "NVT",
    "Chapecó", "XAP", "Ribeirão Preto", "RAO", "São José do Rio Preto", "SJP",
    "Imperatriz", "IMP", "Uberlândia", "UDI",
    
    # Internacionais - América do Sul
    "Bogotá", "Bogota", "BOG", "Santiago", "SCL", "Buenos Aires", "EZE", "AEP",
    "Lima", "LIM", "Montevidéu", "MVD", "Caracas", "CCS", "Quito", "UIO",
    
    # Internacionais - América do Norte
    "Miami", "MIA", "Nova York", "JFK", "New York", "Orlando", "MCO",
    "Los Angeles", "LAX", "Toronto", "YYZ", "Cidade do México", "MEX",
    
    # Internacionais - Europa
    "Londres", "LHR", "Madrid", "MAD", "Paris", "CDG", "Frankfurt", "FRA",
    "Lisboa", "LIS", "Roma", "FCO", "Amsterdã", "AMS", "Zurique", "ZRH",
    "Barcelona", "BCN", "Milão", "MXP", "Munique", "MUC",
    
    # Internacionais - Oriente Médio e Ásia
    "Dubai", "DXB", "Doha", "DOH", "Abu Dhabi", "AUH", "Istambul", "IST",
    "Tel Aviv", "TLV", "Singapura", "SIN", "Bangkok", "BKK", "Tóquio", "NRT",
    
    # Outras
    "Cidade do Panamá", "PTY", "San José", "SJO"
]

# ============================================================================
# STATUS
# ============================================================================
# CORREÇÃO 2: Ampliação de status para incluir 'Voo encerrado', 'Confirmado' e 'Cancelado'
STATUS_ALVO = [
    "Embarque Próximo",
    "Imediato Embarque",
    "Última Chamada",
    "Voo encerrado",  # CORREÇÃO 2
    "Confirmado",     # CORREÇÃO 2
    "Cancelado"       # CORREÇÃO 2
]

# ============================================================================
# STATUS MONITORED FOR OPERATIONAL STABILITY ANALYSIS
# ============================================================================
# Status monitored for operational disruption analysis (IROPS - Irregular Operations)
# Tracks schedule deviations, cancellations, and operational anomalies
# Based on IATA/ICAO standards for operational performance metrics
STATUS_OPERATIONAL_DISRUPTIONS = [
    "Cancelado",
    "Cancelado/Procure Cia.",  # Found in previous logs
    "Atrasado",
    "Adiado",
    "Em atraso",
    "Procure Cia",
    "Voo encerrado",  # Keep for recent history
    "Estimado",       # Frequently indicates new schedule estimate
    "Nova Previsão",
    "Consulte Cia",
    "Nova Hora",      # Indicates new scheduled time
    "Alterado",       # Flight with schedule changes
    "Atraso",         # Short variation of "Atrasado"
]

# ============================================================================
# OPERATIONAL METRICS LOGGING PATHS
# ============================================================================
DIR_LOGS_OPERATIONAL_METRICS = "logs_operational_metrics"
CSV_PREFIX_OPERATIONAL_REPORT = "operational_report"

# ============================================================================
# USER-AGENTS ROTATIVOS
# ============================================================================
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# ============================================================================
# PERMISSÕES macOS
# ============================================================================
# Define TMPDIR para evitar erros de permissão
os.environ["TMPDIR"] = os.path.expanduser("~/Downloads")
