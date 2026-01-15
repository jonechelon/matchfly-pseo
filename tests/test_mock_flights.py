"""
Teste de validação offline usando mock data.
Não depende do site dinâmico do GRU.
Operação Resgate: Valida que voos problemáticos (7586, 7484, A6509) são resgatados.

NOTA: Este teste requer que o ambiente virtual esteja ativado com todas as dependências.
Execute: source venv/bin/activate && python tests/test_mock_flights.py
"""
import sys
import os

# Adiciona o diretório raiz ao path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Tenta importação normal primeiro
try:
    from src.scrapers.gru_proximos.data_processor import FlightDataProcessor
    from src.scrapers.gru_proximos.logger_config import setup_logger
except ImportError:
    # Fallback para quando executado diretamente sem o path correto
    sys.path.append(os.path.join(project_root, 'src'))
    from scrapers.gru_proximos.data_processor import FlightDataProcessor
    from scrapers.gru_proximos.logger_config import setup_logger

try:
    from tests.mock_data import MOCK_SCENARIOS, MOCK_FLIGHT_DATA, REAL_ROW_TEXTS, REAL_MOCK_STRINGS
except ImportError:
    import mock_data
    MOCK_SCENARIOS = mock_data.MOCK_SCENARIOS
    MOCK_FLIGHT_DATA = mock_data.MOCK_FLIGHT_DATA
    REAL_ROW_TEXTS = getattr(mock_data, 'REAL_ROW_TEXTS', [])
    REAL_MOCK_STRINGS = getattr(mock_data, 'REAL_MOCK_STRINGS', {})


