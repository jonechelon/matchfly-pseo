# 📖 Guia do Dicionário IATA - MatchFly

## 🎯 Objetivo

O dicionário `CITY_TO_IATA` mapeia nomes de cidades para códigos IATA de aeroportos, permitindo que o link do funil da AirHelp seja pré-preenchido automaticamente, aumentando a taxa de conversão.

## 📍 Localização

**Arquivo:** `src/generator.py`  
**Linhas:** 45-74 (dicionário) e 118-143 (função de busca)

## 🔧 Como Funciona

### 1. Busca Case-Insensitive

A função `get_iata_code()` normaliza a entrada antes de buscar:

```python
# Todas essas entradas retornam "CDG":
get_iata_code("Paris")      # → "CDG"
get_iata_code("PARIS")      # → "CDG"
get_iata_code("paris")      # → "CDG"
get_iata_code("  Paris  ")  # → "CDG"
```

### 2. Formato do Dicionário

```python
CITY_TO_IATA = {
    # Todas as chaves devem estar em LOWERCASE
    "paris": "CDG",           # ✅ Correto
    "rio de janeiro": "GIG",  # ✅ Correto
    "foz do iguaçu": "IGU",   # ✅ Aceita acentos
    
    # ❌ NÃO use maiúsculas nas chaves:
    # "PARIS": "CDG",         # Errado
    # "Paris": "CDG",         # Errado
}
```

### 3. Fallback Automático

Se a cidade não estiver no dicionário:
- O código IATA fica vazio no link
- `departureAirportIata=GRU` sempre presente
- Usuário pode preencher manualmente no funil

## ➕ Como Adicionar Novos Destinos

### Passo 1: Identificar Cidade e Código IATA

Consulte os logs do generator para ver cidades não mapeadas:

```bash
grep "Cidade não mapeada" generator.log
```

Pesquise o código IATA em:
- [IATA Airport Codes](https://www.iata.org/en/publications/directories/code-search/)
- [Wikipedia - List of IATA codes](https://en.wikipedia.org/wiki/List_of_IATA_airport_codes)

### Passo 2: Adicionar ao Dicionário

Edite `src/generator.py` e adicione a nova entrada:

```python
CITY_TO_IATA = {
    # ... entradas existentes ...
    
    # Nova entrada (sempre lowercase!)
    "nova cidade": "ABC",
    "new city": "ABC",  # Adicione variações se necessário
}
```

### Passo 3: Atualizar Lista de Aeroportos Brasileiros (se aplicável)

Se for um aeroporto brasileiro, adicione também em `BRAZILIAN_AIRPORTS`:

```python
BRAZILIAN_AIRPORTS = {
    "GRU", "GIG", "BSB", "SSA", # ... existentes ...
    "ABC",  # Novo aeroporto brasileiro
}
```

### Passo 4: Testar

```bash
# Teste manual
python test_iata_mapping.py

# Teste unitário
python -m unittest tests.test_generator -v

# Teste completo
python src/generator.py
```

## 📋 Checklist de Manutenção

Ao adicionar novos destinos:

- [ ] Chave do dicionário em **lowercase**
- [ ] Código IATA em **UPPERCASE** (padrão IATA)
- [ ] Adicionar variações comuns (com/sem acento, português/inglês)
- [ ] Se brasileiro, adicionar em `BRAZILIAN_AIRPORTS`
- [ ] Executar `test_iata_mapping.py` para validar
- [ ] Verificar logs do generator após deploy

## 🌍 Destinos Atualmente Cobertos

### Internacionais (20+)
- **Europa:** Paris, Lisboa, Madrid, Londres, Frankfurt, Roma, Barcelona, Amsterdã, Zurique, Milão
- **América do Sul:** Buenos Aires, Santiago, Lima, Bogotá, Montevidéu
- **América do Norte:** Miami, Nova York, Orlando, Los Angeles, Toronto, Cidade do México, Panamá

### Nacionais (20+)
- **Sudeste:** Rio de Janeiro, Belo Horizonte, Vitória
- **Sul:** Porto Alegre, Curitiba, Florianópolis, Foz do Iguaçu
- **Nordeste:** Salvador, Fortaleza, Recife, Natal, Maceió, Aracaju, Porto Seguro
- **Norte:** Manaus, Belém
- **Centro-Oeste:** Brasília, Goiânia, Cuiabá, Campo Grande

## 🔍 Monitoramento

### Ver cidades não mapeadas nos logs:

```bash
grep "Cidade não mapeada" generator.log | sort | uniq -c | sort -rn
```

### Ver estatísticas de mapeamento:

```bash
python test_iata_mapping.py
```

### Verificar links gerados:

```bash
# Ver todos os links de afiliado gerados
grep -r "arrivalAirportIata=" public/voo/*.html | grep -o "arrivalAirportIata=[A-Z]*" | sort | uniq -c
```

## 🐛 Troubleshooting

### Problema: Cidade não está sendo mapeada

**Solução:**
1. Verifique se a chave está em lowercase no dicionário
2. Verifique se há acentos ou caracteres especiais
3. Teste com `get_iata_code("nome da cidade")` diretamente

### Problema: Link sem código IATA de destino

**Causa:** Cidade não mapeada (comportamento esperado - fallback)

**Solução:** Adicione a cidade ao dicionário seguindo o guia acima

### Problema: Código IATA errado

**Solução:**
1. Verifique se o código IATA está correto em [IATA.org](https://www.iata.org/)
2. Corrija no dicionário
3. Execute `python src/generator.py` novamente

## 📊 Métricas de Sucesso

Monitore estas métricas para avaliar o impacto:

1. **Taxa de mapeamento:** Quantos % dos voos têm código IATA mapeado
2. **CTR do link AirHelp:** Taxa de cliques no botão CTA
3. **Conversão no funil:** % de usuários que completam o formulário
4. **Comissões AirHelp:** Aumento nas comissões recebidas

## 📚 Referências

- [IATA Airport Codes](https://www.iata.org/en/publications/directories/code-search/)
- [AirHelp API Documentation](https://funnel.airhelp.com/claims/new/trip-details)
- [MatchFly Generator Architecture](GENERATOR_V2_ARCHITECTURE.md)

## 🆘 Suporte

Se encontrar problemas ou tiver dúvidas:
1. Verifique os logs: `generator.log`
2. Execute os testes: `python test_iata_mapping.py`
3. Consulte este guia
4. Revise o código em `src/generator.py` (bem documentado)

---

**Última atualização:** 2026-01-12  
**Versão do Generator:** 2.0.0
