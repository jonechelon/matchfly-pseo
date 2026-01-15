"""
Testes para o módulo MCP Diagnostics.
Valida extração de voos problemáticos.
"""
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scrapers.gru_proximos.data_processor import FlightDataProcessor
from src.scrapers.gru_proximos.logger_config import setup_logger
from tests.mock_data import MOCK_FLIGHT_DATA, REAL_ROW_TEXTS


def test_problematic_flights():
    """Testa extração dos voos problemáticos identificados."""
    logger = setup_logger()
    processor = FlightDataProcessor(logger=logger, enable_mcp=False)  # Desabilita MCP para teste rápido
    
    print("\n" + "=" * 70)
    print("TESTE: Voos Problemáticos (7586, 7484, A6509)")
    print("=" * 70 + "\n")
    
    results = {}
    
    for flight_id, data in MOCK_FLIGHT_DATA.items():
        print(f"\n📋 Testando: {flight_id}")
        print(f"   Texto: {data['row_text']}")
        
        flight_data = processor.extract_from_text(data['row_text'])
        
        if flight_data:
            print(f"   ✅ Extraído com sucesso!")
            print(f"      Voo: {flight_data.get('Voo')}")
            print(f"      Companhia: {flight_data.get('Companhia')}")
            print(f"      Destino: {flight_data.get('Destino')}")
            print(f"      Status: {flight_data.get('Status')}")
            results[flight_id] = {"status": "success", "data": flight_data}
        else:
            print(f"   ❌ Falha na extração")
            results[flight_id] = {"status": "failed", "data": None}
    
    print("\n" + "=" * 70)
    print("RESUMO DOS TESTES")
    print("=" * 70)
    
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    total_count = len(results)
    
    print(f"\n✅ Sucessos: {success_count}/{total_count}")
    print(f"❌ Falhas: {total_count - success_count}/{total_count}\n")
    
    for flight_id, result in results.items():
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"{status_icon} {flight_id}: {result['status']}")
    
    return results


if __name__ == "__main__":
    test_problematic_flights()
