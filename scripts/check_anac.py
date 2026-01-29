import sys
from pathlib import Path

import pandas as pd

# Raiz do projeto para paths relativos (scripts/ está em raiz/scripts)
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

files = sorted(DATA_DIR.glob("*.xls"))
print(f'📊 {len(files)} arquivos ANAC')
for f in files[-6:]:  # Últimos 6
    df = pd.read_excel(f)
    gru = df[df['Origem OACI'] == 'SBGR'].shape[0]
    print(f'{f.name}: {gru} linhas GRU')
