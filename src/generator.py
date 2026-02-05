#!/usr/bin/env python3
"""
MatchFly Static Page Generator - Production Grade
==================================================
Sistema de geração de páginas estáticas com:
- Gestão de órfãos (arquivos antigos)
- Geração de sitemap.xml
- Auditoria completa de builds
- Resiliência total (try/except por voo)

Author: MatchFly Team
Date: 2026-01-11
Version: 2.0.0
"""

import json
import logging
import os
import random
import sys
import subprocess
import hashlib
import re
from collections import defaultdict, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
from slugify import slugify
from jinja2 import Environment, FileSystemLoader, Template
import xml.etree.ElementTree as ET
from xml.dom import minidom

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Importa módulo de enriquecimento
import copy
try:
    import enrichment as enrichment_module
except ImportError:
    # Fallback para quando executado como módulo
    import src.enrichment as enrichment_module

# Exposição explícita do banco ANAC carregado no módulo de enrichment
ANAC_DB = getattr(enrichment_module, "ANAC_DB", {})

# Correções de destino (viés SCL) — prioridade máxima no pipeline
try:
    from src.scl_corrections import CORRECTIONS_DICT
except ImportError:
    from scl_corrections import CORRECTIONS_DICT

# Diretório do projeto (raiz) para paths relativos
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Configuração de logging (logs em logs/generator.log)
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def safe_str(val):
    """Converte qualquer valor para string limpa, evitando erro de float/None."""
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() == 'nan':
        return ""
    return s


def parse_flight_time(flight: Dict) -> datetime:
    """
    Converte data/hora do voo em datetime para ordenação.
    Prioriza 'Data_Captura' para garantir que voos novos (31/01) fiquem no topo.
    """
    try:
        # 1. Tenta pegar a data de captura (Coluna Data_Captura ou scraped_at)
        date_iso = safe_str(flight.get('Data_Captura') or flight.get('scraped_at'))

        # 2. Tenta pegar o horário (Coluna Horario ou scheduled_time)
        time_str = safe_str(flight.get('scheduled_time') or flight.get('Horario') or '00:00')

        # Limpeza: Garante formato HH:MM (remove segundos se vier 11:05:00)
        if len(time_str) > 5:
            time_str = time_str[:5]

        # LÓGICA 1: Tenta formato ISO (YYYY-MM-DD)
        if date_iso and '-' in date_iso:
            # Limpa separador T se existir (2026-01-31T10:00 -> 2026-01-31)
            date_clean = date_iso.replace('T', ' ').split(' ')[0]
            return datetime.strptime(f"{date_clean} {time_str}", "%Y-%m-%d %H:%M")

        # LÓGICA 2: Tenta formato Brasileiro com barras (DD/MM/YYYY ou DD/MM)
        if date_iso and '/' in date_iso:
            parts = date_iso.split('/')
            if len(parts) == 3:  # Formato completo dd/mm/yyyy
                return datetime.strptime(f"{parts[2]}-{parts[1]}-{parts[0]} {time_str}", "%Y-%m-%d %H:%M")
            if len(parts) == 2:  # Formato curto dd/mm (assume ano atual)
                day, month = parts[0], parts[1]
                year = datetime.now().year
                return datetime.strptime(f"{year}-{month}-{day} {time_str}", "%Y-%m-%d %H:%M")

        # LÓGICA 3: Fallback para Data_Partida se Data_Captura falhar
        date_br = safe_str(flight.get('date_raw') or flight.get('data_partida') or '')
        if date_br and '/' in date_br:
            parts = date_br.split('/')
            if len(parts) >= 2:
                day = parts[0]
                month = parts[1]
                year = "2026"
                return datetime.strptime(f"{year}-{month}-{day} {time_str}", "%Y-%m-%d %H:%M")

        # Se não tiver data nenhuma, vai para o fim da fila
        return datetime.min

    except Exception:
        return datetime.min


def format_date_time_fmt(flight_or_page: Dict) -> str:
    """
    Formata data e hora para exibição em cards: "dd/mm às HH:MM".
    Usado na Home e em listas por cidade para mostrar ordem temporal.
    """
    data = safe_str(flight_or_page.get('data_partida', ''))
    time_part = safe_str(flight_or_page.get('display_time', ''))
    if not time_part:
        st = safe_str(flight_or_page.get('scheduled_time', ''))
        if st and ' ' in st:
            time_part = st.split(' ')[-1][:5]
        elif st and ':' in st and len(st) <= 5:
            time_part = st[:5]
        elif st:
            try:
                dt = datetime.fromisoformat(st.replace('Z', '').split('+')[0].split('.')[0])
                time_part = dt.strftime('%H:%M')
            except Exception:
                pass
    if data and '/' in data:
        parts = data.split('/')
        if len(parts) >= 2:
            data = f"{parts[0]}/{parts[1]}"
    if data and time_part:
        return f"{data} às {time_part}"
    if data:
        return data
    return ''


# ==============================================================================
# 1. Tradutor ICAO (4 letras) -> IATA (3 letras)
ICAO_TO_IATA = {
    # Principais Capitais Brasileiras
    'SBGR': 'GRU', 'SBSP': 'CGH', 'SBGL': 'GIG', 'SBRJ': 'SDU', 'SBBR': 'BSB',
    'SBCF': 'CNF', 'SBSV': 'SSA', 'SBRF': 'REC', 'SBCT': 'CWB', 'SBPA': 'POA',
    'SBFL': 'FLN', 'SBEG': 'MAO', 'SBGO': 'GYN', 'SBVT': 'VIX', 'SBNF': 'NVT',
    'SBCY': 'CGB', 'SBBE': 'BEL', 'SBMO': 'MCZ', 'SBFI': 'IGU', 'SBPS': 'BPS',
    'SBJP': 'JPA', 'SBKG': 'CKG', 'SBAR': 'AJU', 'SBPL': 'PNZ', 'SBSL': 'SLZ',
    'SBTE': 'THE', 'SBPV': 'PVH', 'SBRB': 'RBR', 'SBMQ': 'MCP', 'SBBV': 'BVB',
    'SBSR': 'SJP', 'SBJU': 'JDO', 'SBIL': 'IOS', 'SBCG': 'CGR', 'SBUL': 'UDI',
    # Internacionais Comuns em GRU
    'KMIA': 'MIA', 'KJFK': 'JFK', 'KMCO': 'MCO', 'KATL': 'ATL', 'KLAX': 'LAX',
    'EGLL': 'LHR', 'LFPG': 'CDG', 'LEMD': 'MAD', 'EDDF': 'FRA', 'EHAM': 'AMS',
    'LPPT': 'LIS', 'LIMC': 'MXP', 'LIRF': 'FCO', 'LEBL': 'BCN', 'LSZH': 'ZRH',
    'SAEZ': 'EZE', 'SABE': 'AEP', 'SCEL': 'SCL', 'SPJC': 'LIM', 'SKBO': 'BOG',
    'SUMU': 'MVD', 'SGAS': 'ASU', 'SLVR': 'VVI', 'OMDB': 'DXB', 'OTHH': 'DOH'
}

# 2. Tradutor IATA (3 letras) -> Nome da Cidade (Display)
IATA_TO_CITY_NAME = {
    # --- BRASIL (Capitais e Principais) ---
    "GIG": "Rio de Janeiro", "SDU": "Rio de Janeiro", 
    "CGH": "São Paulo", "GRU": "São Paulo", "VCP": "Campinas",
    "BSB": "Brasília", "CNF": "Belo Horizonte", "SSA": "Salvador", 
    "REC": "Recife", "POA": "Porto Alegre", "CWB": "Curitiba", 
    "FLN": "Florianópolis", "MAO": "Manaus", "GYN": "Goiânia", 
    "VIX": "Vitória", "NVT": "Navegantes", "CGB": "Cuiabá",
    "BEL": "Belém", "MCZ": "Maceió", "IGU": "Foz do Iguaçu", 
    "BPS": "Porto Seguro", "JPA": "João Pessoa", "AJU": "Aracaju", 
    "NAT": "Natal", "THE": "Teresina", "SLZ": "São Luís", 
    "CGR": "Campo Grande", "UDI": "Uberlândia", "LDB": "Londrina",
    "MGF": "Maringá", "RAO": "Ribeirão Preto", "SJP": "São José do Rio Preto",
    "JOI": "Joinville", "XAP": "Chapecó", "PVH": "Porto Velho",
    "RBR": "Rio Branco", "MCP": "Macapá", "PMW": "Palmas",
    "JDO": "Juazeiro do Norte", "IOS": "Ilhéus", "FEN": "Fernando de Noronha",
    
    # --- AMÉRICA DO SUL ---
    "EZE": "Buenos Aires", "AEP": "Buenos Aires", # Argentina
    "MVD": "Montevidéu", # Uruguai
    "SCL": "Santiago", # Chile
    "LIM": "Lima", # Peru
    "BOG": "Bogotá", # Colômbia
    "ASU": "Assunção", # Paraguai
    "VVI": "Santa Cruz de la Sierra", # Bolívia
    "COR": "Córdoba", "ROS": "Rosário", "MDZ": "Mendoza", # Argentina Interior
    "CLO": "Cali", "MDE": "Medellín", # Colômbia Interior
    "UIO": "Quito", "GYE": "Guayaquil", # Equador
    "CCS": "Caracas", # Venezuela
    
    # --- AMÉRICA DO NORTE ---
    "MIA": "Miami", "MCO": "Orlando", "JFK": "Nova York", 
    "EWR": "Nova York (Newark)", "ATL": "Atlanta", "LAX": "Los Angeles",
    "BOS": "Boston", "IAD": "Washington", "ORD": "Chicago",
    "IAH": "Houston", "DFW": "Dallas", "LAS": "Las Vegas",
    "SFO": "San Francisco", "YUL": "Montreal", "YYZ": "Toronto",
    "MEX": "Cidade do México", "CUN": "Cancún", "PTY": "Panamá",
    
    # --- EUROPA ---
    "LIS": "Lisboa", "OPO": "Porto", # Portugal
    "MAD": "Madrid", "BCN": "Barcelona", # Espanha
    "CDG": "Paris", "ORY": "Paris", # França
    "LHR": "Londres", "LGW": "Londres", # Reino Unido
    "AMS": "Amsterdã", # Holanda
    "FRA": "Frankfurt", "MUC": "Munique", # Alemanha
    "FCO": "Roma", "MXP": "Milão", # Itália
    "ZRH": "Zurique", # Suíça
    "IST": "Istambul", # Turquia
    
    # --- ORIENTE MÉDIO E ÁFRICA ---
    "DXB": "Dubai", "DOH": "Doha", "TLV": "Tel Aviv",
    "JNB": "Joanesburgo", "CPT": "Cidade do Cabo", 
    "ADD": "Adis Abeba", "LAD": "Luanda"
}


# ============================================================
# PARTE 1: MAPEAMENTO DE CIDADES PARA CÓDIGOS IATA
# ============================================================
# Dicionário expandido com principais destinos nacionais e internacionais
# Garante pré-preenchimento automático do funil AirHelp para maximizar conversão
CITY_TO_IATA = {
    # ========== INTERNACIONAIS ==========
    # Europa
    "paris": "CDG",
    "lisboa": "LIS",
    "madrid": "MAD",
    "londres": "LHR",
    "frankfurt": "FRA",
    "roma": "FCO",
    "barcelona": "BCN",
    "amsterdã": "AMS",
    "amsterdam": "AMS",
    "zurique": "ZRH",
    "milão": "MXP",
    "milao": "MXP",
    
    # América do Sul
    "buenos aires": "EZE",
    "santiago": "SCL",
    "lima": "LIM",
    "bogotá": "BOG",
    "bogota": "BOG",
    "montevideo": "MVD",
    "montevidéu": "MVD",
    
    # América do Norte
    "miami": "MIA",
    "nova york": "JFK",
    "new york": "JFK",
    "orlando": "MCO",
    "los angeles": "LAX",
    "toronto": "YYZ",
    "cidade do méxico": "MEX",
    "mexico city": "MEX",
    "panamá": "PTY",
    "panama": "PTY",
    
    # ========== NACIONAIS (Principais fluxos de GRU) ==========
    "rio de janeiro": "GIG",
    "brasília": "BSB",
    "brasilia": "BSB",
    "belo horizonte": "CNF",
    "salvador": "SSA",
    "fortaleza": "FOR",
    "recife": "REC",
    "porto alegre": "POA",
    "curitiba": "CWB",
    "florianópolis": "FLN",
    "florianopolis": "FLN",
    "goiânia": "GYN",
    "goiania": "GYN",
    "cuiabá": "CGB",
    "cuiaba": "CGB",
    "manaus": "MAO",
    "belém": "BEL",
    "belem": "BEL",
    "natal": "NAT",
    "maceió": "MCZ",
    "maceio": "MCZ",
    "vitória": "VIX",
    "vitoria": "VIX",
    "foz do iguaçu": "IGU",
    "foz do iguacu": "IGU",
    "porto seguro": "BPS",
    "aracaju": "AJU",
    "joão pessoa": "JPA",
    "joao pessoa": "JPA",
    "são luís": "SLZ",
    "sao luis": "SLZ",
    "teresina": "THE",
    "campo grande": "CGR",
}

# Mapeamento Reverso (IATA -> Cidade) para Display
IATA_TO_CITY = {
    "DXB": "Dubai",
    "ATL": "Atlanta",
    "JFK": "Nova York",
    "MIA": "Miami",
    "MCO": "Orlando",
    "CDG": "Paris",
    "LIS": "Lisboa",
    "MAD": "Madrid",
    "LHR": "Londres",
    "AMS": "Amsterdã",
    "FRA": "Frankfurt",
    "SCL": "Santiago",
    "EZE": "Buenos Aires",
    "MVD": "Montevidéu",
    "PTY": "Panamá",
    "MEX": "Cidade do México",
    "BOG": "Bogotá",
    "LIM": "Lima",
    "GIG": "Rio de Janeiro",
    "GRU": "São Paulo",
    "BSB": "Brasília",
    "CNF": "Belo Horizonte",
    "SSA": "Salvador",
    "REC": "Recife",
    "FOR": "Fortaleza",
    "CWB": "Curitiba",
    "POA": "Porto Alegre",
    "MAO": "Manaus",
    "BEL": "Belém",
    "FLN": "Florianópolis",
    "GYN": "Goiânia",
    "VIX": "Vitória",
    "CGB": "Cuiabá",
    "NAT": "Natal",
    "MCZ": "Maceió",
    "IGU": "Foz do Iguaçu",
    "AEP": "Buenos Aires (Aeroparque)",
    "CGH": "São Paulo (Congonhas)",
    "SDU": "Rio (Santos Dumont)",
}
# Popula o restante automaticamente do dicionário original
for k, v in CITY_TO_IATA.items():
    if v and v not in IATA_TO_CITY:
        IATA_TO_CITY[v] = k.title()


def resolve_city_name(iata: str, current_name: str) -> str:
    """Retorna o nome da cidade baseado no IATA se o atual for inválido."""
    iata = safe_str(iata)
    current_name = safe_str(current_name)
    if current_name and current_name not in ["N/A", "Aguardando atualização", "VAZIO"]:
        return current_name
    return IATA_TO_CITY.get(iata, current_name or "")


# Lista de códigos IATA brasileiros para identificar voos nacionais
BRAZILIAN_AIRPORTS = {
    "GRU", "GIG", "BSB", "SSA", "FOR", "REC", "POA", "CWB", "CNF",
    "MAO", "BEL", "FLN", "VIX", "NAT", "JPA", "MCZ", "AJU", "SLZ",
    "THE", "CGR", "CGB", "GYN", "VCP", "CGH", "SDU"
}


