import pandas as pd
import glob

files = glob.glob('data/*.xls')
print(f'📊 Analisando {files[0]}\n')

# Lê arquivo pulando título, pegando header multi-linha
df = pd.read_excel(files[0], engine='xlrd', skiprows=3)  # Pula linha 0,1,2 (título+header+separador)

# Define colunas manualmente baseado na estrutura ANAC
df.columns = ['Empresa Aérea', 'Nº Voo', 'Origem OACI', 'Nome Origem', 
              'Destino OACI', 'Nome Destino', 'Etapas', '% Cancelamento', 
              '% Atraso >30min', '% Atraso >60min']

print(f'Colunas renomeadas:\n{list(df.columns)}\n')
print(f'Primeiras 5 linhas:\n{df.head(5)}')

# Filtra GRU
gru = df[df['Origem OACI'] == 'SBGR']
print(f'\n✅ Total linhas GRU: {len(gru)}')
print(f'Primeiros 3 voos GRU:\n{gru[["Nº Voo", "Destino OACI", "% Cancelamento"]].head(3)}')
