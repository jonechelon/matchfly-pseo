import json
import os
from collections import Counter
from pathlib import Path

def audit():
    print("🕵️‍♂️ Iniciando Auditoria de Santiago (SCL)...")
    
    # Tenta encontrar o arquivo em vários lugares
    paths = [
        Path('data/flights-db.json'),
        Path('flights-db.json'),
        Path('../data/flights-db.json')
    ]
    
    db_path = next((p for p in paths if p.exists()), None)
    
    if not db_path:
        print("❌ Erro: Arquivo flights-db.json não encontrado!")
        print(f"   Diretório atual: {os.getcwd()}")
        print("   Certifique-se de ter rodado 'python3 src/generator.py' antes.")
        return

    print(f"📂 Lendo banco de dados: {db_path}")
    
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        flights = data.get('flights', [])
        print(f"📊 Total de voos no banco: {len(flights)}")
        
        scl_suspects = []
        for f in flights:
            # Verifica se o destino foi definido como SCL ou Santiago
            dest_iata = f.get('destination_iata', '')
            dest_name = f.get('destination', '')
            
            is_scl = 'SCL' in dest_iata or 'Santiago' in dest_name
            
            if is_scl:
                num = str(f.get('flight_number', 'N/A'))
                # Ignora os voos que CONFIRMAMOS serem para SCL
                # Adicione aqui os voos reais se souber
                known_scl = ['8050', '8051', '750', '751', 'LA8050', 'LA8051']
                
                clean_num = "".join(filter(str.isdigit, num))
                
                if clean_num not in ['8050', '8051', '750', '751']: 
                    scl_suspects.append(num)

        print(f"\n🚨 Total de suspeitos indo para Santiago: {len(scl_suspects)}")
        
        if scl_suspects:
            print("\n📋 LISTA PARA O CURSOR (Copie abaixo):")
            print("-" * 50)
            # Conta frequência e ordena
            counts = Counter(scl_suspects)
            
            # Formata como lista Python para facilitar
            lista_str = ", ".join([f'"{k}"' for k in sorted(counts.keys())])
            print(f"[{lista_str}]")
            print("-" * 50)
        else:
            print("✅ Nenhum suspeito encontrado! O viés de Santiago parece resolvido.")
            
    except Exception as e:
        print(f"❌ Erro ao ler JSON: {e}")

if __name__ == "__main__":
    audit()