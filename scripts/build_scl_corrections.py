#!/usr/bin/env python3
"""
Gera CORRECTIONS_DICT: voos LATAM GRU erroneamente classificados como SCL -> IATA real.
Fonte: data/specificroutes_anac.json + ICAO->IATA (generator + extras).
"""

import json
from pathlib import Path

# Base: generator ICAO_TO_IATA
ICAO_TO_IATA = {
    'SBGR': 'GRU', 'SBSP': 'CGH', 'SBGL': 'GIG', 'SBRJ': 'SDU', 'SBBR': 'BSB',
    'SBCF': 'CNF', 'SBSV': 'SSA', 'SBRF': 'REC', 'SBCT': 'CWB', 'SBPA': 'POA',
    'SBFL': 'FLN', 'SBEG': 'MAO', 'SBGO': 'GYN', 'SBVT': 'VIX', 'SBNF': 'NVT',
    'SBCY': 'CGB', 'SBBE': 'BEL', 'SBMO': 'MCZ', 'SBFI': 'IGU', 'SBPS': 'BPS',
    'SBJP': 'JPA', 'SBKG': 'CKG', 'SBAR': 'AJU', 'SBPL': 'PNZ', 'SBSL': 'SLZ',
    'SBTE': 'THE', 'SBPV': 'PVH', 'SBRB': 'RBR', 'SBMQ': 'MCP', 'SBBV': 'BVB',
    'SBSR': 'SJP', 'SBJU': 'JDO', 'SBIL': 'IOS', 'SBCG': 'CGR', 'SBUL': 'UDI',
    'KMIA': 'MIA', 'KJFK': 'JFK', 'KMCO': 'MCO', 'KATL': 'ATL', 'KLAX': 'LAX',
    'EGLL': 'LHR', 'LFPG': 'CDG', 'LEMD': 'MAD', 'EDDF': 'FRA', 'EHAM': 'AMS',
    'LPPT': 'LIS', 'LIMC': 'MXP', 'LIRF': 'FCO', 'LEBL': 'BCN', 'LSZH': 'ZRH',
    'SAEZ': 'EZE', 'SABE': 'AEP', 'SCEL': 'SCL', 'SPJC': 'LIM', 'SKBO': 'BOG',
    'SUMU': 'MVD', 'SGAS': 'ASU', 'SLVR': 'VVI', 'OMDB': 'DXB', 'OTHH': 'DOH',
}
# Extras (ANAC usa, generator não)
ICAO_TO_IATA.update({
    'SBPJ': 'PMW',   # Palmas
    'SBFN': 'FEN',   # Fernando de Noronha
    'SBSG': 'NAT',   # Natal São Gonçalo do Amarante
    'SBCH': 'XAP',   # Chapecó
    'SBVC': 'VDC',   # Vitória da Conquista
    'SBJV': 'JOI',   # Joinville
    'SBJA': 'JJG',   # Jaguaruna
    'SBMG': 'MGF',   # Maringá
    'SBFZ': 'FOR',   # Fortaleza
    'KBOS': 'BOS',   # Boston
    'KIAD': 'IAD',   # Washington Dulles
})

SUSPECTS = [
    "3265", "3268", "3276", "3288", "3316", "3334", "3346", "3354", "3394", "3408",
    "3556", "3562", "3604", "3620", "3790", "3828", "3832", "3834", "3856", "4413",
    "4550", "4666", "5126", "5152", "5156", "5172", "5176", "5184", "5185", "5223",
    "5250", "5251", "5501", "5561", "6050", "6051", "6052", "6054", "6219", "6240",
    "6265", "6270", "6314", "6504", "6728", "6763", "7110", "7255", "7805", "8072",
    "8089", "8097", "8110", "8115", "8117", "8121", "8125", "8164", "8180", "8190",
    "8200", "8202", "8225", "8227", "8349", "8376", "8416", "8422", "8497", "8514",
    "9746",
    "1070", "1924", "2328", "2329", "2357", "3340", "3366", "3368", "3698", "3874",
    "3945", "3947", "3974", "4065", "4070", "4126", "4193", "4227", "4305", "4307",
    "4548", "4653", "4771", "4796", "4797", "5190", "5225", "5357", "5538", "6099",
    "6187", "6193", "6199", "6238", "6242", "6271", "6603", "6647", "6690", "6719",
    "6720", "6721", "7120", "7250", "7260", "7269", "7277", "7335", "7344", "7347",
    "7350", "7355", "7361", "7392", "7536", "7586", "7702", "7741", "8471", "8475",
    "8476", "8490", "8558", "8643", "9072", "9173", "9253", "9254", "9700", "9809",
    "9813",
]


def icao_to_iata(icao: str) -> str:
    if not icao or len(icao) < 3:
        return icao
    if icao in ICAO_TO_IATA:
        return ICAO_TO_IATA[icao]
    if len(icao) == 4 and icao.startswith("K"):
        return icao[1:]
    return icao


# Raiz do projeto (scripts/ está em raiz/scripts)
ROOT = Path(__file__).resolve().parent.parent


def main():
    p = ROOT / "data" / "specificroutes_anac.json"
    with open(p, "r", encoding="utf-8") as f:
        anac = json.load(f)

    out = {}
    missing = []
    for k in SUSPECTS:
        icao = anac.get(k)
        if not icao:
            missing.append(k)
            continue
        iata = icao_to_iata(icao)
        out[k] = iata

    print("# CORRECTIONS_DICT — Voos LATAM GRU mal classificados como SCL -> IATA real")
    print("# Fonte: ANAC specificroutes_anac.json + ICAO->IATA")
    print("")
    print("CORRECTIONS_DICT = {")
    INTL = {"JFK", "MIA", "BOS", "IAD", "FRA", "LIS", "MXP", "LIM", "MVD", "SCL", "EZE", "AEP"}
    for k in sorted(out.keys(), key=lambda x: (x.isdigit(), int(x) if x.isdigit() else 0, x)):
        v = out[k]
        comment = ""
        if v == "SCL":
            comment = "  # Santiago"
        elif v in INTL:
            comment = "  # internacional"
        print(f'    "{k}": "{v}",{comment}')
    print("}")
    if missing:
        print("")
        print("# Não encontrados na ANAC:", missing)


if __name__ == "__main__":
    main()