# ==============================================================================
# ROTAS REAIS E CONFIRMADAS DE GUARULHOS (GRU) - BASE ANAC + LATAM MANUAL
# Mapeia Número do Voo -> Código IATA do Destino
# ==============================================================================
KNOWN_ROUTES = {
    "104": "ATL", "1070": "GIG", "1071": "AJU", "1105": "MVD", "1112": "MGF", "1118": "CWB",
    "1128": "CWB", "1135": "SCL", "1144": "GIG", "1146": "JJD", "1148": "CWB", "1152": "REC",
    "1156": "XAP", "1160": "SSA", "1164": "CWB", "1166": "SSA", "1170": "IGU", "1172": "IGU",
    "1174": "IGU", "1178": "JPA", "1190": "FEN", "1203": "AEP", "1220": "NVT", "1224": "POA",
    "1226": "FLN", "1234": "NVT", "1236": "POA", "1237": "AEP", "1241": "AEP", "1243": "AEP",
    "1244": "POA", "1249": "AEP", "1250": "NVT", "1252": "NVT", "1258": "NVT", "1262": "NVT",
    "1268": "AEP", "1274": "POA", "1276": "POA", "1284": "CNF", "1290": "CNF", "1296": "CNF",
    "1300": "CNF", "1306": "CNF", "1314": "VCP", "1316": "VCP", "1320": "VCP", "1322": "VCP",
    "1324": "VCP", "1326": "VCP", "1328": "VCP", "1330": "VCP", "1332": "VCP", "1334": "VCP",
    "1338": "VCP", "1342": "VCP", "1344": "VCP", "1346": "VCP", "1360": "UDI", "1366": "UDI",
    "1374": "SSA", "1376": "SSA", "1380": "SSA", "1384": "SSA", "1386": "SSA", "1392": "ILH",
    "1396": "ILH", "1402": "BPS", "1406": "BPS", "1412": "VIX", "1414": "VIX", "1416": "VIX",
    "1420": "VIX", "1422": "VIX", "1430": "GYN", "1432": "GYN", "1436": "GYN", "1438": "GYN",
    "1440": "GYN", "1442": "BSB", "1446": "BSB", "1448": "BSB", "1450": "BSB", "1452": "BSB",
    "1454": "BSB", "1464": "CGB", "1468": "CGB", "1472": "CGB", "1486": "RAO", "1490": "RAO",
    "1492": "RAO", "1494": "RAO", "1498": "SJP", "1500": "SJP", "1504": "SJP", "1506": "SJP",
    "1510": "CXJ", "1512": "CXJ", "1520": "REC", "1522": "DXB", "1524": "REC", "1530": "REC",
    "1532": "REC", "1534": "MCZ", "1544": "FOR", "1554": "NAT", "1558": "NAT", "1560": "JJG",
    "1566": "JPA", "1574": "AJU", "1578": "CNF", "1588": "FLN", "1598": "IGU", "1602": "BEL",
    "1622": "MAO", "1636": "DXB", "1660": "SLZ", "1680": "THE", "1682": "THE", "1720": "CGR",
    "1722": "CGR", "1730": "LDB", "1734": "LDB", "1736": "LDB", "1746": "MGF", "1748": "MGF",
    "1754": "JDO", "1762": "PNZ", "1774": "PVH", "1802": "GIG", "1806": "GIG", "1808": "GIG",
    "1810": "GIG", "1812": "GIG", "1856": "IOS", "1872": "REC", "1878": "FOR", "1902": "REC",
    "1908": "FOR", "1924": "MAO", "1940": "IMP", "1944": "XAP", "1948": "JOI", "1954": "VIX",
    "1956": "VIX", "1958": "VIX", "1960": "VIX", "1980": "MAB", "1988": "ATM", "2000": "REC",
    "2002": "REC", "2013": "REC", "2014": "REC", "2024": "REC", "2032": "REC", "2046": "REC",
    "2076": "MCZ", "2100": "SSA", "2110": "SSA", "2116": "SSA", "2122": "SSA", "2128": "SSA",
    "2130": "SSA", "2148": "BPS", "2150": "BPS", "2154": "BPS", "2162": "JPA", "2164": "JPA",
    "2166": "JPA", "2176": "AJU", "2180": "AJU", "2196": "NAT", "2198": "NAT", "2202": "NAT",
    "2224": "FOR", "2226": "FOR", "2228": "FOR", "2244": "FOR", "2248": "FOR", "2286": "THE",
    "2298": "SLZ", "2306": "BEL", "2308": "BEL", "2312": "BEL", "2316": "BEL", "2320": "MAO",
    "2324": "MAO", "2328": "MAO", "2338": "GIG", "2340": "GIG", "2344": "GIG", "2354": "CGB",
    "2357": "CGB", "2380": "VIX", "2382": "VIX", "2386": "VIX", "2390": "VIX", "2402": "CNF",
    "2404": "CNF", "2408": "CNF", "2410": "CNF", "2414": "CDG", "2416": "CDG", "2420": "BSB",
    "2422": "BSB", "2424": "BSB", "2426": "BSB", "2429": "BSB", "2430": "BSB", "2434": "BSB",
    "2436": "BSB", "2446": "POA", "2454": "POA", "2456": "POA", "2462": "POA", "2466": "POA",
    "2470": "POA", "2472": "POA", "2474": "POA", "2476": "POA", "2478": "POA", "2480": "POA",
    "2482": "POA", "2486": "CWB", "2488": "CWB", "2492": "CWB", "2496": "CWB", "2498": "CWB",
    "2500": "CWB", "2502": "CWB", "2510": "FLN", "2514": "FLN", "2516": "FLN", "2522": "FLN",
    "2524": "FLN", "2526": "FLN", "2532": "NVT", "2536": "NVT", "2538": "NVT", "2540": "NVT",
    "2542": "NVT", "2552": "IGU", "2554": "IGU", "2556": "IGU", "2558": "IGU", "2566": "GYN",
    "2568": "GYN", "2572": "GYN", "2574": "GYN", "2576": "GYN", "2578": "GYN", "2580": "GYN",
    "2609": "OPO", "2612": "RAO", "2614": "RAO", "2616": "RAO", "2618": "RAO", "2626": "SJP",
    "2628": "SJP", "2632": "SJP", "2636": "LDB", "2640": "LDB", "2642": "LDB", "2644": "LDB",
    "2646": "MGF", "2648": "MGF", "2650": "MGF", "2654": "JOI", "2656": "JOI", "2658": "JOI",
    "2660": "XAP", "2662": "XAP", "2672": "UDI", "2674": "UDI", "2676": "UDI", "2680": "CGR",
    "2684": "CGR", "2686": "CGR", "2696": "JDO", "2698": "CPV", "2702": "IOS", "2712": "VDC",
    "2722": "MOC", "2726": "IPN", "2730": "GVR", "2738": "CLV", "2746": "CAW", "2748": "CAW",
    "2754": "PET", "2758": "PET", "2768": "CAC", "2776": "JJG", "2782": "FEN", "2790": "JJD",
    "2792": "JJD", "2808": "CXJ", "2816": "UBA", "2826": "BYO", "2828": "BYO", "2834": "CFB",
    "2858": "CGB", "2868": "PVH", "2870": "PVH", "2874": "RBR", "2882": "PMW", "2884": "PMW",
    "2888": "MCP", "2892": "OPS", "2894": "OPS", "2916": "CKS", "2918": "CKS", "2926": "JDF",
    "2932": "QNS", "2936": "AFL", "2944": "GUZ", "2946": "GUZ", "2964": "RIA", "2976": "BVB",
    "2982": "MVF", "2986": "TFF", "2988": "TFF", "3000": "MAO", "3001": "MAO", "3002": "MAO",
    "3003": "MAO", "3006": "MAO", "3008": "MAO", "3009": "MAO", "3010": "MAO", "3012": "MAO",
    "3015": "MAO", "3023": "BSB", "3024": "BSB", "3025": "BSB", "3026": "BSB", "3028": "BSB",
    "3030": "BSB", "3032": "BSB", "3033": "BSB", "3034": "BSB", "3036": "BSB", "3038": "BSB",
    "3041": "BSB", "3042": "BSB", "3044": "BSB", "3046": "BSB", "3047": "BSB", "3048": "BSB",
    "3051": "BSB", "3052": "BSB", "3053": "BSB", "3054": "BSB", "3055": "BSB", "3056": "BSB",
    "3057": "BSB", "3062": "BSB", "3064": "CGB", "3066": "CGB", "3068": "CGB", "3076": "GYN",
    "3078": "GYN", "3080": "GYN", "3083": "GYN", "3086": "GYN", "3088": "GYN", "3090": "GYN",
    "3092": "GYN", "3094": "GYN", "3095": "GYN", "3100": "POA", "3104": "POA", "3106": "POA",
    "3110": "POA", "3112": "POA", "3114": "POA", "3116": "POA", "3118": "POA", "3120": "POA",
    "3121": "POA", "3123": "POA", "3124": "POA", "3126": "POA", "3128": "POA", "3130": "POA",
    "3131": "POA", "3132": "POA", "3135": "POA", "3136": "POA", "3138": "CWB", "3140": "CWB",
    "3142": "CWB", "3144": "CWB", "3146": "CWB", "3147": "CWB", "3148": "CWB", "3151": "CWB",
    "3152": "CWB", "3154": "CWB", "3156": "CWB", "3158": "CWB", "3166": "GIG", "3169": "GIG",
    "3172": "GIG", "3176": "GIG", "3180": "FLN", "3182": "FLN", "3183": "FLN", "3184": "FLN",
    "3185": "FLN", "3186": "FLN", "3187": "FLN", "3188": "FLN", "3189": "FLN", "3196": "NVT",
    "3198": "NVT", "3200": "NVT", "3202": "NVT", "3204": "NVT", "3206": "NVT", "3208": "NVT",
    "3210": "NVT", "3216": "VIX", "3218": "VIX", "3219": "VIX", "3220": "VIX", "3222": "VIX",
    "3223": "VIX", "3224": "VIX", "3226": "VIX", "3228": "IGU", "3232": "IGU", "3234": "IGU",
    "3236": "IGU", "3238": "IGU", "3240": "IGU", "3245": "FLN", "3246": "CGR", "3248": "CGR",
    "3252": "CGR", "3254": "CGR", "3256": "CGR", "3258": "JOI", "3260": "JOI", "3262": "JOI",
    "3266": "LDB", "3268": "LDB", "3270": "LDB", "3274": "FOR", "3275": "FOR", "3276": "FOR",
    "3277": "FOR", "3278": "FOR", "3280": "FOR", "3282": "FOR", "3284": "FOR", "3286": "FOR",
    "3288": "FOR", "3290": "FOR", "3292": "FOR", "3294": "FOR", "3296": "MGF", "3298": "MGF",
    "3300": "CNF", "3302": "CNF", "3306": "CNF", "3308": "CNF", "3310": "CNF", "3312": "CNF",
    "3314": "CNF", "3316": "CNF", "3318": "CNF", "3320": "CNF", "3322": "CNF", "3326": "CNF",
    "3332": "CNF", "3334": "CNF", "3336": "CNF", "3338": "CNF", "3340": "CNF", "3342": "CNF",
    "3344": "CNF", "3346": "CNF", "3347": "CNF", "3354": "REC", "3355": "REC", "3356": "REC",
    "3357": "REC", "3358": "REC", "3360": "REC", "3362": "REC", "3364": "REC", "3366": "REC",
    "3368": "REC", "3370": "REC", "3372": "REC", "3374": "REC", "3376": "SSA", "3378": "SSA",
    "3380": "SSA", "3382": "SSA", "3384": "SSA", "3386": "SSA", "3388": "SSA", "3390": "SSA",
    "3392": "SSA", "3394": "SSA", "3396": "SSA", "3398": "SSA", "3400": "SSA", "3404": "SSA",
    "3406": "SSA", "3408": "SSA", "3409": "SSA", "3412": "NAT", "3414": "NAT", "3416": "NAT",
    "3418": "NAT", "3420": "NAT", "3422": "NAT", "3424": "NAT", "3426": "NAT", "3430": "MCZ",
    "3432": "MCZ", "3434": "MCZ", "3436": "MCZ", "3438": "MCZ", "3440": "MCZ", "3444": "JPA",
    "3446": "JPA", "3448": "JPA", "3450": "AJU", "3452": "AJU", "3454": "AJU", "3456": "AJU",
    "3460": "BEL", "3461": "BEL", "3462": "BEL", "3464": "BEL", "3466": "BEL", "3468": "BEL",
    "3470": "BEL", "3472": "SLZ", "3474": "SLZ", "3476": "SLZ", "3478": "SLZ", "3482": "UDI",
    "3484": "UDI", "3486": "SJP", "3488": "SJP", "3490": "SJP", "3492": "SJP", "3496": "XAP",
    "3498": "XAP", "3502": "RAO", "3504": "RAO", "3506": "RAO", "3508": "RAO", "3510": "RAO",
    "3512": "THE", "3514": "THE", "3516": "THE", "3520": "PVH", "3522": "PVH", "3529": "BSB",
    "3530": "IOS", "3532": "IOS", "3536": "IOS", "3540": "BPS", "3542": "BPS", "3544": "BPS",
    "3546": "BPS", "3548": "BPS", "3550": "BPS", "3552": "BPS", "3554": "BPS", "3556": "BPS",
    "3558": "BPS", "3562": "JJD", "3564": "JJD", "3566": "JJD", "3570": "FEN", "3572": "FEN",
    "3576": "IMP", "3578": "IMP", "3584": "MCP", "3586": "MCP", "3590": "RBR", "3594": "PMW",
    "3596": "PMW", "3598": "PMW", "3600": "PMW", "3604": "CWB", "3605": "CWB", "3610": "CXJ",
    "3611": "AMS", "3612": "CXJ", "3616": "JDO", "3618": "JDO", "3620": "JDO", "3624": "PNZ",
    "3626": "PNZ", "3632": "VDC", "3634": "VDC", "3642": "CPV", "3646": "JJG", "3648": "JJG",
    "3652": "MVF", "3654": "IPN", "3656": "IPN", "3658": "UNA", "3662": "JDF", "3666": "SIN",
    "3668": "OPS", "3672": "RIA", "3674": "RIA", "3683": "AMS", "3685": "MOC", "3686": "MOC",
    "3700": "PET", "3702": "PET", "3708": "CLV", "3709": "CLV", "3712": "CAW", "3714": "CAW",
    "3724": "JJG", "3738": "GVR", "3742": "UBA", "3758": "BYO", "3760": "BYO", "3770": "BVB",
    "3778": "JJD", "3790": "CAC", "3794": "CKS", "3796": "CKS", "3802": "IZA", "3824": "AFL",
    "3828": "GUZ", "3832": "TFF", "3834": "TFF", "3842": "MII", "3856": "ATM", "3904": "GIG",
    "3908": "GIG", "3910": "GIG", "3912": "GIG", "3914": "GIG", "3916": "GIG", "3918": "GIG",
    "3920": "GIG", "3922": "GIG", "3924": "GIG", "3926": "GIG", "3928": "GIG", "3930": "GIG",
    "3932": "GIG", "3934": "GIG", "3936": "GIG", "3938": "GIG", "3940": "GIG", "3942": "GIG",
    "3944": "GIG", "3947": "GIG", "3948": "GIG", "3949": "GIG", "3956": "SDU", "3958": "SDU",
    "3960": "SDU", "3962": "SDU", "3966": "SDU", "3968": "SDU", "3970": "SDU", "3972": "SDU",
    "3974": "SDU", "3976": "SDU", "3978": "SDU", "3980": "SDU", "3982": "SDU", "3984": "SDU",
    "3986": "SDU", "3988": "SDU", "3994": "SDU", "4018": "GIG", "4067": "DXB", "4070": "SCL",
    "4117": "SCL", "4152": "LHR", "4172": "AMS", "4227": "SCL", "4235": "JFK", "4247": "SCL",
    "4277": "JFK", "4301": "SCL", "4305": "SCL", "4351": "CPT", "4355": "JNB", "4361": "ADD",
    "4364": "IST", "4366": "IST", "4382": "POA", "4413": "SCL", "4516": "LIS", "4522": "LIS",
    "4540": "MIA", "4548": "CDG", "4550": "JFK", "457": "CDG", "4587": "CPT", "4610": "FRA",
    "4632": "LHR", "4640": "ZRH", "4653": "JNB", "4656": "AMS", "4666": "DXB", "4690": "MAD",
    "4700": "FCO", "4715": "JFK", "4722": "BOS", "4724": "JFK", "4732": "MIA", "4741": "MCO",
    "4746": "MIA", "4752": "MIA", "4754": "MIA", "4767": "JFK", "4771": "DXB", "4777": "MCO",
    "4781": "JFK", "4783": "JFK", "4785": "MIA", "4793": "JFK", "4797": "DXB", "4834": "CNF",
    "5038": "LHR", "5046": "DOH", "5101": "FOR", "5117": "BCN", "5126": "LHR", "5133": "POA",
    "5134": "BSB", "5138": "BCN", "5148": "BPS", "5152": "LHR", "5156": "MIA", "5167": "CGR",
    "5172": "MIA", "5176": "MIA", "5191": "CGB", "5192": "MCZ", "5194": "CWB", "5203": "MCZ",
    "5205": "MCZ", "5216": "IGU", "5217": "JPA", "5219": "LHR", "5223": "MIA", "5242": "POA",
    "5279": "BCN", "5282": "MCZ", "5285": "VDC", "5290": "MCZ", "5291": "BPS", "5295": "POA",
    "5357": "DOH", "5500": "AMS", "5538": "MXP", "5563": "JUL", "5726": "MIA", "5896": "JFK",
    "5939": "MIA", "5949": "SCL", "5963": "MEX", "6023": "MIA", "6029": "MIA", "6035": "MIA",
    "6051": "JFK", "6059": "MIA", "6061": "PUJ", "6193": "MXP", "6199": "MXP", "6200": "MIA",
    "6204": "JFK", "6219": "MAD", "6238": "AMS", "6240": "BCN", "6242": "BCN", "6246": "FRA",
    "6248": "JFK", "6270": "MIA", "6271": "CDG", "6314": "CDG", "6315": "CDG", "6375": "ATL",
    "6403": "MIA", "6434": "MAD", "6548": "CDG", "6572": "CDG", "6603": "AMS", "6635": "SDU",
    "6647": "CDG", "6690": "ATL", "6718": "AMS", "6719": "AMS", "6721": "ATL", "6747": "AMS",
    "6849": "AMS", "7000": "MIA", "7002": "MIA", "7006": "MIA", "7014": "MIA", "7048": "CDG",
    "7056": "CDG", "7058": "CDG", "7081": "FCO", "7085": "FCO", "7087": "FCO", "7110": "MIA",
    "7120": "FRA", "7134": "JFK", "7140": "MIA", "7213": "IAH", "7255": "EWR", "7257": "ORD",
    "7260": "LHR", "7269": "DXB", "7277": "LHR", "7280": "ATL", "7283": "POA", "7289": "CNF",
    "7299": "DXB", "7314": "VCP", "7330": "CWB", "7332": "CWB", "7335": "SDU", "7344": "FRA",
    "7347": "LHR", "7350": "JFK", "7355": "GIG", "7361": "MAD", "7454": "AMS", "7456": "BSB",
    "7477": "MIA", "750": "SCL", "751": "SCL", "7534": "CWB", "7536": "EZE", "7586": "AMS",
    "7610": "EZE", "7611": "EZE", "7614": "COR", "7620": "EZE", "7621": "EZE", "7622": "EZE",
    "7626": "EZE", "7630": "SCL", "7631": "SCL", "7634": "SCL", "7635": "SCL", "7636": "SCL",
    "7640": "SCL", "7641": "SCL", "7642": "SCL", "7643": "SCL", "7652": "SCL", "7656": "SCL",
    "7658": "SCL", "7660": "SCL", "7661": "SCL", "7662": "SCL", "7664": "SCL", "7665": "CWB",
    "7669": "GYN", "7670": "MDZ", "7672": "FLN", "7673": "MCZ", "7675": "FLN", "7679": "REC",
    "7685": "SSA", "7686": "FLN", "7689": "MAO", "7690": "BPS", "7696": "GYN", "7700": "CGR",
    "7702": "JFK", "7703": "AEP", "7707": "EZE", "7710": "CWB", "7711": "AEP", "7714": "VVI",
    "7721": "BSB", "7724": "IGU", "7730": "PUJ", "7741": "GIG", "7744": "NVT", "7746": "MVD",
    "7757": "FLN", "7761": "MCZ", "7763": "GIG", "7766": "VIX", "7774": "REC", "7780": "SLZ",
    "7844": "JFK", "7848": "SJO", "7850": "BOG", "7852": "BOG", "7854": "BOG", "7858": "LIM",
    "7860": "LIM", "7862": "LIM", "7864": "LIM", "7866": "LIM", "7868": "LIM", "7870": "MVD",
    "7872": "MVD", "7874": "MVD", "7876": "ASU", "7878": "ASU", "7880": "AEP", "7882": "AEP",
    "7884": "AEP", "7886": "AEP", "7890": "AEP", "7894": "MDZ", "7900": "BOG", "7908": "MIA",
    "7967": "MAD", "8000": "BOG", "8001": "BOG", "8012": "SCL", "8013": "SCL", "8020": "EZE",
    "8021": "EZE", "8026": "EZE", "8027": "EZE", "8028": "EZE", "8029": "EZE", "8032": "EZE",
    "8033": "EZE", "8038": "LIM", "8039": "LIM", "8044": "MVD", "8045": "MVD", "8050": "SCL",
    "8051": "SCL", "8058": "CDG", "8059": "CDG", "8062": "MXP", "8063": "MXP", "8064": "MAD",
    "8065": "MAD", "8066": "MAD", "8070": "FRA", "8071": "FRA", "8072": "FCO", "8073": "FCO",
    "8082": "LHR", "8084": "LHR", "8085": "LHR", "8089": "MCO", "8104": "ASU", "8112": "BCN",
    "8113": "BCN", "8114": "BOS", "8115": "BOS", "8121": "MCO", "8125": "MCO", "8126": "MCO",
    "8127": "MCO", "8128": "MCO", "8134": "MVD", "8135": "CNF", "8146": "LIS", "8147": "LIS",
    "8148": "LAX", "8180": "JFK", "8181": "JFK", "8182": "JFK", "8190": "MIA", "8191": "MIA",
    "8194": "MIA", "8200": "MIA", "8227": "MCO", "8349": "SCL", "8416": "SCL", "8422": "SCL",
    "8471": "SCL", "8475": "SCL", "8476": "SCL", "8490": "JUL", "8497": "SCL", "8643": "SCL",
    "9072": "SCL", "9173": "SCL", "9253": "SCL", "9254": "SCL", "9298": "AMS", "9326": "AMS",
    "9700": "DXB", "9746": "MIA", "9809": "SCL", "9813": "SCL", "9961": "AMS", "AA906": "MIA",
    "AA930": "MIA", "AA950": "JFK", "AC90": "YYZ", "AC91": "YYZ", "AF454": "CDG", "AF457": "CDG",
    "AM14": "MEX", "AM15": "MEX", "BA246": "LHR", "BA247": "LHR", "ET506": "ADD", "ET507": "ADD",
    "IB6824": "MAD", "IB6827": "MAD", "LA3000": "MAO", "LA3001": "MAO", "LA3056": "BSB", "LA3130": "POA",
    "LA3131": "POA", "LA3245": "FLN", "LA3274": "FOR", "LA3275": "FOR", "LA3346": "CNF", "LA3347": "CNF",
    "LA3354": "REC", "LA3355": "REC", "LA3408": "SSA", "LA3409": "SSA", "LA3529": "BSB", "LA3604": "CWB",
    "LA3605": "CWB", "LA3947": "GIG", "LA3948": "GIG", "LA4540": "MIA", "LA750": "SCL", "LA751": "SCL",
    "LA8000": "BOG", "LA8001": "BOG", "LA8028": "EZE", "LA8029": "EZE", "LA8032": "EZE", "LA8033": "EZE",
    "LA8038": "LIM", "LA8039": "LIM", "LA8044": "MVD", "LA8045": "MVD", "LA8050": "SCL", "LA8051": "SCL",
    "LA8058": "CDG", "LA8059": "CDG", "LA8062": "MXP", "LA8063": "MXP", "LA8064": "MAD", "LA8065": "MAD",
    "LA8066": "MAD", "LA8070": "FRA", "LA8071": "FRA", "LA8072": "FCO", "LA8073": "FCO", "LA8084": "LHR",
    "LA8085": "LHR", "LA8104": "ASU", "LA8112": "BCN", "LA8113": "BCN", "LA8114": "BOS", "LA8115": "BOS",
    "LA8126": "MCO", "LA8127": "MCO", "LA8128": "MCO", "LA8146": "LIS", "LA8147": "LIS", "LA8148": "LAX",
    "LA8180": "JFK", "LA8181": "JFK", "LA8182": "JFK", "LA8190": "MIA", "LA8191": "MIA", "LA8194": "MIA",
    "LH506": "FRA", "LH507": "FRA", "LX92": "ZRH", "LX93": "ZRH", "QR773": "DOH", "QR774": "DOH",
    "TK15": "IST", "TK16": "IST", "TP82": "OPO", "TP83": "LIS", "TP84": "LIS", "UA148": "EWR",
    "UA844": "ORD", "UA860": "IAD"
}


