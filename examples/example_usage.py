#!/usr/bin/env python3
"""
Exemplos de uso do GRU Flight Scraper.

Este arquivo demonstra diferentes formas de usar o scraper.
"""

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scrapers.gru_flights_scraper import GRUFlightScraper
import logging


def exemplo_basico():
    """Exemplo 1: Uso básico do scraper."""
    print("\n" + "="*60)
    print("EXEMPLO 1: Uso Básico")
    print("="*60 + "\n")
    
    scraper = GRUFlightScraper(output_file="data/flights-db.json")
    scraper.run()


def exemplo_customizado():
    """Exemplo 2: Filtros customizados."""
    print("\n" + "="*60)
    print("EXEMPLO 2: Filtros Customizados")
    print("="*60 + "\n")
    
    scraper = GRUFlightScraper(output_file="data/flights-custom.json")
    
    # Busca todos os voos
    all_flights = scraper.fetch_flights()
    
    # Filtro customizado: apenas atrasos > 3 horas
    custom_filtered = [
        f for f in all_flights 
        if f.get('delay_hours', 0) > 3
    ]
    
    print(f"✅ Voos com atraso > 3h: {len(custom_filtered)}")
    
    # Salva resultados customizados
    scraper.save_to_json(custom_filtered)


def exemplo_analise():
    """Exemplo 3: Análise de dados."""
    print("\n" + "="*60)
    print("EXEMPLO 3: Análise de Dados")
    print("="*60 + "\n")
    
    scraper = GRUFlightScraper()
    flights = scraper.fetch_flights()
    filtered = scraper.filter_flights(flights)
    
    # Estatísticas
    if filtered:
        # Conta por status
        status_count = {}
        for flight in filtered:
            status = flight['status']
            status_count[status] = status_count.get(status, 0) + 1
        
        print("\n📊 Estatísticas:")
        print(f"   Total de voos problemáticos: {len(filtered)}")
        for status, count in status_count.items():
            print(f"   - {status}: {count}")
        
        # Conta por companhia
        airline_count = {}
        for flight in filtered:
            airline = flight['airline']
            airline_count[airline] = airline_count.get(airline, 0) + 1
        
        print("\n✈️  Por Companhia Aérea:")
        for airline, count in sorted(airline_count.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {airline}: {count} voos")
        
        # Atraso médio
        delays = [f['delay_hours'] for f in filtered if f['delay_hours'] > 0]
        if delays:
            avg_delay = sum(delays) / len(delays)
            print(f"\n⏱️  Atraso médio: {avg_delay:.2f} horas")
            print(f"   Maior atraso: {max(delays):.2f} horas")
            print(f"   Menor atraso: {min(delays):.2f} horas")


def exemplo_por_companhia():
    """Exemplo 4: Filtrar por companhia específica."""
    print("\n" + "="*60)
    print("EXEMPLO 4: Filtrar por Companhia")
    print("="*60 + "\n")
    
    scraper = GRUFlightScraper()
    all_flights = scraper.fetch_flights()
    
    # Filtrar apenas LATAM
    latam_flights = [
        f for f in all_flights 
        if 'LATAM' in f.get('airline', '')
    ]
    
    print(f"✅ Voos LATAM: {len(latam_flights)}")
    
    # Filtrar LATAM com problemas
    latam_filtered = scraper.filter_flights(latam_flights)
    print(f"⚠️  Voos LATAM com problemas: {len(latam_filtered)}")
    
    # Salva em arquivo separado
    if latam_filtered:
        scraper.output_file = Path("data/flights-latam.json")
        scraper.save_to_json(latam_filtered)


def exemplo_logging_debug():
    """Exemplo 5: Ativar modo DEBUG."""
    print("\n" + "="*60)
    print("EXEMPLO 5: Modo DEBUG")
    print("="*60 + "\n")
    
    # Ativa modo DEBUG
    logger = logging.getLogger('scrapers.gru_flights_scraper')
    logger.setLevel(logging.DEBUG)
    
    scraper = GRUFlightScraper(output_file="data/flights-debug.json")
    scraper.run()


def menu():
    """Menu interativo de exemplos."""
    exemplos = {
        '1': ('Uso Básico', exemplo_basico),
        '2': ('Filtros Customizados', exemplo_customizado),
        '3': ('Análise de Dados', exemplo_analise),
        '4': ('Filtrar por Companhia', exemplo_por_companhia),
        '5': ('Modo DEBUG', exemplo_logging_debug),
    }
    
    print("\n" + "="*60)
    print("   GRU FLIGHT SCRAPER - EXEMPLOS DE USO")
    print("="*60)
    print("\nEscolha um exemplo para executar:\n")
    
    for key, (desc, _) in exemplos.items():
        print(f"  {key}. {desc}")
    
    print(f"  0. Executar todos")
    print(f"  Q. Sair")
    
    print("\n" + "="*60)
    
    choice = input("\nSua escolha: ").strip().upper()
    
    if choice == 'Q':
        print("\n👋 Até logo!\n")
        return
    elif choice == '0':
        print("\n🚀 Executando todos os exemplos...\n")
        for _, (_, func) in exemplos.items():
            try:
                func()
            except Exception as e:
                print(f"❌ Erro: {e}")
            print("\n" + "-"*60)
    elif choice in exemplos:
        _, func = exemplos[choice]
        try:
            func()
        except Exception as e:
            print(f"❌ Erro: {e}")
    else:
        print("\n❌ Opção inválida!\n")


if __name__ == "__main__":
    # Se executado diretamente, mostra menu
    if len(sys.argv) == 1:
        menu()
    else:
        # Permite executar exemplo específico via CLI
        exemplo = sys.argv[1]
        
        exemplos_map = {
            'basico': exemplo_basico,
            'custom': exemplo_customizado,
            'analise': exemplo_analise,
            'companhia': exemplo_por_companhia,
            'debug': exemplo_logging_debug,
        }
        
        if exemplo in exemplos_map:
            exemplos_map[exemplo]()
        else:
            print(f"❌ Exemplo '{exemplo}' não encontrado!")
            print(f"Exemplos disponíveis: {', '.join(exemplos_map.keys())}")

