import json

# Mapeamento OACI → IATA aeroportos comuns
OACI_TO_IATA = {
    'SBCT': 'CWB', 'SBGO': 'GYN', 'SAME': 'EZE', 'SBFL': 'FLN', 'SBMO': 'MVF',
    'SCEL': 'SCL', 'SBGL': 'GIG', 'SBBR': 'BSB', 'SBPA': 'POA', 'SBSV': 'SSA',
    'SBRJ': 'SDU', 'SBRF': 'REC', 'SBCF': 'CNF', 'SBSP': 'CGH', 'SBBH': 'CNF',
    'KMIA': 'MIA', 'KJFK': 'JFK', 'KEWR': 'EWR', 'KATL': 'ATL', 'KORD': 'ORD',
    'LEMD': 'MAD', 'LFPG': 'CDG', 'EGLL': 'LHR', 'EHAM': 'AMS', 'LIRF': 'FCO',
    'OMDB': 'DXB', 'VHHH': 'HKG', 'RJAA': 'NRT', 'YSSY': 'SYD', 'FAOR': 'JNB',
    'SAEZ': 'EZE', 'SABE': 'AEP', 'SUMU': 'MVD', 'SPIM': 'LIM', 'SKBO': 'BOG',
    'SBGR': 'GRU', 'SBKP': 'VCP', 'SBEG': 'MAO', 'SBFZ': 'FOR', 'SBBE': 'BEL'
}

# Carrega bases
with open('data/flights-db.json', 'r') as f:
    flights_db = json.load(f)

with open('data/specificroutes_anac.json', 'r') as f:
    anac_routes = json.load(f)

# Enriquece voos sem destino
enriquecidos = 0
falhados = []

for flight in flights_db.get('flights', []):
    # Ignora se já tem destino
    if flight.get('destination_iata'):
        continue
    
    fnum = str(flight.get('flight_number', '')).strip().upper()
    
    # Busca em ANAC
    if fnum in anac_routes:
        oaci = anac_routes[fnum]
        iata = OACI_TO_IATA.get(oaci, oaci)  # Converte ou mantém OACI
        
        flight['destination_iata'] = iata
        flight['enrichment_status'] = 'success'
        flight['enrichment_source'] = 'anac_routes'
        enriquecidos += 1
        print(f'✅ {fnum} → {oaci} ({iata})')
    else:
        falhados.append(fnum)

# Salva base atualizada
with open('data/flights-db.json', 'w') as f:
    json.dump(flights_db, f, indent=2)

print(f'\n📊 Resumo:')
print(f'✅ Enriquecidos: {enriquecidos}')
print(f'❌ Não encontrados: {len(falhados)}')
print(f'Exemplos não mapeados: {list(set(falhados))[:10]}')