# Dicionário Massivo de Conversão ICAO -> IATA (Focado em GRU/Brasil/Latam)
ICAO_TO_IATA = {
    # Brasil - Capitais e Hubs
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


# Fonte da verdade: voos que chegam só com número (sem prefixo IATA no CSV).
# Baseado em pesquisa externa (horários GRU, FlightStats, ANAC) — não usar faixa numérica.
KNOWN_NUMERIC_FLIGHTS = {
    "0015": "Aeromexico",   # AM 15 GRU→MEX (emsampa/ANAC Z0015→MMMX)
    "15": "Aeromexico",
    "3609": "GOL",          # G3 3609 GRU→CWB (ANAC 3609→SBCT)
    "4390": "Azul",         # AD 4390 GRU→CWB (FlightStats / ANAC 4390→SBCT)
    "6805": "Air Canada",   # AC 6805 GRU→YYZ (ANAC 6805→CYYZ)
}


def get_iata_code(city_name: str) -> str:
    """
    Mapeia nome da cidade para código IATA com busca case-insensitive.
    
    Args:
        city_name: Nome da cidade (ex: "PARIS", "Rio de Janeiro", " Lisboa ")
        
    Returns:
        Código IATA (ex: "CDG", "GIG") ou string vazia se não encontrado
    """
    city_name = safe_str(city_name)
    if not city_name:
        return ""
    
    city_clean = city_name.lower()
    iata_code = CITY_TO_IATA.get(city_clean, "")

    if iata_code:
        logger.debug(f"Mapeamento IATA: {city_name} → {iata_code}")
    else:
        logger.debug(f"Cidade não mapeada: {city_name} (fallback: campo vazio no funil)")

    return iata_code


def is_domestic_flight(destination_iata: str) -> bool:
    """
    Verifica se o voo é doméstico (nacional).
    
    Args:
        destination_iata: Código IATA do destino
        
    Returns:
        True se for voo nacional, False se internacional
    """
    return destination_iata in BRAZILIAN_AIRPORTS


# ============================================================================
# NOVA LÓGICA DE INFERÊNCIA (BASEADA EM DADOS REAIS DE GRU - JAN/2026)
# ============================================================================

def infer_airline(flight_number: str, airline: Optional[str] = None) -> str:
    """
    Deduz a companhia aérea com base em regras de negócio validadas para GRU.

    Regras Baseadas em Pesquisa (31/01/2026):
    1. Voo 0015/15 -> Aeromexico (Exceção Crítica)
    2. Voos 7255 -> LATAM (Operado por LATAM, vendido por Qatar)
    3. Faixas 1000-9999 -> LATAM (Dominante em GRU: 1470, 4682, 8191, etc.)
    4. Faixas < 1000 -> LATAM (Se não for GOL/Azul explícito)
    """
    airline = safe_str(airline)
    flight_number = safe_str(flight_number)

    # 1. Se já tem companhia válida no CSV, respeita ela
    if airline and airline.upper() not in ["DESCONHECIDO", "N/A", "", "UNKNOWN", "NAN"]:
        return airline

    # 2. Se não tem número, assume LATAM (fallback seguro para GRU)
    if not flight_number:
        return "LATAM"

    flight_number_upper = flight_number.upper()

    # 3. Verifica Prefixos Explícitos (ex: AD4390, G33609)
    airline_prefixes = {
        'LA': 'LATAM', 'JJ': 'LATAM', 'RJ': 'LATAM',
        'AD': 'Azul', 'G3': 'Gol', 'TP': 'TAP',
        'DL': 'Delta', 'KL': 'KLM', 'EK': 'Emirates',
        'QR': 'Qatar', 'AF': 'Air France', 'LH': 'Lufthansa',
        'BA': 'British Airways', 'AA': 'American Airlines',
        'UA': 'United Airlines', 'AM': 'Aeromexico', 'AC': 'Air Canada'
    }

    for prefix, name in airline_prefixes.items():
        if flight_number_upper.startswith(prefix):
            return name

    # 4. Limpeza para análise numérica
    clean_num = "".join(filter(str.isdigit, flight_number))
    if not clean_num:
        return "LATAM"

    voo_int = int(clean_num)

    # 5. REGRAS DE EXCEÇÃO (A "Lista VIP" baseada na pesquisa)
    # 0015 é o único voo numérico baixo recorrente que NÃO é LATAM/GOL
    if voo_int == 15:
        return "Aeromexico"

    # 6. REGRA GERAL DE FAIXAS (GRU)
    # A pesquisa mostrou que 1470, 4682, 5283, 7598, 8173 são TODOS LATAM.
    # Em GRU, se o CSV vem vazio, 99% de chance de ser LATAM (sistema legado).
    return "LATAM"


class FlightPageGenerator:
    """Gerador de páginas estáticas para voos - Production Grade."""
    
    def __init__(
        self,
        data_file: str = "data/flights-db.json",
        template_file: str = "src/templates/tier2-anac400.html",
        output_dir: str = "docs",
        voo_dir: str = "docs/voo",
        affiliate_link: str = "",
        base_url: str = "https://matchfly.org"
    ):
        """
        Inicializa o gerador.
        
        Args:
            data_file: Caminho para o arquivo JSON com dados de voos
            template_file: Caminho para o template Jinja2
            output_dir: Diretório de saída para páginas HTML
            voo_dir: Diretório específico para páginas de voos
            affiliate_link: Link de afiliado para monetização
            base_url: URL base para sitemap
        """
        self.data_file = Path(data_file)
        self.template_file = Path(template_file)
        self.output_dir = Path(output_dir)
        self.voo_dir = Path(voo_dir)
        self.affiliate_link = affiliate_link
        self.base_url = base_url.rstrip('/')
        
        # Configurar Jinja2
        template_dir = self.template_file.parent
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )
        
        # Estatísticas detalhadas
        self.stats = {
            'total_flights': 0,
            'successes': 0,
            'failures': 0,
            'orphans_removed': 0,
            'old_files_detected': 0,
            'filtered_out': 0
        }
        
        # Tracking de arquivos gerados com sucesso
        self.success_files: Set[str] = set()
        self.success_pages: List[Dict] = []
        # True quando dados foram carregados do Supabase (não gravar JSON enriquecido)
        self._loaded_from_supabase = False
    
        # Banco de rotas da ANAC (já traduzido para IATA)
        self.anac_db: Dict[str, str] = self.load_anac_database()
    
    def load_anac_database(self) -> Dict[str, str]:
        """Carrega ANAC DB e converte ICAO -> IATA na memória."""
        try:
            path = PROJECT_ROOT / 'data' / 'specificroutes_anac.json'
            if not path.exists():
                logger.warning("⚠️ Arquivo specificroutes_anac.json não encontrado.")
                return {}
            
            with open(path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            
            clean_db: Dict[str, str] = {}
            for k, v in raw.items():
                # Limpa chave (apenas números)
                clean_k = "".join(filter(str.isdigit, str(k)))
                
                # TRADUÇÃO: ICAO -> IATA
                iata = ICAO_TO_IATA.get(v, v)  # Tenta traduzir, senão mantém original
                
                # Remove prefixo 'K' de aeroportos dos EUA (ex: KORD -> ORD)
                if len(iata) == 4 and iata.startswith('K'):
                    iata = iata[1:]
                
                if clean_k:
                    clean_db[clean_k] = iata
            
            logger.info(f"✅ ANAC DB carregado e traduzido: {len(clean_db)} rotas.")
            return clean_db
        except Exception as e:
            logger.error(f"❌ Erro carregando ANAC DB: {e}")
            return {}

    def safe_str(self, val):
        """Converte qualquer valor para string limpa, evitando erro de float/None."""
        return safe_str(val)

    def setup_and_validate(self) -> bool:
        """
        STEP 1: Setup & Validação.
        Verifica affiliate link e cria estrutura de pastas.
        
        Returns:
            True se validação passou, False caso contrário
        """
        logger.info("=" * 70)
        logger.info("STEP 1: SETUP & VALIDAÇÃO")
        logger.info("=" * 70)
        
        # Validação e fallback: Affiliate Link
        if not safe_str(self.affiliate_link):
            # Usar link padrão em vez de interromper o build
            self.affiliate_link = "https://www.compensair.com/"
            logger.warning("⚠️  AFFILIATE_LINK não configurada - usando link padrão")
            logger.warning("   Para produção, configure AFFILIATE_LINK em src/generator.py")
        
        logger.info(f"✅ Affiliate link configurada: {self.affiliate_link[:50]}...")
        
        # Criar estrutura de pastas
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.voo_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Pasta {self.voo_dir} pronta")
            # Infraestrutura GitHub Pages (CNAME + bypass Jekyll)
            (self.output_dir / "CNAME").write_text("matchfly.org", encoding="utf-8")
            (self.output_dir / ".nojekyll").touch()
            return True
        except Exception as e:
            logger.error(f"Erro ao criar pastas: {e}")
            return False
    
    def initial_cleanup(self) -> None:
        """
        STEP 2: Initial Cleanup com auditoria.
        Remove index.html antigo e conta arquivos em voo_dir.
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 2: INITIAL CLEANUP (Auditoria)")
        logger.info("=" * 70)

        # Remove index.html antigo
        index_file = self.output_dir / "index.html"
        if index_file.exists():
            try:
                index_file.unlink()
                logger.info(f"Removido: {index_file} (será regenerado)")
            except Exception as e:
                logger.warning(f"Não foi possível remover index.html: {e}")

        # Conta arquivos HTML em voo_dir
        old_files = list(self.voo_dir.glob("*.html"))
        self.stats['old_files_detected'] = len(old_files)

        if old_files:
            logger.info(f"Detectados {len(old_files)} arquivos antigos em {self.voo_dir}")
            logger.info("Serão removidos automaticamente quando não regenerados.")
        else:
            logger.info(f"Nenhum arquivo antigo detectado em {self.voo_dir}")
    
    def _row_to_flight_dict(self, row: dict) -> dict:
        """Converte uma linha Supabase (snake_case) em dict de voo. Preferência por raw_data."""
        if isinstance(row.get("raw_data"), dict):
            return row["raw_data"].copy()
        return {
            "Data_Captura": row.get("data_captura"),
            "Horario": row.get("horario") or row.get("scheduled_time"),
            "Companhia": row.get("companhia") or row.get("airline"),
            "Numero_Voo": row.get("numero_voo") or row.get("flight_number"),
            "Operado_Por": row.get("operado_por"),
            "Status": row.get("status"),
            "Data_Partida": row.get("data_partida"),
            "Hora_Partida": row.get("hora_partida"),
            "flight_number": row.get("flight_number"),
            "airline": row.get("airline"),
            "status": row.get("status"),
            "scheduled_time": row.get("scheduled_time"),
            "data_partida": row.get("data_partida"),
            "delay_hours": row.get("delay_hours"),
            "destination_iata": row.get("destination_iata"),
            "destination": row.get("destination"),
            "destination_city": row.get("destination_city"),
        }

    def _load_flight_data_from_file(self) -> Optional[Dict]:
        """Lê JSON do data_file. Retorna {'raw_flights': [...], 'data': {...}} ou None."""
        if not self.data_file.exists():
            return None
        with open(self.data_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        if isinstance(raw_data, list):
            return {"raw_flights": raw_data, "data": {}}
        if isinstance(raw_data, dict):
            raw_flights = raw_data.get("flights") or raw_data.get("data") or []
            return {"raw_flights": raw_flights, "data": raw_data}
        return {"raw_flights": [], "data": {}}

    def load_flight_data(self) -> Optional[Dict]:
        """
        Carrega e NORMALIZA dados de voos.
        Se SUPABASE_URL e SUPABASE_KEY estiverem definidos, busca da tabela flights.
        Caso contrário, lê do arquivo JSON (data_file).

        Returns:
            Dicionário com dados normalizados ou None em caso de erro
        """
        try:
            url = os.environ.get("SUPABASE_URL") or os.environ.get("SUPABASE_SERVICE_URL")
            key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
            if url and key:
                try:
                    from supabase import create_client
                    client = create_client(url, key)
                    resp = client.table("flights").select("*").execute()
                    rows = resp.data or []
                    raw_flights = [self._row_to_flight_dict(r) for r in rows if isinstance(r, dict)]
                    data = {"flights": raw_flights, "metadata": {}}
                    self._loaded_from_supabase = True
                    logger.info("📥 Dados carregados do Supabase: %s voos", len(raw_flights))
                except Exception as e:
                    logger.warning("⚠️ Fallback para JSON após erro no Supabase: %s", e)
                    self._loaded_from_supabase = False
                    file_data = self._load_flight_data_from_file()
                    if file_data is None:
                        return None
                    raw_flights = file_data.get("raw_flights", [])
                    data = file_data.get("data", {})
            else:
                self._loaded_from_supabase = False
                file_data = self._load_flight_data_from_file()
                if file_data is None:
                    return None
                raw_flights = file_data.get("raw_flights", [])
                data = file_data.get("data", {})

            # Normalização de Chaves (Polyglot)
            normalized_flights: List[Dict] = []
            for fdata in raw_flights:
                # Segurança: alguns pipelines podem trazer linhas como strings/None
                if not isinstance(fdata, dict):
                    continue

                norm = fdata.copy()

                # Mapeia chaves PT -> EN se necessário (safe_str evita float/None)
                if 'Numero_Voo' in fdata:
                    norm['flight_number'] = safe_str(fdata.get('Numero_Voo'))
                if 'Companhia' in fdata:
                    norm['airline'] = safe_str(fdata.get('Companhia'))
                if 'Status' in fdata:
                    norm['status'] = safe_str(fdata.get('Status'))
                if 'Horario' in fdata:
                    norm['scheduled_time'] = safe_str(fdata.get('Horario'))
                if 'Destino' in fdata:
                    norm['destination'] = safe_str(fdata.get('Destino'))
                if 'Data_Partida' in fdata:
                    norm['data_partida'] = safe_str(fdata.get('Data_Partida'))

                # Sinônimos comuns (robustez extra)
                if not norm.get('flight_number') and 'Número Voo' in fdata:
                    norm['flight_number'] = safe_str(fdata.get('Número Voo'))
                if not norm.get('airline') and 'Cia' in fdata:
                    norm['airline'] = safe_str(fdata.get('Cia'))
                if not norm.get('scheduled_time') and 'Hora' in fdata:
                    norm['scheduled_time'] = safe_str(fdata.get('Hora'))

                # Garante campos string para chaves já existentes (ex.: JSON com floats)
                for key in ('flight_number', 'airline', 'status', 'scheduled_time', 'data_partida', 'destination'):
                    if key in norm and not isinstance(norm[key], str):
                        norm[key] = safe_str(norm[key])

                # Garante que delay_hours exista (para não filtrar tudo)
                if 'delay_hours' not in norm:
                    status_lower = safe_str(norm.get('status', '')).lower()
                    if 'cancel' in status_lower:
                        norm['delay_hours'] = 0.0
                    elif 'atras' in status_lower:
                        norm['delay_hours'] = 1.0  # Default para atraso
                    else:
                        norm['delay_hours'] = 0.0

                normalized_flights.append(norm)

            data['flights'] = normalized_flights
            logger.info(f"✅ Dados carregados e normalizados: {len(normalized_flights)} voos")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}")
            return None
    
    def _get_effective_destination_city(self, flight: Dict) -> str:
        """
        Retorna a cidade de destino efetiva após correções (SCL, ANAC, IATA).
        Mesma lógica usada em generate_page_resilient para consistência.
        """
        clean_fnum = "".join(filter(str.isdigit, self.safe_str(flight.get('flight_number', ''))))
        correction_iata = CORRECTIONS_DICT.get(clean_fnum)
        anac_iata = ANAC_DB.get(clean_fnum)
        if correction_iata:
            dest_iata = correction_iata
        elif anac_iata:
            dest_iata = anac_iata
        else:
            dest_iata = self.safe_str(flight.get('destination_iata')) or ''
        dest_city = IATA_TO_CITY_NAME.get(dest_iata) or getattr(
            enrichment_module, 'IATA_TO_CITY', {}
        ).get(dest_iata)
        if not dest_city:
            dest_city = self.safe_str(flight.get('destination')) or dest_iata or "Destino Desconhecido"
        return dest_city

    def should_generate_page(self, flight: Dict) -> bool:
        """
        Valida se a página do voo deve ser gerada.
        Agora aceita voos recuperados pela inferência (não descarta mais por falta de Cia).
        """
        # Validação Básica
        if not safe_str(flight.get('flight_number')):
            return False
        if not safe_str(flight.get('status')):
            return False

        # Inferência Forçada (Recupera voos "órfãos" como o 4682 e 0015)
        effective_airline = infer_airline(flight.get('flight_number'), flight.get('airline'))

        # Atualiza o objeto do voo com a companhia descoberta
        flight['airline'] = effective_airline

        # Se a inferência retornasse vazio (o que não acontece mais), aí sim descartaria
        if not effective_airline:
            return False

        return True
    
    def calculate_hours_ago(self, scraped_at: str) -> int:
        """
        Calcula quantas horas se passaram desde o scraping.
        
        Args:
            scraped_at: Timestamp ISO do scraping
            
        Returns:
            Número de horas (arredondado)
        """
        try:
            # Remove timezone se presente e converte para UTC
            scraped_at_clean = scraped_at.replace('Z', '').split('+')[0].split('.')[0]
            scraped_dt = datetime.fromisoformat(scraped_at_clean)
            now = datetime.now()
            delta = now - scraped_dt
            hours = int(delta.total_seconds() / 3600)
            return max(0, hours)  # Não retorna valores negativos
        except Exception as e:
            logger.debug(f"Erro ao calcular hours_ago: {e}")
            return 0
    
    def generate_slug(self, flight: Dict) -> str:
        """
        Gera slug de URL amigável para SEO, único por voo+data.
        Formato: voo-{airline}-{number}-{origin}-{dest}-{dd}-{mm}
        Ex.: voo-latam-1470-gru-cwb-31-01.html
        """
        airline = self.safe_str(flight.get('airline', ''))
        number = self.safe_str(flight.get('flight_number', ''))
        origin = self.safe_str(flight.get('origin', 'GRU'))
        dest = self.safe_str(flight.get('destination_iata', ''))

        if not airline:
            airline = "voo"
        if not number:
            number = "desconhecido"
        if not dest:
            dest = "atrasado"  # fallback quando não há IATA

        base = f"voo-{slugify(airline)}-{slugify(number)}-{slugify(origin)}-{slugify(dest)}"
        flight_date = parse_flight_time(flight)
        if flight_date == datetime.min:
            date_suffix = ""  # fallback: comportamento antigo (sem data no nome)
        else:
            date_suffix = f"-{flight_date.strftime('%d-%m')}"  # ex: -31-01
        return base + date_suffix

    def get_city_slug(self, city_name: str) -> str:
        """Gera slug padronizado para nome de cidade (Single Source of Truth para URLs de destino)."""
        return slugify(safe_str(city_name) or "destino")

    def prepare_template_context(self, flight: Dict, metadata: Dict) -> Dict:
        """
        Prepara contexto de dados para o template.
        """
        scraped_at = safe_str(metadata.get('scraped_at') or '') or datetime.now(timezone.utc).isoformat()
        hours_ago = self.calculate_hours_ago(scraped_at)

        flight_number = self.safe_str(flight.get('flight_number')) or 'N/A'
        origin = self.safe_str(flight.get('origin')) or 'GRU'
        destination = self.safe_str(flight.get('destination')) or 'N/A'
        airline_raw = self.safe_str(flight.get('airline', ''))

        airline = infer_airline(flight_number, airline_raw)

        scheduled_time = self.safe_str(flight.get('scheduled_time', ''))
        display_time = 'N/A'
        if scheduled_time:
            try:
                if ' ' in scheduled_time:
                    display_time = scheduled_time.split(' ')[-1]
                elif ':' in scheduled_time and len(scheduled_time) <= 5:
                    display_time = scheduled_time
                else:
                    dt = datetime.fromisoformat(scheduled_time.replace('Z', '').split('+')[0].split('.')[0])
                    display_time = dt.strftime('%H:%M')
            except Exception as e:
                logger.debug(f"Erro ao extrair display_time de '{scheduled_time}': {e}")
                display_time = scheduled_time
        
        # ============================================================
        # PARTE 2: CONSTRUÇÃO DO DEEP LINK OTIMIZADO (FUNIL AIRHELP)
        # ============================================================
        
        # Mapeia destino para código IATA
        destination_iata = get_iata_code(destination)
        
        # Determina se é voo nacional ou internacional
        is_domestic = is_domestic_flight(destination_iata) if destination_iata else False
        
        # Define regulamentação aplicável
        regulation = "ANAC 400" if is_domestic else "EC 261/ANAC"
        
        # Constrói Deep Link do Funil AirHelp com parâmetros otimizados
        # Base: funnel.airhelp.com/claims/new/trip-details
        affiliate_link_with_flight = (
            f"https://funnel.airhelp.com/claims/new/trip-details?"
            f"lang=pt-br"
            f"&departureAirportIata={origin}"
        )
        
        # Adiciona destino se disponível (aumenta conversão significativamente)
        if destination_iata:
            affiliate_link_with_flight += f"&arrivalAirportIata={destination_iata}"
        
        # Anexa parâmetros de rastreio de afiliado (obrigatório)
        affiliate_link_with_flight += (
            f"&a_aid=69649260287c5"
            f"&a_bid=c63de166"
            f"&utm_medium=affiliate"
            f"&utm_source=pap"
            f"&utm_campaign=aff-69649260287c5"
        )
        
        logger.debug(f"Link gerado: {affiliate_link_with_flight}")
        logger.debug(f"Voo {'NACIONAL' if is_domestic else 'INTERNACIONAL'}: {origin} → {destination} ({destination_iata})")
        
        context = {
            'flight_number': flight_number,
            'airline': airline,
            'status': self.safe_str(flight.get('status')) or 'Problema',
            'scheduled_time': scheduled_time or 'N/A',
            'display_time': display_time,
            'data_partida': self.safe_str(flight.get('data_partida', '')),
            'actual_time': self.safe_str(flight.get('actual_time')) or 'N/A',
            'delay_hours': flight.get('delay_hours', 0),
            'origin': origin,
            'destination': destination,
            'destination_iata': destination_iata,
            'is_domestic': is_domestic,
            'regulation': regulation,
            'hours_ago': hours_ago,
            'scraped_at': scraped_at,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'affiliate_link': affiliate_link_with_flight,
            'departure_time': scheduled_time or datetime.now().isoformat(),
        }
        
        return context

    def _generate_robots_txt(self):
        """Gera robots.txt na pasta public."""
        robots_content = (
            "User-agent: *\n"
            "Allow: /\n\n"
            f"Sitemap: {self.base_url}/sitemap.xml\n"
        )
        (self.output_dir / "robots.txt").write_text(robots_content, encoding="utf-8")
        logging.info("🤖 robots.txt gerado.")

    def _get_seo_context(self, flight: dict, slug: str) -> dict:
        """
        Gera dados de SEO (Schema JSON-LD, Títulos e Canonical).
        Recebe 'slug' já calculado para garantir consistência.
        """
        # 1. Extração segura usando função GLOBAL safe_str
        fnum = safe_str(flight.get('flight_number')) or "Voo"
        airline = safe_str(flight.get('airline')) or "Companhia"
        dest = safe_str(flight.get('destination')) or "Destino Desconhecido"
        status = safe_str(flight.get('status')) or ""

        # Validação de Edge Cases
        if fnum == "Voo" or dest == "Destino Desconhecido":
            logging.warning(f"⚠️ SEO Incompleto para voo: {fnum} -> {dest}")

        current_year = datetime.now().year
        flight_url = f"{self.base_url}/voo/{slug}.html"

        # 2. Copywriting baseado no status do voo
        if "Cancelado" in status or "CANCELLED" in status.upper():
            title = f"Voo {fnum} Cancelado? Indenização e Direitos {current_year} | MatchFly"
            desc = f"Voo {fnum} da {airline} cancelado? Veja como pedir indenização por danos morais. Análise gratuita de direitos."
            schema_status = "https://schema.org/FlightCancelled"
        else:
            title = f"Voo {fnum} Atrasou? Valor da Indenização {current_year} | MatchFly"
            desc = f"Atraso no voo {fnum} para {dest}? Saiba seus direitos e verifique se cabe indenização imediata."
            schema_status = "https://schema.org/FlightDelayed"

        # 3. Schema JSON-LD (Flight + Breadcrumb + FAQ)
        schema = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "Home", "item": self.base_url},
                        {"@type": "ListItem", "position": 2, "name": f"Voo {fnum}", "item": flight_url}
                    ]
                },
                {
                    "@type": "Flight",
                    "flightNumber": fnum,
                    "provider": {"@type": "Airline", "name": airline},
                    "departureAirport": {"@type": "Airport", "iataCode": "GRU", "name": "Aeroporto de Guarulhos"},
                    "arrivalAirport": {"@type": "Airport", "name": dest},
                    "flightStatus": schema_status
                },
                {
                    "@type": "FAQPage",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": f"Tenho direito a indenização pelo voo {fnum}?",
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": "Se houve cancelamento ou atraso superior a 4 horas, você pode ter direito a indenização. Verifique gratuitamente no link."
                            }
                        }
                    ]
                }
            ]
        }

        return {
            "page_title": title,
            "page_description": desc,
            "canonical_url": flight_url,
            "json_ld_schema": json.dumps(schema, ensure_ascii=False)
        }

    def get_flight_card_flip_html(self, flight: dict, related_dates: list = None) -> str:
        """
        Card Flip 3D com navegação hierárquica: Data → Horário → Página do Voo.

        Args:
            flight: Dicionário com dados do voo
            related_dates: Lista de tuplas (datetime_display, slug)
                          Ex: [("03/02 14:00", "slug123"), ("03/02 18:30", "slug456")]
        """
        # Extração segura de dados
        flight_num = self.safe_str(flight.get('flight_number')) or 'N/A'
        airline = self.safe_str(flight.get('airline')) or 'Companhia'
        origin = self.safe_str(flight.get('origin')) or 'GRU'
        dest = self.safe_str(flight.get('destination')) or self.safe_str(flight.get('destination_iata')) or 'Destino'
        status = self.safe_str(flight.get('status')) or 'Status'
        status_upper = status.upper()

        # ID seguro para JavaScript
        flight_id_safe = re.sub(r'[^a-zA-Z0-9]', '', flight_num)

        # Cores
        is_delayed = 'ATRASADO' in status_upper or 'DELAYED' in status_upper
        badge_bg = "bg-orange-100 text-orange-800" if is_delayed else "bg-red-100 text-red-800"
        btn_bg = "bg-orange-600 hover:bg-orange-700" if is_delayed else "bg-red-600 hover:bg-red-700"
        border_col = "border-orange-200" if is_delayed else "border-red-200"

        # Ícones SVG
        icon_plane = """<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>"""
        icon_clock = """<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>"""
        icon_ban = """<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" /></svg>"""
        icon_status = icon_clock if is_delayed else icon_ban
        icon_check = """<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" /></svg>"""
        icon_close = """<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>"""
        icon_back = """<svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>"""

        # Lógica de agrupamento
        if not related_dates:
            slug = self.generate_slug(flight)
            scheduled = self.safe_str(flight.get('scheduled_time', ''))
            if len(scheduled) >= 16:
                date_part = f"{scheduled[8:10]}/{scheduled[5:7]}"
                time_part = scheduled[11:16]
                date_display = f"{date_part} {time_part}"
            else:
                date_display = "N/A"
            related_dates = [(date_display, slug)]

        grouped_by_date = defaultdict(list)
        total_count = 0

        for datetime_str, slug in related_dates:
            total_count += 1
            clean_str = datetime_str.replace("ATRASADO", "").replace("CANCELADO", "").strip()
            parts = clean_str.split()
            date_key = parts[0] if parts else "N/A"
            time_val = parts[1] if len(parts) > 1 else "Ver"
            if len(date_key) >= 5 and '/' in date_key:
                grouped_by_date[date_key].append({'time': time_val, 'slug': slug})

        # Preview de datas únicas (DD/MM) para a frente do card
        unique_dates = set()
        for datetime_str, _ in related_dates:
            parts = datetime_str.split()
            date_key = parts[0] if parts else ""
            if len(date_key) >= 5 and "/" in date_key:
                try:
                    d, m = date_key.split("/")[:2]
                    unique_dates.add((int(m), int(d)))
                except (ValueError, IndexError):
                    pass
        all_dates_sorted = sorted(unique_dates, reverse=True)
        total_unique = len(all_dates_sorted)
        preview_5 = all_dates_sorted[:5]
        preview_dates = ", ".join([f"{d:02d}/{m:02d}" for m, d in preview_5]) if preview_5 else ""
        if total_unique > 5 and preview_dates:
            preview_dates += f" <span class=\"text-blue-600 font-semibold\">(+{total_unique - 5})</span>"
        # Ícone SVG calendário (Heroicons)
        icon_calendar = """<svg class="w-3.5 h-3.5 inline-block mr-1 text-gray-500 align-middle" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>"""

        # HTML do verso
        dates_buttons_html = ""
        times_containers_html = ""

        for date_key, times_list in grouped_by_date.items():
            safe_date_id = re.sub(r'[^a-zA-Z0-9]', '', date_key)
            dates_view_id = f"dates-{flight_id_safe}"
            times_view_id = f"times-{flight_id_safe}-{safe_date_id}"

            dates_buttons_html += f"""
        <button type="button"
                onclick="document.getElementById('{dates_view_id}').classList.add('hidden'); document.getElementById('{times_view_id}').classList.remove('hidden');"
                class="flex flex-col items-center justify-center p-2 rounded bg-slate-700 hover:bg-slate-600 border border-slate-600 transition-all text-white font-bold text-xs">
            {date_key}
        </button>
        """

            time_buttons = ""
            for t in times_list:
                time_buttons += f"""
            <a href="voo/{t['slug']}.html"
               class="block w-full text-center py-2 mb-2 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-colors">
                {t['time']}
            </a>
            """

            times_containers_html += f"""
        <div id="{times_view_id}" class="hidden flex flex-col h-full">
            <button type="button"
                    onclick="document.getElementById('{times_view_id}').classList.add('hidden'); document.getElementById('{dates_view_id}').classList.remove('hidden');"
                    class="flex items-center text-[10px] text-slate-400 hover:text-white mb-2 self-start uppercase tracking-wider">
                {icon_back} Voltar
            </button>
            <div class="flex-1 overflow-y-auto custom-scrollbar pr-1">
                <div class="text-center mb-2 text-sm font-bold text-white border-b border-slate-600 pb-1">{date_key}</div>
                {time_buttons}
            </div>
        </div>
        """

        card_id = f"card-{flight_id_safe}"
        dates_view_id = f"dates-{flight_id_safe}"

        return f"""
    <div class="group perspective-1000 w-full h-[280px]">
        <div class="flip-card-inner relative w-full h-full transform-style-3d shadow-sm hover:shadow-md transition-shadow rounded-2xl" id="{card_id}">
            <div class="card-front absolute w-full h-full backface-hidden bg-white rounded-2xl p-5 flex flex-col justify-between border {border_col} z-10">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-2 text-gray-700">
                        {icon_plane}<span class="font-bold text-sm tracking-wide">{airline}</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="flex items-center {badge_bg} text-xs font-bold px-2 py-1 rounded-md">
                            {icon_status}<span class="ml-1">{total_count}</span>
                        </span>
                        <span class="{badge_bg} text-xs font-bold px-2 py-1 rounded-md uppercase">{status_upper}</span>
                    </div>
                </div>
                <div class="text-center my-2">
                    <h3 class="text-4xl font-black text-gray-900 tracking-tighter">{flight_num}</h3>
                    <div class="flex items-center justify-center gap-2 text-gray-500 text-xs font-medium mt-1 uppercase tracking-widest">
                        <span>{origin}</span><span class="text-gray-300">•</span><span>{dest}</span>
                    </div>
                </div>
                <div class="mt-3 mb-2 px-1">
                    <p class="text-xs text-gray-500 font-medium truncate">{icon_calendar} {preview_dates if preview_dates else 'Datas não disponíveis'}</p>
                </div>
                <div class="mt-auto">
                    <button type="button" onclick="document.getElementById('{card_id}').classList.add('rotate-y-180')"
                            aria-label="Ver datas disponíveis" class="w-full {btn_bg} text-white font-bold py-3 rounded-xl shadow-sm transition-all transform active:scale-95 flex items-center justify-center gap-2 text-sm">
                        {icon_check}Verificar Indenização
                    </button>
                </div>
            </div>
            <div class="absolute w-full h-full backface-hidden rotate-y-180 bg-slate-800 rounded-2xl p-4 flex flex-col border border-slate-700 text-white shadow-xl">
                <div class="flex justify-between items-center mb-3 pb-2 border-b border-slate-600">
                    <div class="flex items-center gap-2 text-slate-300">
                        <span class="font-bold text-xs uppercase tracking-wide">Selecione</span>
                    </div>
                    <button type="button" onclick="document.getElementById('{card_id}').classList.remove('rotate-y-180')"
                            aria-label="Voltar" class="text-slate-400 hover:text-white transition-colors p-1">{icon_close}</button>
                </div>
                <div id="{dates_view_id}" class="flex-1 overflow-y-auto custom-scrollbar">
                    <div class="grid grid-cols-3 gap-2">{dates_buttons_html}</div>
                    <div class="mt-4 text-center"><p class="text-[10px] text-slate-500">Escolha a data do voo</p></div>
                </div>
                {times_containers_html}
            </div>
        </div>
    </div>
    """

    def get_view_more_card_html(
        self, city_name: str, total_hidden: int, hidden_flights: List[str], city_url: str
    ) -> str:
        """Gera card animado com ticker vertical de voos ocultos."""
        flight_items = "".join(
            f'<div class="ticker-item">✈ {fn}</div>' for fn in hidden_flights
        )
        ticker_content = f'<div class="ticker-loop">{flight_items}</div>' * 3
        return f"""
    <a href="{city_url}" class="group relative w-full h-[300px] bg-gradient-to-br from-blue-900 via-slate-800 to-slate-900 rounded-2xl p-6 flex flex-col justify-between overflow-hidden shadow-lg hover:shadow-2xl hover:scale-[1.02] transition-all duration-300 border border-blue-700/50">
        <div class="absolute inset-0 opacity-5">
            <div class="absolute inset-0" style="background-image: radial-gradient(circle, #fff 1px, transparent 1px); background-size: 20px 20px;"></div>
        </div>
        <div class="relative z-10">
            <h3 class="text-4xl font-black text-white mb-2">+{total_hidden}</h3>
            <p class="text-blue-200 text-sm font-medium leading-tight">
                Outros voos para<br>
                <span class="text-white text-lg font-bold">{city_name}</span>
            </p>
        </div>
        <div class="relative h-28 overflow-hidden mask-gradient-y my-3">
            <div class="animate-marquee-vertical">
                {ticker_content}
            </div>
        </div>
        <div class="relative z-10 flex items-center text-white font-bold text-sm group-hover:translate-x-2 transition-transform duration-300">
            Ver lista completa
            <svg class="w-5 h-5 ml-2 group-hover:ml-3 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"></path>
            </svg>
        </div>
    </a>
    """

    def generate_page_resilient(self, flight: Dict, metadata: Dict) -> bool:
        try:
            raw_fnum = self.safe_str(flight.get('flight_number'))
            status = self.safe_str(flight.get('status'))

            if not raw_fnum or not status:
                return False

            clean_fnum = "".join(filter(str.isdigit, raw_fnum))

            correction_iata = CORRECTIONS_DICT.get(clean_fnum)
            anac_iata = ANAC_DB.get(clean_fnum)

            if correction_iata:
                dest_iata = correction_iata
            elif anac_iata:
                dest_iata = anac_iata
            else:
                dest_iata = self.safe_str(flight.get('destination_iata')) or ''

            dest_city = IATA_TO_CITY_NAME.get(dest_iata) or getattr(
                enrichment_module, 'IATA_TO_CITY', {}
            ).get(dest_iata)
            if not dest_city:
                dest_city = self.safe_str(flight.get('destination')) or dest_iata or "Destino Desconhecido"

            context = self.prepare_template_context(flight, metadata)
            context.update({
                'destination': dest_city,
                'destination_iata': dest_iata,
                'destination_city': dest_city,
                'is_multiple': flight.get('occurrences_count', 1) > 1,
                'data_partida': context.get('data_partida') or self.safe_str(flight.get('data_partida')),
                'scheduled_time': self.safe_str(flight.get('scheduled_time')) or context.get('scheduled_time', ''),
                'display_time': context.get('display_time', ''),
                'status': status,
            })

            # --- LÓGICA SEO PROGRAMÁTICO (Injetar no dicionário 'voo') ---
            # Objetivo: Capturar buscas como "Indenização voo LA1234" ou "Voo GOL 1234 Atrasado"
            voo = {
                'Airline': context.get('airline', ''),
                'FlightNumber': context.get('flight_number', ''),
                'Status': context.get('status', ''),
                'Date': context.get('data_partida', ''),
            }
            # 1. Título da Página (<title>)
            # Ex: "Indenização Voo LA3030 (Latam) - Atrasado em Guarulhos | MatchFly"
            seo_title = f"Indenização Voo {voo.get('Airline', '')} {voo.get('FlightNumber', '')} - {voo.get('Status', '')} em Guarulhos | MatchFly"
            # 2. Meta Description (<meta name="description">)
            # Ex: "Teve problemas com o voo LA3030 em 15/02? Se atrasou mais de 4h, você pode ter direito a R$ 10.000. Verifique grátis agora."
            seo_description = (
                f"Teve problemas com o voo {voo.get('FlightNumber', '')} da {voo.get('Airline', '')} "
                f"no dia {voo.get('Date', '')}? Se houve atraso ou cancelamento, verifique seus direitos "
                f"de indenização imediatamente."
            )
            voo['seo_title'] = seo_title
            voo['seo_description'] = seo_description
            context['voo'] = voo

            # 4. Gerar HTML
            slug = self.generate_slug(flight)
            # Injeta dados de SEO no contexto
            seo_data = self._get_seo_context(flight, slug)
            context.update(seo_data)
            context.update(self._get_widget_context())

            filename = f"{slug}.html"
            
            template = self.jinja_env.get_template(self.template_file.name)
            with open(self.voo_dir / filename, 'w', encoding='utf-8') as f:
                f.write(template.render(**context))
            self.success_files.add(filename)

            # 5. Indexação (Home/Cidades)
            # Regra: Só indexa se tiver cidade válida (não for "Destino Desconhecido")
            is_valid_city = dest_city not in ["Destino Desconhecido", "Aguardando atualização", "N/A"]
            
            # Penalidade se não tiver IATA
            quality = 100 if dest_iata and is_valid_city else 50
            
            # Garante que as estatísticas de 30 dias existam (inteiros para o frontend)
            canc_30d = int(flight.get('cancelamentos_30d', 0) or 0)
            atrasos_30d = int(flight.get('atrasos_30d', 0) or 0)

            page_dict = {
                'filename': filename,
                'slug': slug,
                'flight_number': raw_fnum,
                'airline': context.get('airline', 'N/A'),
                'status': status,
                'scheduled_time': self.safe_str(flight.get('scheduled_time')) or context.get('scheduled_time', ''),
                'display_time': context.get('display_time') or self.safe_str(flight.get('scheduled_time')) or '',
                'destination': dest_city,
                'destination_iata': dest_iata,
                'destination_city': dest_city,
                'data_partida': self.safe_str(flight.get('data_partida')) or context.get('data_partida', ''),
                'delays_count': flight.get('occurrences_count', 0),
                'cancelamentos_30d': canc_30d,
                'atrasos_30d': atrasos_30d,
                'url': f"/voo/{filename}",
                'quality_score': quality
            }
            page_dict['date_time_fmt'] = format_date_time_fmt(page_dict)
            self.success_pages.append(page_dict)

            self.stats['successes'] += 1
            return True

        except Exception as e:
            logger.error(f"❌ Erro voo {self.safe_str(flight.get('flight_number'))}: {e}")
            return False
    
    def manage_orphans(self) -> None:
        """
        STEP 3.2: Gestão de Órfãos.
        Preserva arquivos antigos em public/voo/ (não regenerados nesta run) para SEO.
        Não remove mais órfãos; apenas registra preservação.
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 3.2: GESTÃO DE ÓRFÃOS")
        logger.info("=" * 70)
        
        existing_files = set(f.name for f in self.voo_dir.glob("*.html"))
        orphans = existing_files - self.success_files
        
        if orphans:
            logger.info(f"📂 {len(orphans)} arquivo(s) antigo(s) preservado(s) (histórico SEO):")
            for orphan in sorted(orphans):
                logger.info(f"   Arquivo antigo preservado: {orphan}")
                # Não removemos órfãos: manter páginas passadas acessíveis para SEO
                # orphan_path.unlink()  # REMOVIDO
        else:
            logger.info("✅ Nenhum arquivo órfão detectado")
    
    def generate_sitemap(self) -> None:
        """
        STEP 3.3: Gera sitemap.xml com URLs geradas com sucesso.
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 3.3: GERAÇÃO DE SITEMAP")
        logger.info("=" * 70)
        
        try:
            # Cria elemento raiz
            urlset = ET.Element('urlset')
            urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
            
            # Adiciona página inicial
            url_home = ET.SubElement(urlset, 'url')
            ET.SubElement(url_home, 'loc').text = self.base_url + "/"
            ET.SubElement(url_home, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
            ET.SubElement(url_home, 'changefreq').text = 'hourly'
            ET.SubElement(url_home, 'priority').text = '1.0'
            
            # Adiciona páginas de categoria
            category_pages = ['cancelados', 'atrasados']
            for category in category_pages:
                category_file = self.output_dir / f"{category}.html"
                if category_file.exists():
                    url_elem = ET.SubElement(urlset, 'url')
                    ET.SubElement(url_elem, 'loc').text = self.base_url + f"/{category}.html"
                    ET.SubElement(url_elem, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
                    ET.SubElement(url_elem, 'changefreq').text = 'hourly'
                    ET.SubElement(url_elem, 'priority').text = '0.9'
            
            # Adiciona página de cidades (índice)
            cidades_file = self.output_dir / "cidades.html"
            if cidades_file.exists():
                url_cidades = ET.SubElement(urlset, 'url')
                ET.SubElement(url_cidades, 'loc').text = self.base_url + "/cidades.html"
                ET.SubElement(url_cidades, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
                ET.SubElement(url_cidades, 'changefreq').text = 'daily'
                ET.SubElement(url_cidades, 'priority').text = '0.9'
            
            # Adiciona página institucional de Política de Privacidade (se existir)
            privacy_file = self.output_dir / "privacy.html"
            privacy_count = 0
            if privacy_file.exists():
                url_priv = ET.SubElement(urlset, 'url')
                ET.SubElement(url_priv, 'loc').text = self.base_url + "/privacy.html"
                ET.SubElement(url_priv, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
                ET.SubElement(url_priv, 'changefreq').text = 'yearly'
                ET.SubElement(url_priv, 'priority').text = '0.4'
                privacy_count = 1
            
            # Adiciona páginas de destino (cidades)
            for city in getattr(self, 'generated_cities', []):
                url_elem = ET.SubElement(urlset, 'url')
                ET.SubElement(url_elem, 'loc').text = self.base_url + "/" + city['url']
                ET.SubElement(url_elem, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
                ET.SubElement(url_elem, 'changefreq').text = 'daily'
                ET.SubElement(url_elem, 'priority').text = '0.85'
            
            # Adiciona páginas de voos
            for page in self.success_pages:
                url_elem = ET.SubElement(urlset, 'url')
                ET.SubElement(url_elem, 'loc').text = self.base_url + page['url']
                ET.SubElement(url_elem, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
                ET.SubElement(url_elem, 'changefreq').text = 'daily'
                ET.SubElement(url_elem, 'priority').text = '0.8'
            
            # Formata XML
            xml_str = minidom.parseString(ET.tostring(urlset)).toprettyxml(indent="  ")
            
            # Remove linhas vazias
            xml_str = '\n'.join([line for line in xml_str.split('\n') if line.strip()])
            
            # Salva sitemap
            sitemap_file = self.output_dir / "sitemap.xml"
            with open(sitemap_file, 'w', encoding='utf-8') as f:
                f.write(xml_str)
            
            category_count = sum(1 for cat in category_pages if (self.output_dir / f"{cat}.html").exists())
            cidades_count = 1 if cidades_file.exists() else 0
            city_count = len(getattr(self, 'generated_cities', []))
            total_urls = 1 + category_count + cidades_count + city_count + len(self.success_pages) + privacy_count
            logger.info(f"✅ Sitemap gerado: {sitemap_file}")
            logger.info(
                f"   • URLs incluídas: {total_urls} (1 home + {category_count} categorias + "
                f"{cidades_count} índice cidades + {city_count} destinos + {len(self.success_pages)} voos + {privacy_count} institucionais)"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar sitemap: {e}")

    def get_premium_gate(self) -> str:
        """Retorna um local premium aleatório para o widget (Seja o Herói do {{ gate_context }}!)."""
        locais = [
            'Terminal 3', 'Terminal 2', 'Portão 323', 'Portão 324',
            'Portão 305', 'Portão 202', 'Área VIP T3'
        ]
        return random.choice(locais)

    def _get_widget_context(self) -> Dict:
        """Contexto global para o widget de compartilhamento (base.html): gate_context e voos_hoje_count."""
        voos_count = getattr(self, '_total_flights', None)
        if voos_count is None:
            voos_count = len(getattr(self, 'success_pages', []))
        if not voos_count:
            voos_count = 850
        return {
            'gate_context': self.get_premium_gate(),
            'voos_hoje_count': voos_count,
        }
    
    def generate_homepage(self) -> None:
        """
        STEP 3.4: Gera public/index.html com Flip Cards organizados por cidade.
        Mantém estrutura visual: Rio de Janeiro → Cards → Ver mais.
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 3.4: GERAÇÃO DE HOME PAGE")
        logger.info("=" * 70)
        
        try:
            # Top cidades (gera agora caso não exista)
            if not hasattr(self, 'generated_cities'):
                self.generated_cities = self.generate_city_pages(self.success_pages)
            top_cities = getattr(self, 'generated_cities', [])
            
            # ETAPA 1: Agrupa voos por CIDADE
            flights_by_city = defaultdict(list)
            for page in self.success_pages:
                city_key = self._get_effective_destination_city(page)
                city_key = safe_str(city_key)
                if not city_key or city_key in ('Aguardando atualização', 'N/A', 'VAZIO'):
                    continue
                if self._is_city_blacklisted(city_key):
                    continue
                flights_by_city[city_key].append(page)
            
            # ETAPA 2: Top 20 cidades intercaladas (Nacional ↔ Internacional)
            BR_IATAS = {
                'GIG', 'SDU', 'BSB', 'CNF', 'SSA', 'REC', 'FOR',
                'POA', 'CWB', 'FLN', 'VIX', 'GYN', 'MAO', 'BEL', 'NAT', 'CGB', 'MCZ',
                'SLZ', 'JPA', 'AJU', 'THE', 'PVH', 'BVB', 'RBR', 'MCP', 'PMW', 'IOS',
                'NVT', 'LDB', 'RAO', 'UDI', 'IMP', 'JDO', 'PPB', 'STM', 'TFF',
            }
            national_cities = []
            international_cities = []
            for city_name, city_flights in flights_by_city.items():
                city_iatas_set = set()
                for f in city_flights:
                    iata = self.safe_str(f.get('destination_iata', ''))
                    if iata:
                        city_iatas_set.add(iata)
                is_national = bool(city_iatas_set & BR_IATAS)
                entry = (city_name, len(city_flights), city_flights)
                if is_national:
                    national_cities.append(entry)
                else:
                    international_cities.append(entry)
            national_cities.sort(key=lambda x: x[1], reverse=True)
            international_cities.sort(key=lambda x: x[1], reverse=True)
            interleaved = []
            max_len = max(len(national_cities), len(international_cities))
            for i in range(max_len):
                if i < len(national_cities):
                    interleaved.append(national_cities[i])
                if i < len(international_cities):
                    interleaved.append(international_cities[i])
            top_20_cities = interleaved[:20]

            city_data = OrderedDict()
            for city_name, _count, city_flights in top_20_cities:
                iata_codes = set()
                for f in city_flights:
                    iata = self.safe_str(f.get('destination_iata', ''))
                    if iata:
                        iata_codes.add(iata)
                city_iatas = sorted(list(iata_codes))
                grouped_by_flight_num = defaultdict(list)
                for flight in city_flights:
                    num = flight.get('flight_number')
                    if num:
                        grouped_by_flight_num[num].append(flight)
                groups_list = list(grouped_by_flight_num.values())
                cancelled = []
                delayed = []
                for group in groups_list:
                    statuses = [self.safe_str(f.get('status', '')).upper() for f in group]
                    if any("CANCELADO" in s or "CANCEL" in s for s in statuses):
                        cancelled.append(group)
                    elif any("ATRASADO" in s or "DELAY" in s for s in statuses):
                        delayed.append(group)
                cancelled.sort(key=lambda g: -len(g))
                delayed.sort(key=lambda g: -len(g))
                selected_groups = []
                if cancelled:
                    selected_groups.append(cancelled[0])
                if delayed:
                    selected_groups.append(delayed[0])
                if len(selected_groups) < 2:
                    remaining_pool = (cancelled[1:] if len(cancelled) > 1 else []) + (
                        delayed[1:] if len(delayed) > 1 else []
                    )
                    if not selected_groups and remaining_pool:
                        remaining_pool.sort(key=lambda g: -len(g))
                        selected_groups.extend(remaining_pool[:2])
                    elif len(selected_groups) == 1 and remaining_pool:
                        remaining_pool.sort(key=lambda g: -len(g))
                        selected_groups.append(remaining_pool[0])
                selected_groups = selected_groups[:2]
                city_cards = []
                for group in selected_groups:
                    related_dates = []
                    for f in group:
                        slug = self.generate_slug(f)
                        scheduled = self.safe_str(f.get('scheduled_time', ''))
                        if len(scheduled) >= 16:
                            date_display = f"{scheduled[8:10]}/{scheduled[5:7]} {scheduled[11:16]}"
                        elif len(scheduled) >= 10:
                            date_display = f"{scheduled[8:10]}/{scheduled[5:7]}"
                        else:
                            date_display = "N/A"
                        related_dates.append((date_display, slug))
                    city_cards.append(self.get_flight_card_flip_html(group[0], related_dates=related_dates))
                all_remaining = (
                    (cancelled[1:] if len(cancelled) > 1 else [])
                    + (delayed[1:] if len(delayed) > 1 else [])
                )
                if selected_groups:
                    taken = {id(g) for g in selected_groups}
                    all_remaining = [g for g in all_remaining if id(g) not in taken]
                all_remaining.sort(key=lambda g: -len(g))
                total_hidden = sum(len(g) for g in all_remaining)
                city_url = f"destino/{self.get_city_slug(city_name)}.html"
                if total_hidden > 0:
                    hidden_flights = [
                        g[0].get("flight_number", "N/A") for g in all_remaining[:15]
                    ]
                    city_cards.append(
                        self.get_view_more_card_html(
                            city_name, total_hidden, hidden_flights, city_url
                        )
                    )
                city_data[city_name] = {
                    "cards": city_cards,
                    "iatas": city_iatas,
                    "total_flights": len(city_flights),
                    "url": f"destino/{self.get_city_slug(city_name)}.html",
                }
            
            city_metadata = {}
            for city_name, info in city_data.items():
                city_metadata[city_name] = {
                    "iata": info["iatas"][0] if info["iatas"] else "",
                    "slug": self.get_city_slug(city_name),
                    "count": info["total_flights"],
                    "url": info["url"],
                }
            
            # recent_pages para schema/ticker (lista plana ordenada por data)
            all_recent = sorted(
                [f for fl in flights_by_city.values() for f in fl],
                key=parse_flight_time,
                reverse=True
            )[:20]
            
            voos_hoje_count = len(self.success_pages)
            herois_count = int(voos_hoje_count * 1.8) + random.randint(20, 35)
            gate_context = self.get_premium_gate()
            utm_suffix = '?utm_source=hero_gru'
            
            context = {
                'top_cities': top_cities[:20],
                'recent_pages': all_recent,
                'city_data': city_data,
                'home_city_cards': city_data,
                'city_metadata': city_metadata,
                'voos_hoje_count': voos_hoje_count,
                'herois_count': herois_count,
                'gate_context': gate_context,
                'utm_suffix': utm_suffix,
                'affiliate_link': self.affiliate_link,
                'ticker_flights': getattr(self, 'ticker_flights', []),
                'current_time': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'last_update': datetime.now().strftime('%d/%m/%Y às %H:%M'),
                'base_url': self.base_url,
            }
            # Dados para o Widget (includes/share_widget.html)
            context['gate_context'] = self.get_premium_gate()
            context['voos_hoje_count'] = getattr(self, '_total_flights', None) or len(self.success_pages)
            context['herois_count'] = random.randint(20, 50)
            
            template = self.jinja_env.get_template('index.html')
            html_content = template.render(**context)
            index_file = self.output_dir / "index.html"
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✅ Home page gerada: {index_file}")
            logger.info(f"   • {len(city_data)} cidades (nacional/int intercaladas) com Flip Cards (2 por cidade + Ver Mais)")
            logger.info(f"   • Growth: herois={herois_count}, gate={gate_context}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar home page: {e}")
    
    def generate_privacy_page(self) -> None:
        """
        Gera página institucional de Política de Privacidade em public/privacy.html.
        Usa o template Jinja2 privacy.html baseado em base.html.
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 3.8: GERAÇÃO DE PÁGINA DE PRIVACIDADE")
        logger.info("=" * 70)

        try:
            context = {
                'title': "Política de Privacidade - MatchFly",
                'meta_desc': (
                    "Entenda como o MatchFly trata sua privacidade e o uso de dados ao "
                    "acessar informações sobre voos atrasados e cancelados."
                ),
                'page_type': 'privacy',
                'base_url': self.base_url,
                'last_update': datetime.now().strftime('%d/%m/%Y às %H:%M'),
                'request_path': '/privacy.html',
            }
            context.update(self._get_widget_context())

            template = self.jinja_env.get_template('privacy.html')
            html_content = template.render(**context)

            output_file = self.output_dir / "privacy.html"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"Página de privacidade gerada: {output_file}")

        except Exception as e:
            logger.error(f"Erro ao gerar página de privacidade: {e}")

    def generate_404(self) -> None:
        """Gera página 404 profissional em output_dir/404.html usando base.html."""
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 3.8b: GERAÇÃO DE PÁGINA 404")
        logger.info("=" * 70)
        try:
            context = {
                'title': '404 - Página não encontrada | MatchFly',
                'meta_desc': 'Página não encontrada. Volte ao início do MatchFly.',
                'page_type': '404',
                'base_url': self.base_url,
                'request_path': '/404.html',
            }
            template = self.jinja_env.get_template('404.html')
            html_content = template.render(**context)
            output_file = self.output_dir / "404.html"
            output_file.write_text(html_content, encoding='utf-8')
            logger.info(f"Página 404 gerada: {output_file}")
        except Exception as e:
            logger.error(f"Erro ao gerar 404: {e}")

    def enrich_flight_with_30d_stats(self, flight: Dict) -> Dict:
        """
        Enriquece voo com contadores de 30 dias.
        Se não existirem, calcula baseado no status atual.
        
        Args:
            flight: Dicionário com dados do voo
            
        Returns:
            Voo enriquecido com cancelamentos_30d e atrasos_30d
        """
        enriched = flight.copy()
        
        # Se já existem os campos, usa eles
        if 'cancelamentos_30d' not in enriched or enriched.get('cancelamentos_30d') is None:
            status_lower = safe_str(enriched.get('status', '')).lower()
            if 'cancel' in status_lower:
                enriched['cancelamentos_30d'] = enriched.get('cancellations_count', random.randint(1, 5))
            else:
                enriched['cancelamentos_30d'] = enriched.get('cancellations_count', 0)

        if 'atrasos_30d' not in enriched or enriched.get('atrasos_30d') is None:
            status_lower = safe_str(enriched.get('status', '')).lower()
            if 'atras' in status_lower or enriched.get('delay_hours', 0) > 0:
                enriched['atrasos_30d'] = enriched.get('delays_count', random.randint(1, 8))
            else:
                enriched['atrasos_30d'] = enriched.get('delays_count', 0)
        
        if 'destination_iata' not in enriched or not enriched.get('destination_iata'):
            enriched['destination_iata'] = get_iata_code(safe_str(enriched.get('destination', '')))
        
        return enriched
    
    def get_lista_cancelados(self, flights: List[Dict]) -> List[Dict]:
        """
        Filtra e ordena voos cancelados com destination_iata.
        
        Args:
            flights: Lista de voos
            
        Returns:
            Lista filtrada e ordenada por cancelamentos_30d (desc), atrasos_30d (desc)
        """
        enriched_flights = [self.enrich_flight_with_30d_stats(f) for f in flights]
        
        # Filtra: cancelamentos_30d > 0 E destination_iata presente
        filtered = [
            f for f in enriched_flights
            if f.get('cancelamentos_30d', 0) > 0
            and f.get('destination_iata')
        ]
        
        # Ordena: 1. cancelamentos_30d (desc), 2. atrasos_30d (desc)
        sorted_list = sorted(
            filtered,
            key=lambda x: (x.get('cancelamentos_30d', 0), x.get('atrasos_30d', 0)),
            reverse=True
        )
        
        return sorted_list
    
    def get_lista_atrasados(self, flights: List[Dict]) -> List[Dict]:
        """
        Filtra e ordena voos atrasados com destination_iata.
        
        Args:
            flights: Lista de voos
            
        Returns:
            Lista filtrada e ordenada por atrasos_30d (desc), cancelamentos_30d (desc)
        """
        enriched_flights = [self.enrich_flight_with_30d_stats(f) for f in flights]
        
        # Filtra: atrasos_30d > 0 E destination_iata presente
        filtered = [
            f for f in enriched_flights
            if f.get('atrasos_30d', 0) > 0
            and f.get('destination_iata')
        ]
        
        # Ordena: 1. atrasos_30d (desc), 2. cancelamentos_30d (desc)
        sorted_list = sorted(
            filtered,
            key=lambda x: (x.get('atrasos_30d', 0), x.get('cancelamentos_30d', 0)),
            reverse=True
        )
        
        return sorted_list
    
    def generate_smart_ticker(self, flights: List[Dict]) -> List[Dict]:
        """
        Gera Smart Ticker com 10 voos aleatórios do TOP 20 com maior impacto.
        Usa hashlib e hora atual como seed para seleção determinística.
        
        Args:
            flights: Lista de voos
            
        Returns:
            Lista de 10 voos para o ticker (com slug)
        """
        # Enriquece voos
        enriched_flights = [self.enrich_flight_with_30d_stats(f) for f in flights]
        
        # Filtra apenas voos com destination_iata
        valid_flights = [f for f in enriched_flights if f.get('destination_iata')]
        
        # Calcula score: cancelamentos*3 + atrasos
        for flight in valid_flights:
            flight['_impact_score'] = (
                flight.get('cancelamentos_30d', 0) * 3 +
                flight.get('atrasos_30d', 0)
            )
        
        # Ordena por score (desc) e pega TOP 20
        top_20 = sorted(
            valid_flights,
            key=lambda x: x.get('_impact_score', 0),
            reverse=True
        )[:20]
        
        if not top_20:
            return []
        
        # Gera seed baseado na hora atual
        hour_seed = datetime.now().strftime('%Y-%m-%d-%H')
        seed_hash = hashlib.md5(hour_seed.encode()).hexdigest()
        random.seed(int(seed_hash[:8], 16))  # Usa primeiros 8 chars como int
        
        # Seleciona 10 aleatórios do TOP 20
        ticker_flights = random.sample(top_20, min(10, len(top_20)))
        
        # Adiciona slug para cada voo
        for flight in ticker_flights:
            flight['slug'] = self.generate_slug(flight)
        
        return ticker_flights
    
    # Blacklist de cidades inválidas - não gerar páginas para estes nomes
    BLACKLIST_CITIES = frozenset([
        "DESTINO DESCONHECIDO", "DESTINO INTERNACIONAL", "N/A", "VAZIO", "UNKNOWN",
        "AGUARDANDO ATUALIZAÇÃO", "DESCONHECIDO"
    ])

    def _is_city_blacklisted(self, city_name: str) -> bool:
        """Verifica se o nome da cidade é inválido (blacklist ou código ICAO)."""
        if not city_name or not isinstance(city_name, str):
            return True
        normalized = city_name.strip().upper()
        if normalized in self.BLACKLIST_CITIES:
            return True
        # Rejeita códigos ICAO (4 letras, maiúsculas) que apareceriam como siglas
        if len(normalized) == 4 and normalized.isalpha() and normalized.isupper():
            return True
        return False

    def generate_city_pages(self, flights: List[Dict], metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Gera páginas específicas por cidade de destino e retorna dados para a Home.
        Lista TODAS as cidades presentes no banco (flights); em cada cidade só inclui
        voos que tiveram página gerada (success_files) para evitar links quebrados.
        Ignora cidades na blacklist (ex: "Destino Desconhecido", siglas ICAO).
        """
        logger.info("=" * 70)
        logger.info("STEP 3.7: GERAÇÃO DE PÁGINAS DE CIDADE")
        
        city_groups = {}
        for flight in flights:
            # Usa cidade efetiva (resolução IATA/ANAC) para consistência com o restante do pipeline
            city = self._get_effective_destination_city(flight)
            city = safe_str(city)
            if not city or city in ('Aguardando atualização', 'N/A', 'VAZIO'):
                continue
            if self._is_city_blacklisted(city):
                continue

            if city not in city_groups:
                clean_fnum = "".join(filter(str.isdigit, self.safe_str(flight.get('flight_number', ''))))
                dest_iata = CORRECTIONS_DICT.get(clean_fnum) or ANAC_DB.get(clean_fnum) or self.safe_str(flight.get('destination_iata')) or ''
                city_groups[city] = {
                    'name': city,
                    'iata': dest_iata,
                    'flights': [],
                    'total_impact': 0
                }
            
            enriched = self.enrich_flight_with_30d_stats(flight)
            enriched['slug'] = self.generate_slug(enriched)
            enriched['filename'] = enriched['slug'] + '.html'
            enriched['date_time_fmt'] = format_date_time_fmt(enriched)
            # Só inclui na lista da cidade voos que tiveram página gerada (evita link quebrado)
            if enriched['filename'] in getattr(self, 'success_files', set()):
                city_groups[city]['flights'].append(enriched)
                impact = enriched.get('cancelamentos_30d', 0) * 3 + enriched.get('atrasos_30d', 0)
                city_groups[city]['total_impact'] += impact

        dest_dir = self.output_dir / "destino"
        dest_dir.mkdir(parents=True, exist_ok=True)
        generated_cities = []

        for city_name, data in city_groups.items():
            if self._is_city_blacklisted(city_name):
                continue
            # Ordenação estrita por data/hora: mais recente no topo (reverse chronological)
            data['flights'].sort(key=parse_flight_time, reverse=True)
            city_slug = self.get_city_slug(city_name)
            filename = f"{city_slug}.html"

            # Agrupar voos por número para Flip Cards 3D (Data → Horário; um card por número)
            flights_by_number = defaultdict(list)
            for f in data['flights']:
                num = f.get('flight_number')
                slug = f.get('slug') or self.generate_slug(f)
                scheduled = self.safe_str(f.get('scheduled_time', ''))
                if len(scheduled) >= 16:
                    date_display = f"{scheduled[8:10]}/{scheduled[5:7]} {scheduled[11:16]}"
                elif len(scheduled) >= 10:
                    date_display = f"{scheduled[8:10]}/{scheduled[5:7]}"
                else:
                    date_display = "N/A"
                flights_by_number[num].append((date_display, slug))
            flight_cards = []
            for num, dates_list in flights_by_number.items():
                first_flight = next((f for f in data['flights'] if f.get('flight_number') == num), None)
                if first_flight:
                    flight_cards.append(self.get_flight_card_flip_html(first_flight, related_dates=dates_list))

            context = {
                'title': f"Voos para {city_name} com Problemas | MatchFly",
                'h1': f"Voos para {city_name}: Relatório de Atrasos e Cancelamentos",
                'h2': f"Monitore voos para {city_name} ({data['iata']}) e peça indenização",
                'meta_desc': f"Lista de voos para {city_name} que atrasaram ou cancelaram recentemente. Veja se você tem direito a R$ 10.000.",
                'page_type': 'cidade',
                'city_name': city_name,
                'flights': data['flights'],
                'flight_cards': flight_cards,
                'base_url': self.base_url,
                'current_time': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'last_update': datetime.now().strftime('%d/%m/%Y às %H:%M'),
                'request_path': f'/destino/{filename}'
            }
            context.update(self._get_widget_context())

            template = self.jinja_env.get_template('atrasados.html')
            html_content = template.render(**context)
            
            with open(dest_dir / filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            generated_cities.append({
                'name': city_name,
                'iata': data['iata'],
                'url': f"destino/{filename}",
                'filename': filename,
                'total_impact': data['total_impact'],
                'top_flights': data['flights'][:2],
                'flight_count': len(data['flights'])
            })
        
        generated_cities.sort(key=lambda x: x['total_impact'], reverse=True)
        
        # Remove páginas órfãs em destino/ (ex: destino-desconhecido.html, mmmx.html)
        valid_filenames = {c['filename'] for c in generated_cities}
        for old_file in dest_dir.glob("*.html"):
            if old_file.name not in valid_filenames:
                try:
                    old_file.unlink()
                    logger.info(f"   🗑️ Removida página órfã: destino/{old_file.name}")
                except Exception as e:
                    logger.warning(f"   ⚠️ Não foi possível remover {old_file.name}: {e}")
        logger.info(f"✅ Geradas {len(generated_cities)} páginas de destino")
        return generated_cities

    def generate_all_cities_index(self) -> None:
        """
        Gera public/cidades.html - índice alfabético de todas as cidades válidas.
        Deve ser chamado após generate_city_pages (usa self.generated_cities).
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 3.7b: GERAÇÃO DE ÍNDICE DE CIDADES (cidades.html)")
        logger.info("=" * 70)
        cities = getattr(self, 'generated_cities', [])
        if not cities:
            logger.warning("⚠️ Nenhuma cidade gerada - cidades.html não criado")
            return
        # Ordena alfabeticamente por nome
        cities_sorted = sorted(cities, key=lambda x: (x['name'].upper(), x['name']))
        context = {
            'title': 'Cidades com Voos GRU | MatchFly',
            'meta_desc': 'Lista completa de cidades com voos partindo de Guarulhos.',
            'page_type': 'cidades',
            'cities': cities_sorted,
            'base_url': self.base_url,
            'last_update': datetime.now().strftime('%d/%m/%Y às %H:%M'),
            'request_path': '/cidades.html',
        }
        context.update(self._get_widget_context())
        template = self.jinja_env.get_template('cidades.html')
        html_content = template.render(**context)
        output_file = self.output_dir / "cidades.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"✅ Índice de cidades gerado: {output_file} ({len(cities_sorted)} cidades)")

    def generate_faq_schema(self, category: str) -> str:
        """
        Gera FAQ Schema (JSON-LD) baseado na categoria.
        
        Args:
            category: 'cancelados' ou 'atrasados'
            
        Returns:
            String JSON-LD formatada
        """
        if category == 'cancelados':
            faq_data = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "Tenho direito a indenização por voo cancelado?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Sim! Segundo a resolução 400 da ANAC, se seu voo foi cancelado sem aviso prévio de 72h ou por problemas operacionais, você pode ter direito a uma compensação de até R$ 10.000. Verifique seu caso aqui na AirHelp: https://www.airhelp.com/en-int/?ref=matchfly"
                        }
                    },
                    {
                        "@type": "Question",
                        "name": "Como pedir reembolso integral?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Em caso de cancelamento pela companhia, você tem direito a escolher entre reacomodação, execução por outro meio de transporte ou reembolso integral do valor pago."
                        }
                    }
                ]
            }
        else:  # atrasados
            faq_data = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "A partir de quanto tempo de atraso gera indenização?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Atrasos superiores a 4 horas permitem que o passageiro solicite indenização por danos morais. Além disso, a companhia deve fornecer assistência material (alimentação e comunicação) conforme o tempo de espera. Calcule sua compensação agora: https://www.airhelp.com/en-int/?ref=matchfly"
                        }
                    }
                ]
            }
        
        return json.dumps(faq_data, ensure_ascii=False, indent=2)
    
    def generate_category_page(self, category: str, flights: List[Dict], metadata: Dict) -> bool:
        """
        Gera página de categoria (cancelados.html ou atrasados.html).
        
        Args:
            category: 'cancelados' ou 'atrasados'
            flights: Lista de voos filtrados
            metadata: Metadados do scraping
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            # Determina configurações baseado na categoria
            if category == 'cancelados':
                title = "Voos Cancelados GRU - Indenização até R$ 10.000 | MatchFly"
                h1 = "Voos Cancelados em Guarulhos (GRU): Histórico e Como Receber Indenização"
                h2 = "Lista Atualizada dos Últimos 30 Dias + Compensação ANAC"
                meta_desc = "Veja o histórico dos voos mais cancelados em Guarulhos. Verifique se seu voo foi cancelado e receba compensação de até R$ 10.000 via AirHelp. Atualizado a cada 15min."
                page_type = "cancelados"
            else:  # atrasados
                title = "Voos Atrasados GRU - Monitoramento e Direitos | MatchFly"
                h1 = "Voos que Mais Atrasam em Guarulhos: Monitoramento em Tempo Real"
                h2 = "Evite Conexões Perdidas e Garanta Seus Direitos (EC 261 + ANAC 400)"
                meta_desc = "Monitoramento em tempo real dos voos mais atrasados em Guarulhos. Verifique seus direitos e receba compensação de até R$ 10.000. Atualizado a cada 15min."
                page_type = "atrasados"
            
            # Pega top 20 voos
            top_flights = flights[:20]
            
            # Prepara voos para o template (adiciona slug e dados necessários)
            template_flights = []
            for flight in top_flights:
                airline = infer_airline(
                    safe_str(flight.get('flight_number')),
                    safe_str(flight.get('airline')),
                )
                if airline in ["Não Informado", "DESCONHECIDO", "N/A"]:
                    continue
                raw_dest = safe_str(flight.get('destination', ''))
                if raw_dest == "Aguardando atualização" and not safe_str(flight.get('destination_iata')):
                    continue

                enriched = self.enrich_flight_with_30d_stats(flight)
                enriched['slug'] = self.generate_slug(enriched)
                enriched['airline'] = airline

                iata = safe_str(enriched.get('destination_iata', ''))
                raw_dest = safe_str(enriched.get('destination', ''))
                final_city = resolve_city_name(iata, raw_dest)

                enriched['destination_city'] = final_city
                enriched['destination'] = final_city

                if iata and final_city and final_city != iata:
                    enriched['display_destination'] = f"{iata} ({final_city})"
                else:
                    enriched['display_destination'] = iata or final_city

                enriched['total_problemas'] = (
                    int(enriched.get('cancelamentos_30d', 0) or 0) +
                    int(enriched.get('atrasos_30d', 0) or 0)
                )
                enriched['cancelamentos_30d'] = int(enriched.get('cancelamentos_30d', 0) or 0)
                enriched['atrasos_30d'] = int(enriched.get('atrasos_30d', 0) or 0)
                _st = safe_str(enriched.get('scheduled_time', ''))
                enriched['display_time'] = _st.split(' ')[-1] if (_st and ' ' in _st) else (_st or '')
                enriched['data_partida'] = safe_str(enriched.get('data_partida', ''))
                enriched['date_time_fmt'] = format_date_time_fmt(enriched)

                template_flights.append(enriched)
            
            # Gera FAQ Schema
            faq_schema = self.generate_faq_schema(category)
            
            # Flip Cards: agrupa por número de voo (mesma lógica das páginas de cidade)
            flights_by_number = defaultdict(list)
            for f in template_flights:
                num = f.get('flight_number')
                if num:
                    slug = f.get('slug') or self.generate_slug(f)
                    scheduled = self.safe_str(f.get('scheduled_time', ''))
                    if len(scheduled) >= 16:
                        date_display = f"{scheduled[8:10]}/{scheduled[5:7]} {scheduled[11:16]}"
                    elif len(scheduled) >= 10:
                        date_display = f"{scheduled[8:10]}/{scheduled[5:7]}"
                    else:
                        date_display = "N/A"
                    flights_by_number[num].append((date_display, slug))
            category_flight_cards = []
            for num, dates_list in flights_by_number.items():
                first_flight = next((x for x in template_flights if x.get('flight_number') == num), None)
                if first_flight:
                    category_flight_cards.append(self.get_flight_card_flip_html(first_flight, related_dates=dates_list))
            
            # Contexto para template (inclui widget global para base.html)
            context = {
                'title': title,
                'h1': h1,
                'h2': h2,
                'meta_desc': meta_desc,
                'page_type': page_type,
                'flights': template_flights,
                'flight_cards': category_flight_cards,
                'base_url': self.base_url,
                'current_time': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'last_update': datetime.now().strftime('%d/%m/%Y às %H:%M'),
                'request_path': f'/{category}.html',
                'ticker_flights': getattr(self, 'ticker_flights', []),  # Ticker já gerado
                'faq_schema': faq_schema,  # FAQ Schema para JSON-LD no head
            }
            context.update(self._get_widget_context())
            
            # Carrega template de categoria
            template = self.jinja_env.get_template(f'{category}.html')
            
            # Renderiza HTML
            html_content = template.render(**context)
            
            # Salva arquivo
            output_file = self.output_dir / f"{category}.html"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✅ Página de categoria gerada: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar página de categoria {category}: {e}")
            return False
    
    def run(self) -> Dict:
        """
        Executa o processo completo de geração de páginas.
        Arquitetura rigorosa: Setup → Cleanup → Generation → Orphans → Sitemap → Home.
        
        Returns:
            Dicionário com estatísticas da geração
        """
        try:
            logger.info("")
            logger.info("╔" + "═" * 68 + "╗")
            logger.info("║" + " " * 15 + "🚀 MATCHFLY PAGE GENERATOR v2.0" + " " * 22 + "║")
            logger.info("╚" + "═" * 68 + "╝")
            logger.info("")
            
            # ============================================================
            # STEP 1: SETUP & VALIDAÇÃO
            # ============================================================
            if not self.setup_and_validate():
                logger.error("Build interrompido na validação.")
                sys.exit(1)
            
            # ============================================================
            # STEP 2: INITIAL CLEANUP
            # ============================================================
            self.initial_cleanup()
            
            # ============================================================
            # STEP 3: WORKFLOW DE GERAÇÃO
            # ============================================================
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 3: WORKFLOW DE GERAÇÃO")
            logger.info("=" * 70)
            
            # Carrega dados
            data = self.load_flight_data()
            if not data:
                logger.error("❌ Não foi possível carregar dados")
                return self.stats
            
            flights = data.get('flights', [])
            metadata = data.get('metadata', {})
            
            self.stats['total_flights'] = len(flights)
            logger.info(f"📊 Total de voos carregados: {len(flights)}")
            
            if not flights:
                logger.warning("⚠️  Nenhum voo encontrado nos dados")
                return self.stats
            
            # ============================================================
            # STEP 3.0: ENRIQUECIMENTO DE DADOS (FALLBACK ESTÁTICO)
            # ============================================================
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 3.0: ENRIQUECIMENTO DE DESTINOS")
            logger.info("=" * 70)
            
            # Verifica se existem voos sem destination_iata
            flights_without_destination = [
                f for f in flights
                if not safe_str(f.get('destination_iata'))
            ]
            
            if flights_without_destination:
                logger.info(f"📊 Encontrados {len(flights_without_destination)} voos sem destination_iata")
                logger.info("   Iniciando enriquecimento com fallback estático...")
                
                # Validação pré-enriquecimento
                if not enrichment_module.validate_dictionaries():
                    raise Exception("Abortando: Dados estáticos inválidos.")
                
                # Análise antes do enriquecimento
                enrichment_module.analyze_failure_rate(flights, "ANTES")
                
                # Backup obrigatório para regressão
                flights_backup = copy.deepcopy(flights)
                
                # Enriquece voos (modifica in-place)
                stats = enrichment_module.enrich_missing_destinations(flights)
                
                # Teste de regressão
                if not enrichment_module.regression_test(flights_backup, flights):
                    logger.warning("⚠️  Aviso: Regressões encontradas, verifique os logs.")
                
                # Análise depois do enriquecimento
                enrichment_module.analyze_failure_rate(flights, "DEPOIS")
                logger.info(f"✅ Enriquecimento concluído: {stats['enriched']} recuperados.")
                
                # Salva dados enriquecidos apenas quando a fonte é JSON local (não Supabase)
                if not getattr(self, "_loaded_from_supabase", False):
                    try:
                        data["flights"] = flights
                        with open(self.data_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        logger.info("✅ Dados enriquecidos salvos em: %s", self.data_file)
                    except Exception as e:
                        logger.error("❌ Erro ao salvar dados enriquecidos: %s", e)
                else:
                    logger.info("✅ Dados enriquecidos em memória (fonte: Supabase; não gravando JSON)")
            else:
                logger.info("✅ Todos os voos já têm destination_iata - pulando enriquecimento")
            
            # ============================================================
            # REGRA DE EXCLUSÃO: Descartar voos que continuam "Destino Desconhecido"
            # (após enriquecimento: sem cidade identificada = não gera página, sitemap, home, cidades)
            # ============================================================
            UNKNOWN_DESTINATION_VALUES = ("Destino Desconhecido", "Aguardando atualização", "N/A")
            count_before_filter = len(flights)
            flights = [f for f in flights if self._get_effective_destination_city(f) not in UNKNOWN_DESTINATION_VALUES]
            discarded = count_before_filter - len(flights)
            if discarded:
                logger.info(f"📋 Excluídos {discarded} voos com Destino Desconhecido (após enriquecimento); restam {len(flights)} voos válidos.")
            
            self._total_flights = len(flights)
            
            # ============================================================
            # STEP 3.1: RENDERIZAÇÃO RESILIENTE
            # ============================================================
            logger.info("")
            logger.info("🔄 Iniciando renderização resiliente...")
            logger.info("-" * 70)
            
            for i, flight in enumerate(flights, 1):
                flight_number = flight.get('flight_number', f'UNKNOWN-{i}')

                # CRITICAL FIX: Tenta inferir companhia se estiver vazia ANTES de validar
                if not flight.get('airline') or flight.get('airline') == 'nan':
                    inferred = infer_airline(flight.get('flight_number'), "")
                    if inferred and inferred != "Não Informado":
                        flight['airline'] = inferred
                        # logger.info(f"🔮 Voo {flight.get('flight_number')} recuperado como {inferred}")

                # Só DEPOIS disso chama o validador
                if not self.should_generate_page(flight):
                    self.stats['filtered_out'] += 1
                    continue
                
                # Tenta gerar página (com try/except interno)
                logger.info(f"[{i}/{len(flights)}] Processando {flight_number}...")
                self.generate_page_resilient(flight, metadata)
            
            # ============================================================
            # STEP 3.2: GESTÃO DE ÓRFÃOS
            # ============================================================
            self.manage_orphans()
            
            # ============================================================
            # STEP 3.7: PÁGINAS DE CIDADE (antes do sitemap e da home)
            # Consolidação: cidades.html lista TODAS as cidades do banco (flights);
            # cada página de cidade só mostra voos que tiveram página gerada.
            # ============================================================
            if flights:
                self.generated_cities = self.generate_city_pages(flights, metadata)
                self.generate_all_cities_index()
            else:
                self.generated_cities = []
            
            # ============================================================
            # STEP 3.8: PÁGINA INSTITUCIONAL (POLÍTICA DE PRIVACIDADE)
            # ============================================================
            # Gera privacy.html sempre que houver build bem-sucedido
            self.generate_privacy_page()

            # STEP 3.8b: Página 404 (GitHub Pages)
            self.generate_404()

            # ============================================================
            # STEP 3.3: SITEMAP
            # ============================================================
            if self.success_pages:
                self.generate_sitemap()
                self._generate_robots_txt()
            else:
                logger.warning("⚠️  Nenhuma página gerada, sitemap não criado")
            
            # ============================================================
            # STEP 3.4: HOME PAGE
            # ============================================================
            if self.success_pages:
                self.generate_homepage()
            else:
                logger.warning("⚠️  Nenhuma página gerada, home page não criada")
            
            # ============================================================
            # STEP 3.5: SMART TICKER (gerado antes para uso nas páginas)
            # ============================================================
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 3.5: GERAÇÃO DE SMART TICKER")
            logger.info("=" * 70)
            
            ticker_flights = self.generate_smart_ticker(flights)
            logger.info(f"✅ Smart Ticker gerado: {len(ticker_flights)} voos selecionados")
            
            # Armazena ticker para uso em templates
            self.ticker_flights = ticker_flights
            
            # ============================================================
            # STEP 3.6: PÁGINAS DE CATEGORIA (pSEO)
            # ============================================================
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 3.6: GERAÇÃO DE PÁGINAS DE CATEGORIA")
            logger.info("=" * 70)
            
            # Gera listas filtradas e ordenadas por data/hora (mais recentes primeiro)
            lista_cancelados = self.get_lista_cancelados(flights)
            lista_atrasados = self.get_lista_atrasados(flights)
            lista_cancelados = sorted(lista_cancelados, key=parse_flight_time, reverse=True)
            lista_atrasados = sorted(lista_atrasados, key=parse_flight_time, reverse=True)
            
            logger.info(f"📊 Voos cancelados filtrados: {len(lista_cancelados)}")
            logger.info(f"📊 Voos atrasados filtrados: {len(lista_atrasados)}")
            
            # Gera páginas de categoria
            if lista_cancelados:
                self.generate_category_page('cancelados', lista_cancelados, metadata)
            else:
                logger.warning("⚠️  Nenhum voo cancelado encontrado para gerar página")
            
            if lista_atrasados:
                self.generate_category_page('atrasados', lista_atrasados, metadata)
            else:
                logger.warning("⚠️  Nenhum voo atrasado encontrado para gerar página")
            
            # ============================================================
            # STEP 4: LOG FINAL
            # ============================================================
            self.print_final_summary()
            
            return self.stats
            
        except KeyboardInterrupt:
            logger.warning("\n⚠️  Build interrompido pelo usuário")
            sys.exit(1)
        except Exception as e:
            logger.error(f"\n❌ Erro fatal no gerador: {e}", exc_info=True)
            sys.exit(1)
    
    def print_final_summary(self) -> None:
        """Imprime sumário final do build."""
        logger.info("")
        logger.info("╔" + "═" * 68 + "╗")
        logger.info("║" + " " * 23 + "✅ BUILD FINALIZADO!" + " " * 24 + "║")
        logger.info("╚" + "═" * 68 + "╝")
        logger.info("")
        logger.info("📊 SUMÁRIO DO BUILD:")
        logger.info(f"   • Voos processados:     {self.stats['total_flights']}")
        logger.info(f"   • Sucessos:             {self.stats['successes']} páginas")
        logger.info(f"   • Falhas:               {self.stats['failures']} páginas")
        logger.info(f"   • Filtrados (< 15min):  {self.stats['filtered_out']} voos")
        logger.info(f"   • Órfãos removidos:     {self.stats['orphans_removed']} arquivos")
        logger.info(f"   • Sitemap:              Atualizado com {self.stats['successes']} URLs")
        logger.info("")
        logger.info(f"📁 Output:")
        logger.info(f"   • Páginas de voos:      {self.voo_dir}/")
        logger.info(f"   • Home page:            {self.output_dir}/index.html")
        logger.info(f"   • Sitemap:              {self.output_dir}/sitemap.xml")
        logger.info("")
        
        if self.stats['successes'] > 0:
            logger.info("🎉 Build concluído com sucesso!")
            logger.info(f"🌐 Abra {self.output_dir}/index.html no navegador")
            logger.info("")
            logger.info("✅ MatchFly: Dicionário IATA expandido com sucesso!")
            
            # Toca som de sucesso (Glass.aiff no macOS)
            try:
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'], 
                             check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass  # Ignora erro se o som não puder ser tocado
        else:
            logger.warning("⚠️  Nenhuma página foi gerada!")
        
        logger.info("")
        logger.info("=" * 70)


def main():
    """Função principal para executar o gerador."""
    
    # ============================================================
    # CONFIGURAÇÃO: AFFILIATE LINK (DEEP LINK OTIMIZADO)
    # ============================================================
    # Deep Link da AirHelp que pré-preenche o formulário de verificação
    # Parâmetros dinâmicos: flightNumber e departureAirport serão adicionados automaticamente
    # Isso elimina fricção e aumenta a conversão drasticamente
    AFFILIATE_LINK = "https://www.airhelp.com/pt-br/verificar-indenizacao/?utm_medium=affiliate&utm_source=pap&utm_campaign=aff-69649260287c5&a_aid=69649260287c5&a_bid=c63de166"
    
    # URL base para sitemap (altere para seu domínio)
    BASE_URL = "https://matchfly.org"
    
    # ============================================================
    # Cria gerador com configurações
    # ============================================================
    generator = FlightPageGenerator(
        data_file="data/flights-db.json",
        template_file="src/templates/tier2-anac400.html",
        output_dir="docs",
        voo_dir="docs/voo",
        affiliate_link=AFFILIATE_LINK,
        base_url=BASE_URL
    )
    
    # ============================================================
    # Executa workflow completo
    # ============================================================
    stats = generator.run()
    
    # Exit code baseado em sucessos
    if stats['successes'] > 0:
        sys.exit(0)  # Sucesso
    else:
        sys.exit(1)  # Falha


if __name__ == "__main__":
    main()

