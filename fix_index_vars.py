with open('src/templates/index.html', 'r') as f:
    content = f.read()

# Troca todas ocorrências de page. por flight. no bloco de cards
content = content.replace('page.destination_iata', 'flight.destination_iata')
content = content.replace('page.destination_city', 'flight.destination_city')
content = content.replace('page.airline', 'flight.airline')
content = content.replace('page.flight_number', 'flight.flight_number')
content = content.replace('page.status', 'flight.status')
content = content.replace('page.hora_partida', 'flight.hora_partida')
content = content.replace('page.data_partida', 'flight.data_partida')

with open('src/templates/index.html', 'w') as f:
    f.write(content)

print("✅ Variáveis corrigidas: page.* → flight.*")
