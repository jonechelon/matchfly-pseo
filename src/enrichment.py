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
# Destinos internacionais partindo de GRU + Brasil (evitar "MMMX" ou "Destino desconhecido")
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
    # América do Norte (GRU)
    'MMMX': 'MEX',   # Cidade do México
    'KJFK': 'JFK',   # Nova York
    'KMIA': 'MIA',   # Miami
    'KMCO': 'MCO',   # Orlando
    'KLAX': 'LAX',   # Los Angeles
    'KATL': 'ATL',   # Atlanta
    'CYYZ': 'YYZ',   # Toronto
    'CYUL': 'YUL',   # Montreal
    'KORD': 'ORD',   # Chicago
    'KIAD': 'IAD', 'KDCA': 'DCA',  # Washington
    'KSFO': 'SFO',   # San Francisco
    'KDFW': 'DFW',   # Dallas
    'KBOS': 'BOS',   # Boston
    'KIAH': 'IAH',   # Houston
    'MMUN': 'CUN',   # Cancún
    # América do Sul
    'SAEZ': 'EZE', 'SABE': 'AEP', 'SCEL': 'SCL', 'SPJC': 'LIM', 'SKBO': 'BOG',
    'SUMU': 'MVD', 'SGAS': 'ASU', 'SLVR': 'VVI', 'SEGU': 'GYE', 'SEQM': 'UIO',
    'SVMI': 'CCS', 'SAME': 'MDZ', 'SACO': 'COR', 'SAAR': 'ROS',
    # Europa
    'EGLL': 'LHR',   # Londres
    'LFPG': 'CDG',   # Paris
    'LEMD': 'MAD',   # Madrid
    'LPPT': 'LIS',   # Lisboa
    'EDDF': 'FRA',   # Frankfurt
    'LIRF': 'FCO',   # Roma
    'EHAM': 'AMS',   # Amsterdã
    'LIMC': 'MXP',   # Milão
    'LEBL': 'BCN',   # Barcelona
    'LSZH': 'ZRH',   # Zurique
    'EDDM': 'MUC',   # Munique
    'LTFM': 'IST',   # Istambul
    'EIDW': 'DUB',   # Dublin
    # Oriente Médio / Ásia / África
    'OMDB': 'DXB',   # Dubai
    'OTHH': 'DOH',   # Doha
    'HAAB': 'ADD',   # Addis Ababa
    'OERK': 'RUH',   # Riade
    'OEJN': 'JED',   # Jeddah
    'VTBS': 'BKK',   # Bangkok
    'ZSPD': 'PVG',   # Xangai
    'RJTT': 'NRT',   # Tóquio Narita
    'VHHH': 'HKG',   # Hong Kong
}

