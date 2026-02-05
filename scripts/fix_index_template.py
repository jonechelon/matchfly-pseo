import re

# Lê template atual
with open('templates/index.html', 'r') as f:
    content = f.read()

# Padrão antigo (provável): {{ flight.destination }} ou {{ flight.destination|default('Aguardando...') }}
# Novo padrão: usar destination_iata com fallback

# Substituições
replacements = [
    # Destino texto
    (r"Destino:\s*{{\s*flight\.destination\s*\|\s*default\(['\"]Aguardando atualização['\"]\)\s*}}",
     "Destino: {% if flight.destination_iata %}{{ flight.destination_iata }}{% else %}Aguardando atualização{% endif %}"),
    
    # Variação sem default
    (r"Destino:\s*{{\s*flight\.destination\s*}}",
     "Destino: {% if flight.destination_iata %}{{ flight.destination_iata }}{% else %}Aguardando atualização{% endif %}"),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Salva
with open('templates/index.html', 'w') as f:
    f.write(content)

print("✅ Template index.html corrigido!")
