#!/usr/bin/env python3
"""
Exemplo de uso do Historical Importer
Demonstra como customizar a importação para diferentes cenários
"""

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from historical_importer import ANACHistoricalImporter


def example_basic():
    """Exemplo 1: Importação básica (padrão)."""
    print("\n" + "="*70)
    print("EXEMPLO 1: Importação Básica")
    print("="*70)
    
    importer = ANACHistoricalImporter(
        output_file="data/flights-db.json",
        airport_code="SBGR",        # Guarulhos
        min_delay_minutes=15,       # Atrasos > 15min
        days_lookback=30            # Últimos 30 dias
    )
    
    print("\nConfiguração:")
    print(f"  • Aeroporto: {importer.airport_code}")
    print(f"  • Atraso mínimo: {importer.min_delay_minutes} minutos")
    print(f"  • Período: últimos {importer.days_lookback} dias")
    print(f"  • Output: {importer.output_file}")
    
    # Para executar de verdade, descomente:
    # importer.run()


def example_other_airport():
    """Exemplo 2: Importar dados de outro aeroporto."""
    print("\n" + "="*70)
    print("EXEMPLO 2: Outro Aeroporto (Congonhas)")
    print("="*70)
    
    importer = ANACHistoricalImporter(
        output_file="data/flights-cgr.json",  # Arquivo separado
        airport_code="SBSP",                   # Congonhas (São Paulo)
        min_delay_minutes=15,
        days_lookback=30
    )
    
    print("\nConfiguração:")
    print(f"  • Aeroporto: {importer.airport_code} (Congonhas)")
    print(f"  • Output: {importer.output_file}")
    
    # Para executar de verdade, descomente:
    # importer.run()


def example_longer_period():
    """Exemplo 3: Período mais longo (60 dias)."""
    print("\n" + "="*70)
    print("EXEMPLO 3: Período Mais Longo (60 dias)")
    print("="*70)
    
    importer = ANACHistoricalImporter(
        output_file="data/flights-db.json",
        airport_code="SBGR",
        min_delay_minutes=15,
        days_lookback=60               # Últimos 60 dias
    )
    
    print("\nConfiguração:")
    print(f"  • Período: últimos {importer.days_lookback} dias")
    print("  • Nota: Pode levar mais tempo (mais arquivos para baixar)")
    
    # Para executar de verdade, descomente:
    # importer.run()


def example_only_major_delays():
    """Exemplo 4: Apenas grandes atrasos (> 1 hora)."""
    print("\n" + "="*70)
    print("EXEMPLO 4: Apenas Grandes Atrasos (> 1h)")
    print("="*70)
    
    importer = ANACHistoricalImporter(
        output_file="data/flights-major-delays.json",
        airport_code="SBGR",
        min_delay_minutes=60,          # Apenas atrasos > 1 hora
        days_lookback=30
    )
    
    print("\nConfiguração:")
    print(f"  • Atraso mínimo: {importer.min_delay_minutes} minutos (1 hora)")
    print("  • Resultado: Menos voos, mas atrasos mais graves")
    
    # Para executar de verdade, descomente:
    # importer.run()


def example_multiple_airports():
    """Exemplo 5: Importar de múltiplos aeroportos."""
    print("\n" + "="*70)
    print("EXEMPLO 5: Múltiplos Aeroportos")
    print("="*70)
    
    airports = [
        ("SBGR", "Guarulhos (SP)"),
        ("SBSP", "Congonhas (SP)"),
        ("SBGL", "Galeão (RJ)"),
        ("SBBR", "Brasília"),
    ]
    
    print("\nImportando de múltiplos aeroportos...")
    
    for code, name in airports:
        print(f"\n  → {name} ({code})")
        
        importer = ANACHistoricalImporter(
            output_file=f"data/flights-{code.lower()}.json",
            airport_code=code,
            min_delay_minutes=15,
            days_lookback=30
        )
        
        print(f"    Output: {importer.output_file}")
        
        # Para executar de verdade, descomente:
        # importer.run()


def example_custom_date_range():
    """Exemplo 6: Range de datas específico (última semana)."""
    print("\n" + "="*70)
    print("EXEMPLO 6: Última Semana Apenas")
    print("="*70)
    
    importer = ANACHistoricalImporter(
        output_file="data/flights-weekly.json",
        airport_code="SBGR",
        min_delay_minutes=15,
        days_lookback=7                # Última semana
    )
    
    print("\nConfiguração:")
    print(f"  • Período: últimos {importer.days_lookback} dias (1 semana)")
    print("  • Uso: Atualizações rápidas/testes")
    
    # Para executar de verdade, descomente:
    # importer.run()


def demo_airline_mapping():
    """Demo: Mostrar mapeamento de companhias aéreas."""
    print("\n" + "="*70)
    print("DEMO: Mapeamento de Companhias Aéreas")
    print("="*70)
    
    from historical_importer import AIRLINE_MAPPING
    
    print("\nCompanhias Brasileiras:")
    brazilian = {k: v for k, v in AIRLINE_MAPPING.items() if k in ['G3', 'AD', 'LA', '2Z']}
    for code, name in brazilian.items():
        print(f"  {code} → {name}")
    
    print("\nCompanhias Europeias:")
    european = {k: v for k, v in AIRLINE_MAPPING.items() if k in ['AF', 'KL', 'LH', 'BA', 'TP']}
    for code, name in european.items():
        print(f"  {code} → {name}")
    
    print("\nCompanhias Americanas:")
    american = {k: v for k, v in AIRLINE_MAPPING.items() if k in ['AA', 'DL', 'UA', 'CM']}
    for code, name in american.items():
        print(f"  {code} → {name}")
    
    print(f"\nTotal de companhias mapeadas: {len(AIRLINE_MAPPING)}")


def main():
    """Executa todos os exemplos."""
    print("\n╔" + "═"*68 + "╗")
    print("║" + " "*15 + "📚 EXEMPLOS DE USO - HISTORICAL IMPORTER" + " "*14 + "║")
    print("╚" + "═"*68 + "╝")
    
    # Executar exemplos (demonstração apenas, não executa de verdade)
    example_basic()
    example_other_airport()
    example_longer_period()
    example_only_major_delays()
    example_multiple_airports()
    example_custom_date_range()
    demo_airline_mapping()
    
    print("\n" + "="*70)
    print("📝 NOTA:")
    print("="*70)
    print("Estes são apenas exemplos de configuração.")
    print("Para executar de verdade, descomente as linhas 'importer.run()'")
    print("\nOu use o script direto:")
    print("  python src/historical_importer.py")
    print("  python run_historical_import.py")
    print("\n")


if __name__ == "__main__":
    main()