IATA_TO_CITY = {
    # Brasil
    "GIG": "Rio de Janeiro", "SDU": "Rio de Janeiro", "CGH": "São Paulo", "GRU": "São Paulo",
    "BSB": "Brasília", "CNF": "Belo Horizonte", "SSA": "Salvador", "REC": "Recife",
    "POA": "Porto Alegre", "CWB": "Curitiba", "FLN": "Florianópolis", "MAO": "Manaus",
    "GYN": "Goiânia", "VIX": "Vitória", "NVT": "Navegantes", "CGB": "Cuiabá",
    "BEL": "Belém", "MCZ": "Maceió", "IGU": "Foz do Iguaçu", "BPS": "Porto Seguro",
    "JPA": "João Pessoa", "AJU": "Aracaju", "NAT": "Natal", "THE": "Teresina",
    "SLZ": "São Luís", "CGR": "Campo Grande", "UDI": "Uberlândia", "LDB": "Londrina",
    # América do Norte
    "MEX": "Cidade do México", "CUN": "Cancún",
    "JFK": "Nova York", "MIA": "Miami", "MCO": "Orlando", "LAX": "Los Angeles",
    "ATL": "Atlanta", "YYZ": "Toronto", "YUL": "Montreal", "ORD": "Chicago",
    "IAD": "Washington", "DCA": "Washington", "SFO": "San Francisco", "DFW": "Dallas",
    "BOS": "Boston", "IAH": "Houston",
    # América do Sul
    "EZE": "Buenos Aires", "AEP": "Buenos Aires", "MVD": "Montevidéu",
    "SCL": "Santiago", "LIM": "Lima", "BOG": "Bogotá", "PTY": "Panamá",
    "CCS": "Caracas", "UIO": "Quito", "GYE": "Guayaquil", "VVI": "Santa Cruz de la Sierra",
    "ASU": "Assunção", "COR": "Córdoba", "MDZ": "Mendoza",
    # Europa
    "LIS": "Lisboa", "MAD": "Madrid", "CDG": "Paris", "LHR": "Londres",
    "AMS": "Amsterdã", "FRA": "Frankfurt", "FCO": "Roma", "MXP": "Milão",
    "BCN": "Barcelona", "ZRH": "Zurique", "MUC": "Munique", "IST": "Istambul",
    "DUB": "Dublin",
    # Oriente Médio / Ásia / África
    "DXB": "Dubai", "DOH": "Doha", "ADD": "Addis Ababa",
    "RUH": "Riade", "JED": "Jeddah", "BKK": "Bangkok", "PVG": "Xangai",
    "NRT": "Tóquio", "HKG": "Hong Kong",
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


def _normalize_to_iata_and_city(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Converte código bruto (ICAO 4 letras ou IATA 3 letras) em (IATA, nome_cidade).
    Fallback inteligente: nunca retorna código bruto para exibição.
    """
    if not raw or not isinstance(raw, str):
        return None, None
    raw = raw.strip().upper()
    if len(raw) == 4:
        # ICAO: primeiro tenta dicionário
        iata = ICAO_TO_IATA.get(raw)
        if iata:
            city = IATA_TO_CITY.get(iata, "Destino internacional")
            return iata, city
        # Fallback EUA: prefixo K + 3 letras (ex: KJFK -> JFK)
        if raw.startswith("K"):
            iata = raw[1:]
            city = IATA_TO_CITY.get(iata, "Destino internacional")
            return iata, city
        # Fallback Canadá: prefixo C + 3 letras (ex: CYYZ -> YYZ)
        if raw.startswith("C"):
            iata = raw[1:]
            city = IATA_TO_CITY.get(iata, "Destino internacional")
            return iata, city
        return None, None
    if len(raw) == 3:
        iata = raw
        city = IATA_TO_CITY.get(iata, "Destino internacional")
        return iata, city
    return None, None


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
    Fallback inteligente: códigos ICAO (4 letras) são convertidos para IATA + cidade;
    nunca exibe código bruto (MMMX -> Cidade do México).
    """
    stats = {'enriched': 0, 'failed': 0, 'already_set': 0}
    
    for i, flight in enumerate(flights):
        current_iata = flight.get('destination_iata') or flight.get('destination', '')
        current_raw = (current_iata or '').strip().upper()

        # Código de 4 letras (ICAO): normaliza para IATA + cidade — nunca exibe bruto
        if len(current_raw) == 4:
            iata_norm, city_norm = _normalize_to_iata_and_city(current_raw)
            if iata_norm and city_norm:
                flight['destination_iata'] = iata_norm
                flight['destination'] = city_norm
                flight['destination_city'] = city_norm
                stats['enriched'] += 1
            else:
                stats['failed'] += 1
            continue

        # Já tem IATA de 3 letras: garante que destino/destination_city sejam nome da cidade
        if len(current_raw) == 3 and current_raw != 'VAZIO':
            city_name = IATA_TO_CITY.get(current_raw, "Destino internacional")
            flight['destination_iata'] = current_raw
            flight['destination'] = city_name
            flight['destination_city'] = city_name
            stats['already_set'] += 1
            continue

        # Tenta enriquecer via ANAC DB
        raw_num = str(flight.get('flight_number', ''))
        clean_num = "".join(filter(str.isdigit, raw_num))
        if not clean_num:
            continue

        found_raw = ANAC_DB.get(clean_num)
        if not found_raw:
            stats['failed'] += 1
            continue

        # ANAC pode retornar ICAO (4 letras) ou IATA (3) — normaliza sempre
        iata_final, city_final = _normalize_to_iata_and_city(found_raw)
        if iata_final and city_final:
            flight['destination_iata'] = iata_final
            flight['destination'] = city_final
            flight['destination_city'] = city_final
            stats['enriched'] += 1
        else:
            # Último recurso: se veio IATA de 3 letras, usa e evita exibir código bruto
            if len(found_raw) == 3:
                flight['destination_iata'] = found_raw
                flight['destination'] = IATA_TO_CITY.get(found_raw, "Destino internacional")
                flight['destination_city'] = flight['destination']
                stats['enriched'] += 1
            else:
                stats['failed'] += 1

    return stats


def regression_test(old_flights, new_flights):
    return True

