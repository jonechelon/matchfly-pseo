import json
import os
import sys
from pathlib import Path

# Adiciona diretório raiz ao path para importar src
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

try:
    from src.scl_corrections import CORRECTIONS_DICT
except ImportError as e:
    print(f"❌ Erro de importação (scl_corrections): {e}")
    sys.exit(1)

try:
    from src.generator import IATA_TO_CITY_NAME
except ImportError:
    IATA_TO_CITY_NAME = {}  # fallback: usa IATA como nome se generator não disponível


def fix_database():
    print("🧹 Iniciando Higienização do Banco de Dados...")

    # Caminhos
    db_path = root_dir / "data" / "flights-db.json"
    backup_path = root_dir / "data" / "flights-db.backup.json"

    if not db_path.exists():
        print(f"❌ Banco não encontrado: {db_path}")
        return

    # Carregar
    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    flights = data.get("flights", [])
    print(f"📊 Total de voos antes: {len(flights)}")

    fixed_count = 0

    for flight in flights:
        # Limpa número
        raw_num = str(flight.get("flight_number", ""))
        clean_num = "".join(filter(str.isdigit, raw_num))

        # Verifica se existe correção
        real_iata = CORRECTIONS_DICT.get(clean_num)

        if real_iata:
            current_iata = flight.get("destination_iata")

            # Só aplica se for diferente ou se estiver vazio
            if current_iata != real_iata:
                # Atualiza IATA
                flight["destination_iata"] = real_iata

                # Atualiza Nome (usando dicionário do generator se disponível, ou genérico)
                real_name = IATA_TO_CITY_NAME.get(real_iata, real_iata)
                flight["destination"] = real_name
                flight["destination_city"] = real_name

                fixed_count += 1
                # print(f"🔧 Corrigido: {raw_num} | {current_iata} -> {real_iata}")

    # Salvar Backup
    if not backup_path.exists():
        with open(db_path, "r", encoding="utf-8") as f_orig:
            with open(backup_path, "w", encoding="utf-8") as f_bkp:
                f_bkp.write(f_orig.read())
        print(f"💾 Backup salvo em: {backup_path}")

    # Salvar JSON Corrigido
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("-" * 40)
    print("✅ Higienização Concluída!")
    print(f"🔧 Voos corrigidos: {fixed_count}")
    print(f"📂 Banco salvo em: {db_path}")


if __name__ == "__main__":
    fix_database()
