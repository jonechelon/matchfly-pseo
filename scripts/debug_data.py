import json
import csv
import re
import sys
from pathlib import Path

# Raiz do projeto para importar src e ler data/ (scripts/ está em raiz/scripts)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data"


def debug():
    print("--- INICIANDO DIAGNÓSTICO DE DADOS ---\n")

    # 1. Carregar ANAC DB
    anac_path = DATA_DIR / "specificroutes_anac.json"
    if not anac_path.exists():
        print(f"❌ Banco ANAC não encontrado: {anac_path}")
        return

    print(f"📂 Lendo banco ANAC de: {anac_path.absolute()}")

    try:
        with open(anac_path, 'r', encoding='utf-8') as f:
            anac_db = json.load(f)
        print(f"✅ ANAC DB carregado. Total rotas: {len(anac_db)}")
        print(f"🔍 Amostra ANAC: {list(anac_db.items())[:3]}")
    except Exception as e:
        print(f"❌ Erro fatal ao ler ANAC DB: {e}")
        return

    print("\n--------------------------------------------------\n")

    # 2. Carregar CSV (data/voos_atrasados_gru.csv ou variante com sufixo)
    csv_path = DATA_DIR / "voos_atrasados_gru (1).csv"
    if not csv_path.exists():
        csv_path = DATA_DIR / "voos_atrasados_gru.csv"
    if not csv_path.exists():
        print(f"❌ CSV não encontrado em {DATA_DIR}")
        return

    print(f"📂 Lendo CSV de: {csv_path.absolute()}")

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Detectar delimitador se necessário, mas assumindo vírgula
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample)
            reader = csv.DictReader(f, dialect=dialect)

            print(f"✅ CSV Headers: {reader.fieldnames}")

            print("\n--- TESTANDO MATCHING NAS PRIMEIRAS 20 LINHAS ---\n")

            count = 0
            matches = 0
            for row in reader:
                if count >= 20:
                    break

                # Tenta pegar numero do voo (varias possibilidades de header)
                raw_num = row.get('Numero_Voo') or row.get('flight_number') or row.get('numero')
                if not raw_num:
                    print(f"⚠️ Linha {count}: Sem número de voo. Row: {row}")
                    continue

                # Limpeza (Simulando o generator)
                clean_num = "".join(filter(str.isdigit, str(raw_num)))

                # Busca
                # Tenta string direta (json keys geralmente sao strings)
                match = anac_db.get(clean_num)

                status = "✅ MATCH" if match else "❌ FAIL"
                print(
                    f"Linha {count:02d} | Original: '{raw_num}' | Limpo: '{clean_num}' | Resultado: {status} -> {match}"
                )

                if match:
                    matches += 1
                count += 1

            print(f"\n📊 Resumo da Amostra: {matches}/{count} encontrados.")

    except Exception as e:
        print(f"❌ Erro ao ler CSV: {e}")


if __name__ == "__main__":
    debug()

