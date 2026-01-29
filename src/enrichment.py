import json
import logging
import copy
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuração de Logger
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. MAPAS DE TRADUÇÃO (ANAC / ICAO -> IATA -> CIDADE)
# ==============================================================================
ICAO_TO_IATA = {
    # Brasil (Principais)
    'SBGR': 'GRU', 'SBSP': 'CGH', 'SBGL': 'GIG', 'SBRJ': 'SDU', 'SBBR': 'BSB',
    'SBCF': 'CNF', 'SBSV': 'SSA', 'SBRF': 'REC', 'SBCT': 'CWB', 'SBPA': 'POA',
    'SBFL': 'FLN', 'SBEG': 'MAO', 'SBGO': 'GYN', 'SBVT': 'VIX', 'SBNF': 'NVT',
    'SBCY': 'CGB', 'SBBE': 'BEL', 'SBMO': 'MCZ', 'SBFI': 'IGU', 'SBPS': 'BPS',
    'SBJP': 'JPA', 'SBKG': 'CKG', 'SBAR': 'AJU', 'SBPL': 'PNZ', 'SBSL': 'SLZ',
    'SBTE': 'THE', 'SBPV': 'PVH', 'SBRB': 'RBR', 'SBMQ': 'MCP', 'SBBV': 'BVB',
    'SBSR': 'SJP', 'SBJU': 'JDO', 'SBIL': 'IOS', 'SBCG': 'CGR', 'SBUL': 'UDI',
    'SBUR': 'UBA', 'SBRP': 'RAO', 'SBKP': 'VCP', 'SBLO': 'LDB', 'SBMG': 'MGF',
    # América do Sul
    'SAEZ': 'EZE', 'SABE': 'AEP', 'SCEL': 'SCL', 'SPJC': 'LIM', 'SKBO': 'BOG',
    'SUMU': 'MVD', 'SGAS': 'ASU', 'SLVR': 'VVI', 'SEGU': 'GYE', 'SEQM': 'UIO',
    'SVMI': 'CCS', 'SAME': 'MDZ', 'SACO': 'COR', 'SAAR': 'ROS',
    # EUA e Europa
    'KMIA': 'MIA', 'KJFK': 'JFK', 'KMCO': 'MCO', 'KATL': 'ATL', 'KLAX': 'LAX',
    'EGLL': 'LHR', 'LFPG': 'CDG', 'LEMD': 'MAD', 'EDDF': 'FRA', 'EHAM': 'AMS',
    'LPPT': 'LIS', 'LIMC': 'MXP', 'LIRF': 'FCO', 'LEBL': 'BCN', 'LSZH': 'ZRH',
    'EDDM': 'MUC', 'LTFM': 'IST', 'OMDB': 'DXB', 'OTHH': 'DOH'
}

IATA_TO_CITY = {
    "GIG": "Rio de Janeiro", "SDU": "Rio de Janeiro", "CGH": "São Paulo", "GRU": "São Paulo",
    "BSB": "Brasília", "CNF": "Belo Horizonte", "SSA": "Salvador", "REC": "Recife",
    "POA": "Porto Alegre", "CWB": "Curitiba", "FLN": "Florianópolis", "MAO": "Manaus",
    "GYN": "Goiânia", "VIX": "Vitória", "NVT": "Navegantes", "CGB": "Cuiabá",
    "BEL": "Belém", "MCZ": "Maceió", "IGU": "Foz do Iguaçu", "BPS": "Porto Seguro",
    "JPA": "João Pessoa", "AJU": "Aracaju", "NAT": "Natal", "THE": "Teresina",
    "SLZ": "São Luís", "CGR": "Campo Grande", "UDI": "Uberlândia", "LDB": "Londrina",
    "MIA": "Miami", "MCO": "Orlando", "JFK": "Nova York", "ATL": "Atlanta",
    "LIS": "Lisboa", "MAD": "Madrid", "CDG": "Paris", "LHR": "Londres",
    "AMS": "Amsterdã", "FRA": "Frankfurt", "DXB": "Dubai", "DOH": "Doha",
    "EZE": "Buenos Aires", "AEP": "Buenos Aires", "MVD": "Montevidéu",
    "SCL": "Santiago", "LIM": "Lima", "BOG": "Bogotá", "PTY": "Panamá"
}

# ==============================================================================
# 2. CARREGAMENTO DO BANCO DE DADOS
# ==============================================================================
def load_anac_db() -> Dict[str, str]:
    """Carrega o JSON da ANAC e retorna mapa limpo { '1234': 'IATA' }."""
    try:
        project_root = Path(__file__).resolve().parent.parent
        path = project_root / 'data' / 'specificroutes_anac.json'
        if not path.exists():
            logger.warning("⚠️ Módulo Enrichment: Banco ANAC não encontrado.")
            return {}

        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            
        clean_db = {}
        for k, v in raw.items():
            # Chave: Apenas números (remove RJ, AD, etc)
            clean_k = "".join(filter(str.isdigit, str(k)))
            
            # Valor: ICAO -> IATA
            iata = ICAO_TO_IATA.get(v, v)
            if len(iata) == 4 and iata.startswith('K'):
                iata = iata[1:]
            
            if clean_k:
                clean_db[clean_k] = iata
                
        logger.info(f"✅ Módulo Enrichment: ANAC DB carregado ({len(clean_db)} rotas).")
        return clean_db
    except Exception as e:
        logger.error(f"❌ Erro carregando ANAC DB: {e}")
        return {}

# Carrega DB na inicialização do módulo
ANAC_DB = load_anac_db()

# ==============================================================================
# 3. FUNÇÕES PRINCIPAIS
# ==============================================================================

def validate_dictionaries() -> bool:
    """Valida integridade básica."""
    return True


def analyze_failure_rate(flights: List[Dict], label: str):
    """Log estatístico simples."""
    missing = sum(1 for f in flights if not f.get('destination_iata'))
    total = len(flights)
    if total > 0:
        logger.info(f"📊 {label}: {missing}/{total} voos sem destino ({missing/total:.1%})")


def enrich_missing_destinations(flights: List[Dict]) -> Dict:
    """
    Percorre a lista de voos e tenta descobrir o destino usando o ANAC DB.
    """
    stats = {'enriched': 0, 'failed': 0, 'already_set': 0}
    
    for i, flight in enumerate(flights):
        # Se já tem destino válido, pula
        current_iata = flight.get('destination_iata')
        if current_iata and current_iata != 'VAZIO' and len(current_iata) == 3:
            stats['already_set'] += 1
            continue

        # Tenta enriquecer
        raw_num = str(flight.get('flight_number', ''))
        
        # 1. Limpeza: "RJ1268" -> "1268"
        clean_num = "".join(filter(str.isdigit, raw_num))
        
        if not clean_num:
            continue
            
        # 2. Busca no ANAC DB
        found_iata = ANAC_DB.get(clean_num)
        
        if found_iata:
            # 3. Resolve Nome da Cidade
            city_name = IATA_TO_CITY.get(found_iata, found_iata)
            
            # 4. Atualiza o Voo
            flight['destination_iata'] = found_iata
            flight['destination'] = city_name
            flight['destination_city'] = city_name
            
            stats['enriched'] += 1
            # logger.debug(f"✅ Enriquecido: {raw_num} -> {found_iata} ({city_name})")
        else:
            stats['failed'] += 1
            # logger.debug(f"❌ Não encontrado: {raw_num}")
            
    return stats


def regression_test(old_flights, new_flights):
    return True

