import json

# Expande mapeamento (códigos que ficaram como OACI)
OACI_EXTRA = {
    'SBCY': 'CGB', 'SPJC': 'JUL', 'SBJU': 'JJG', 'SACO': 'COR',
    'SBJE': 'JPA', 'KIAH': 'IAH', 'MDPC': 'PUJ', 'SBCY': 'CGB'
}

with open('data/flights-db.json', 'r') as f:
    data = json.load(f)

atualizado = 0
for flight in data['flights']:
    dest = flight.get('destination_iata')
    if dest and len(dest) == 4:  # É OACI (4 letras)
        iata = OACI_EXTRA.get(dest)
        if iata:
            flight['destination_iata'] = iata
            atualizado += 1
            print(f'✅ {flight["flight_number"]} → {dest} convertido para {iata}')

with open('data/flights-db.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f'\n✅ {atualizado} voos com OACI convertidos para IATA')