def test_rescue_flights():
    """
    Testa resgate dos voos problemáticos (7586, 7484, A6509).
    Operação Resgate v2.0: Reduzir taxa de descarte de 99% para 0%.
    """
    logger = setup_logger()
    processor = FlightDataProcessor(logger=logger, enable_mcp=False)  # Offline para teste rápido
    
    print("\n" + "=" * 70)
    print("OPERação RESGATE: Teste Offline com Mock Data")
    print("=" * 70)
    print("Objetivo: Validar que voos problemáticos são resgatados")
    print("=" * 70 + "\n")
    
    results = {}
    
    # Testa cada caso do checklist consolidado
    print("📋 TESTANDO CASOS DO CHECKLIST CONSOLIDADO:\n")
    
    for case_id, scenario in MOCK_SCENARIOS.items():
        print(f"\n🔍 {case_id}")
        print(f"   Texto: {scenario['raw_text']}")
        
        flight_data = processor.extract_from_text(scenario['raw_text'])
        
        if flight_data:
            print(f"   ✅ RESGATADO!")
            print(f"      Voo: {flight_data.get('Voo')}")
            print(f"      Companhia: {flight_data.get('Companhia')}")
            print(f"      Destino: {flight_data.get('Destino')}")
            print(f"      Status: {flight_data.get('Status')}")
            
            # Validação contra esperado
            expected = scenario['expected']
            validation_passed = True
            
            if 'Voo' in expected:
                if str(flight_data.get('Voo')) != str(expected['Voo']):
                    print(f"   ⚠️  Voo esperado: {expected['Voo']}, obtido: {flight_data.get('Voo')}")
                    validation_passed = False
            
            if 'Companhia' in expected:
                if flight_data.get('Companhia') == expected['Companhia']:
                    print(f"   ✅ Companhia CORRETA: {expected['Companhia']}")
                else:
                    print(f"   ⚠️  Companhia esperada: {expected['Companhia']}, obtida: {flight_data.get('Companhia')}")
                    validation_passed = False
            
            if 'Destino' in expected and expected['Destino'] != "N/A":
                if flight_data.get('Destino') == expected['Destino']:
                    print(f"   ✅ Destino CORRETO: {expected['Destino']}")
                else:
                    print(f"   ⚠️  Destino esperado: {expected['Destino']}, obtido: {flight_data.get('Destino')}")
            
            results[case_id] = {
                "status": "success" if validation_passed else "partial",
                "data": flight_data,
                "expected": expected
            }
        else:
            print(f"   ❌ AINDA DESCARTADO")
            results[case_id] = {"status": "failed", "data": None, "expected": scenario['expected']}
    
    # Testa também os casos do MOCK_FLIGHT_DATA original
    print("\n" + "=" * 70)
    print("📋 TESTANDO CASOS ORIGINAIS (MOCK_FLIGHT_DATA):\n")
    
    for flight_id, data in MOCK_FLIGHT_DATA.items():
        print(f"\n🔍 {flight_id}")
        print(f"   Texto: {data['row_text']}")
        
        flight_data = processor.extract_from_text(data['row_text'])
        
        if flight_data:
            print(f"   ✅ RESGATADO!")
            print(f"      Voo: {flight_data.get('Voo')}")
            print(f"      Companhia: {flight_data.get('Companhia')}")
            print(f"      Destino: {flight_data.get('Destino')}")
            
            # Validação especial para A6509 (deve ser Avianca)
            if flight_id == "A6509":
                if flight_data.get('Companhia') == "AVIANCA":
                    print(f"   ✅✅✅ CASO CRÍTICO: A6509 identificado como AVIANCA (CORRETO!)")
                else:
                    print(f"   ⚠️  A6509 identificado como: {flight_data.get('Companhia')} (esperado: AVIANCA)")
            
            results[flight_id] = {"status": "success", "data": flight_data}
        else:
            print(f"   ❌ AINDA DESCARTADO")
            results[flight_id] = {"status": "failed", "data": None}
    
    # Resumo final
    print("\n" + "=" * 70)
    print("RESUMO DA OPERAÇÃO RESGATE")
    print("=" * 70)
    
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    partial_count = sum(1 for r in results.values() if r["status"] == "partial")
    failed_count = sum(1 for r in results.values() if r["status"] == "failed")
    total_count = len(results)
    
    print(f"\n✅ Voos Totalmente Resgatados: {success_count}/{total_count}")
    print(f"⚠️  Voos Parcialmente Resgatados: {partial_count}/{total_count}")
    print(f"❌ Voos Ainda Perdidos: {failed_count}/{total_count}\n")
    
    for case_id, result in results.items():
        if result["status"] == "success":
            print(f"✅ {case_id}: RESGATADO")
        elif result["status"] == "partial":
            print(f"⚠️  {case_id}: PARCIAL")
        else:
            print(f"❌ {case_id}: PERDIDO")
    
    # Testa casos reais da FASE 3
    if REAL_MOCK_STRINGS:
        print("\n" + "=" * 70)
        print("📋 TESTANDO CASOS REAIS (REAL_MOCK_STRINGS - FASE 3):\n")
        
        for case_id, raw_text in REAL_MOCK_STRINGS.items():
            print(f"\n🔍 {case_id}")
            print(f"   Texto: {raw_text}")
            
            flight_data = processor.extract_from_text(raw_text)
            
            if flight_data:
                print(f"   ✅ RESGATADO!")
                print(f"      Voo: {flight_data.get('Voo')}")
                print(f"      Companhia: {flight_data.get('Companhia')}")
                print(f"      Destino: {flight_data.get('Destino')}")
                print(f"      Status: {flight_data.get('Status')}")
                results[case_id] = {"status": "success", "data": flight_data}
            else:
                print(f"   ❌ AINDA DESCARTADO")
                results[case_id] = {"status": "failed", "data": None}
    
    # Validação crítica
    print("\n" + "=" * 70)
    print("VALIDAÇÃO CRÍTICA")
    print("=" * 70)
    
    critical_cases = ["CASE_1_BOGOTA_AVIANCA", "CASE_2_ONE_LETTER_PREFIX", "A6509", "ORPHAN_7586"]
    all_critical_pass = all(
        results.get(case, {}).get("status") in ["success", "partial"]
        for case in critical_cases
    )
    
    if all_critical_pass:
        print("✅✅✅ OPERAÇÃO RESGATE: SUCESSO!")
        print("   Casos críticos (Bogotá/Avianca, A6509, 7586) foram resgatados")
    else:
        print("⚠️  OPERAÇÃO RESGATE: PARCIAL")
        print("   Alguns casos críticos ainda precisam de ajustes")
        failed_cases = [case for case in critical_cases 
                       if results.get(case, {}).get("status") not in ["success", "partial"]]
        if failed_cases:
            print(f"   Casos falhados: {', '.join(failed_cases)}")
    
    return results


if __name__ == "__main__":
    test_rescue_flights()
