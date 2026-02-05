#!/usr/bin/env python3
"""
Script de demonstração do mapeamento IATA expandido
Valida a busca case-insensitive e strip()
"""

from src.generator import get_iata_code, is_domestic_flight

def test_iata_mapping():
    """Testa o mapeamento IATA com diferentes formatos."""
    
    print("=" * 80)
    print("🎯 TESTE DE MAPEAMENTO IATA - MatchFly")
    print("=" * 80)
    print()
    
    # Casos de teste
    test_cases = [
        # Formato: (entrada, código_esperado, descrição)
        ("Paris", "CDG", "Internacional - Europa (capitalizado)"),
        ("PARIS", "CDG", "Internacional - Europa (maiúsculo)"),
        ("paris", "CDG", "Internacional - Europa (minúsculo)"),
        ("  Paris  ", "CDG", "Internacional - Europa (com espaços)"),
        
        ("Lisboa", "LIS", "Internacional - Europa"),
        ("MADRID", "MAD", "Internacional - Europa (maiúsculo)"),
        ("Buenos Aires", "EZE", "Internacional - América do Sul"),
        ("NOVA YORK", "JFK", "Internacional - América do Norte (maiúsculo)"),
        ("miami", "MIA", "Internacional - América do Norte (minúsculo)"),
        ("Orlando", "MCO", "Internacional - América do Norte"),
        ("  Panamá  ", "PTY", "Internacional - América Central (com espaços)"),
        
        ("Rio de Janeiro", "GIG", "Nacional - Sudeste"),
        ("BRASÍLIA", "BSB", "Nacional - Centro-Oeste (maiúsculo)"),
        ("fortaleza", "FOR", "Nacional - Nordeste (minúsculo)"),
        ("Porto Alegre", "POA", "Nacional - Sul"),
        ("CURITIBA", "CWB", "Nacional - Sul (maiúsculo)"),
        ("Florianópolis", "FLN", "Nacional - Sul (com acento)"),
        ("  Goiânia  ", "GYN", "Nacional - Centro-Oeste (com espaços e acento)"),
        ("Foz do Iguaçu", "IGU", "Nacional - Sul (nome composto)"),
        ("FOZ DO IGUAÇU", "IGU", "Nacional - Sul (maiúsculo, nome composto)"),
        ("Porto Seguro", "BPS", "Nacional - Nordeste (nome composto)"),
        
        ("Amsterdã", "AMS", "Internacional - Europa (com acento)"),
        ("AMSTERDÃ", "AMS", "Internacional - Europa (maiúsculo com acento)"),
        
        ("Cidade Inexistente", "", "Fallback - cidade não mapeada"),
        ("", "", "Fallback - string vazia"),
        ("   ", "", "Fallback - apenas espaços"),
    ]
    
    print("📋 TESTANDO MAPEAMENTOS:")
    print("-" * 80)
    
    success_count = 0
    total_count = len(test_cases)
    
    for cidade, codigo_esperado, descricao in test_cases:
        codigo_obtido = get_iata_code(cidade)
        status = "✅" if codigo_obtido == codigo_esperado else "❌"
        
        # Formatação da entrada para exibição
        entrada_display = f'"{cidade}"' if cidade else '(vazio)'
        
        print(f"{status} {entrada_display:<25} → {codigo_obtido or '(vazio)':<5} | {descricao}")
        
        if codigo_obtido == codigo_esperado:
            success_count += 1
        else:
            print(f"   ⚠️  Esperado: {codigo_esperado}, Obtido: {codigo_obtido}")
    
    print("-" * 80)
    print()
    
    # Testa detecção de voos domésticos
    print("🛫 TESTANDO DETECÇÃO DE VOOS DOMÉSTICOS vs INTERNACIONAIS:")
    print("-" * 80)
    
    domestic_tests = [
        ("GIG", True, "Rio de Janeiro - Doméstico"),
        ("BSB", True, "Brasília - Doméstico"),
        ("GRU", True, "São Paulo/Guarulhos - Doméstico"),
        ("CDG", False, "Paris - Internacional"),
        ("EZE", False, "Buenos Aires - Internacional"),
        ("MIA", False, "Miami - Internacional"),
    ]
    
    domestic_success = 0
    for iata, is_domestic, descricao in domestic_tests:
        resultado = is_domestic_flight(iata)
        status = "✅" if resultado == is_domestic else "❌"
        tipo = "DOMÉSTICO" if resultado else "INTERNACIONAL"
        
        print(f"{status} {iata:<5} → {tipo:<15} | {descricao}")
        
        if resultado == is_domestic:
            domestic_success += 1
    
    print("-" * 80)
    print()
    
    # Sumário final
    print("=" * 80)
    print("📊 SUMÁRIO DOS TESTES:")
    print("=" * 80)
    print(f"Mapeamento IATA:           {success_count}/{total_count} testes passaram")
    print(f"Detecção Doméstico/Inter:  {domestic_success}/{len(domestic_tests)} testes passaram")
    print()
    
    if success_count == total_count and domestic_success == len(domestic_tests):
        print("🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
        print("✅ MatchFly: Dicionário IATA expandido com sucesso!")
        return True
    else:
        print("⚠️  ALGUNS TESTES FALHARAM - Verifique as mensagens acima")
        return False

if __name__ == "__main__":
    success = test_iata_mapping()
    exit(0 if success else 1)
