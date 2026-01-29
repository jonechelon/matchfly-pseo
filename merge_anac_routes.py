import pandas as pd
import json
import glob

files = sorted(glob.glob('data/*.xls'))  # Ordena Jul→Dez
print(f'📊 Processando {len(files)} arquivos ANAC\n')

routes = {}  # {num_voo: destino_iata}

for f in files:
    mes = f.split('/')[-1]
    df = pd.read_excel(f, engine='xlrd', skiprows=3)
    df.columns = ['Empresa Aérea', 'Nº Voo', 'Origem OACI', 'Nome Origem', 
                  'Destino OACI', 'Nome Destino', 'Etapas', '% Cancelamento', 
                  '% Atraso >30min', '% Atraso >60min']
    
    gru = df[df['Origem OACI'] == 'SBGR'][['Nº Voo', 'Destino OACI']].dropna()
    
    for _, row in gru.iterrows():
        voo = str(row['Nº Voo']).strip().upper()
        dest = str(row['Destino OACI']).strip()
        if voo and dest and dest != 'nan':
            routes[voo] = dest
    
    print(f'{mes}: {len(gru)} linhas GRU → {len(routes)} rotas acumuladas')

# Salva JSON
output = 'data/specificroutes_anac.json'
with open(output, 'w') as fp:
    json.dump(routes, fp, indent=2)

print(f'\n✅ {len(routes)} rotas únicas salvas em {output}')
print(f'Exemplos: {dict(list(routes.items())[:5])}')
