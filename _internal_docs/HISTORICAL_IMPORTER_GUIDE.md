# 📚 MatchFly Historical Importer - Guia de Uso

## 🎯 Visão Geral

O **Historical Importer** é um script de engenharia de dados que baixa e importa dados históricos oficiais da ANAC (Agência Nacional de Aviação Civil) para popular o banco de dados do MatchFly com voos atrasados dos últimos 30 dias.

### Fonte de Dados

- **Origem**: Portal Brasileiro de Dados Abertos da ANAC
- **Dataset**: VRA (Voo Regular Ativo)
- **URL Base**: https://www.gov.br/anac/pt-br/assuntos/dados-abertos/arquivos/vra/
- **Formato**: CSV mensal com todos os voos operados no Brasil

## 🚀 Como Usar

### 1. Instalação de Dependências

```bash
# Certifique-se de que o pandas está instalado
pip install -r requirements.txt
```

### 2. Execução Básica

```bash
# Importa dados dos últimos 30 dias de voos atrasados em Guarulhos
python src/historical_importer.py
```

### 3. Gerar Páginas Após Importação

```bash
# Após importar, gere as páginas HTML
python src/generator.py
```

## ⚙️ Configuração

### Parâmetros Principais (editáveis em `main()`)

```python
importer = ANACHistoricalImporter(
    output_file="data/flights-db.json",  # Arquivo de saída
    airport_code="SBGR",                 # Código ICAO do aeroporto
    min_delay_minutes=15,                # Atraso mínimo para considerar
    days_lookback=30                     # Quantos dias no passado buscar
)
```

### Customizações

#### Mudar Aeroporto

Para importar dados de outro aeroporto, altere o `airport_code`:

```python
airport_code="SBSP"  # Congonhas (São Paulo)
airport_code="SBBR"  # Brasília
airport_code="SBGL"  # Galeão (Rio de Janeiro)
```

#### Ajustar Período

Para importar mais ou menos dias:

```python
days_lookback=60  # Últimos 60 dias
days_lookback=7   # Última semana
```

#### Ajustar Filtro de Atraso

Para mudar o critério de atraso mínimo:

```python
min_delay_minutes=30  # Apenas atrasos > 30 minutos
min_delay_minutes=60  # Apenas atrasos > 1 hora
```

## 📊 Funcionamento

### Workflow do Importer

```
┌─────────────────────────────────────────────────┐
│ STEP 1: Carrega banco de dados existente       │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ STEP 2: Identifica arquivos ANAC disponíveis   │
│  • Calcula meses a buscar (mês atual + anterior)│
│  • Gera URLs de download                        │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ STEP 3: Download e Processamento               │
│  ├─ Download de CSVs mensais da ANAC           │
│  ├─ Parse com pandas (encoding automático)     │
│  ├─ Identificação inteligente de colunas       │
│  ├─ Filtro 1: Aeroporto de origem = SBGR       │
│  ├─ Cálculo de atrasos                         │
│  ├─ Filtro 2: Atraso > 15 minutos              │
│  ├─ Filtro 3: Últimos 30 dias                  │
│  └─ Mapeamento para formato MatchFly           │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ STEP 4: Mesclagem com banco existente          │
│  • Evita duplicatas por ID único                │
│  • Adiciona apenas voos novos                   │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ STEP 5: Limpeza de arquivos temporários        │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ STEP 6: Sumário + Som de Sucesso 🔔            │
└─────────────────────────────────────────────────┘
```

### Mapeamento de Dados

O script converte automaticamente os campos da ANAC para o formato MatchFly:

| Campo ANAC                    | Campo MatchFly      | Transformação                          |
|-------------------------------|---------------------|----------------------------------------|
| `Sigla Empresa ICAO`          | `airline`           | Mapeia via dicionário (G3→GOL, etc.)   |
| `Numero Voo`                  | `flight_number`     | Remove prefixos, zeros à esquerda      |
| `Aeroporto Origem (ICAO)`     | `origin`            | SBGR → GRU                             |
| `Cidade Destino`              | `destination`       | Usa dicionário CITY_TO_IATA            |
| `Data/Hora Prevista`          | `scheduled_time`    | Parse para HH:MM                       |
| `Data/Hora Real`              | `actual_time`       | Parse para HH:MM                       |
| Diferença calculada           | `delay_min`         | (Real - Previsto) em minutos           |
| Diferença calculada           | `delay_hours`       | (Real - Previsto) em horas (decimal)   |
| Baseado no atraso             | `status`            | "Atrasado" ou "Cancelado"              |

## 🗺️ Mapeamento de Companhias Aéreas

O script inclui dicionário completo de companhias:

### Brasileiras
- **G3** → GOL
- **AD** → AZUL  
- **LA/JJ** → LATAM
- **2Z** → Voepass

### Internacionais (Europa)
- **AF** → Air France
- **KL** → KLM
- **LH** → Lufthansa
- **BA** → British Airways
- **TP** → TAP Portugal
- E mais...

### Internacionais (Américas)
- **AR** → Aerolíneas Argentinas
- **AA** → American Airlines
- **DL** → Delta
- **UA** → United Airlines
- **CM** → Copa Airlines
- E mais...

## 📋 Logs e Rastreamento

### Arquivo de Log

Todas as operações são registradas em:

```
historical_importer.log
```

### Exemplo de Log de Sucesso

```
2026-01-12 10:30:15 - INFO - 🔍 Identificando arquivos ANAC disponíveis...
2026-01-12 10:30:15 - INFO - 📅 Períodos a buscar: 202601, 202512
2026-01-12 10:30:16 - INFO - 📥 Baixando: https://...VRA_202601.csv
2026-01-12 10:30:45 - INFO - ✅ Download concluído: VRA_202601.csv (45.32 MB)
2026-01-12 10:31:00 - INFO - 📊 Processando: VRA_202601.csv
2026-01-12 10:31:02 - INFO -    📈 Total de linhas: 123,456
2026-01-12 10:31:03 - INFO -    🛫 Voos de SBGR: 8,234
2026-01-12 10:31:15 - INFO -    ✅ Voos atrasados (>15min): 1,456
2026-01-12 10:31:20 - INFO - ✅ Banco de dados atualizado: 1,456 novos voos adicionados
2026-01-12 10:31:20 - INFO -    Total no banco: 1,458 voos
2026-01-12 10:31:20 - INFO - 🔔 Som de sucesso tocado!
```

## 🎨 Recursos Avançados

### 1. Identificação Inteligente de Colunas

O script usa **padrões flexíveis** para identificar colunas, mesmo que a ANAC mude os nomes:

```python
# Busca por múltiplos padrões
'airline_code': ['sigla', 'empresa', 'companhia', 'icao_empresa']
'flight_number': ['numero_voo', 'voo', 'flight']
# ... etc
```

### 2. Detecção Automática de Encoding

Tenta múltiplos encodings automaticamente:

```python
for encoding in ['latin-1', 'utf-8', 'iso-8859-1']:
    try:
        df = pd.read_csv(csv_path, encoding=encoding)
        break
    except UnicodeDecodeError:
        continue
```

### 3. Prevenção de Duplicatas

Cada voo recebe um ID único baseado em:

```
ID = airline + flight_number + scheduled_date
```

Exemplo: `gol-1234-2025-12-15`

### 4. Integração com Dicionário CITY_TO_IATA

Reutiliza o dicionário do `generator.py` para mapear cidades:

```python
from generator import get_iata_code, CITY_TO_IATA

destination_iata = get_iata_code("Paris")  # → "CDG"
```

## 📊 Estatísticas Geradas

Ao final, o script exibe:

```
📊 SUMÁRIO DA IMPORTAÇÃO:
   • Arquivos baixados:        2
   • Total de linhas lidas:    234,567
   • Voos de SBGR:             15,432
   • Voos com atraso >15min:   2,345
   • Voos importados (novos):  2,345
   • Duplicatas ignoradas:     0
   • Erros:                    12
```

## ⚠️ Troubleshooting

### Erro: "pandas não encontrado"

**Solução**: O script instala automaticamente. Se falhar:

```bash
pip install pandas
```

### Erro: "Arquivo não encontrado (HTTP 404)"

**Causa**: A ANAC ainda não publicou os dados do mês atual.

**Solução**: Normal para os primeiros dias do mês. O script continuará com o mês anterior.

### Erro: "Não foi possível identificar colunas necessárias"

**Causa**: A ANAC mudou drasticamente a estrutura do CSV.

**Solução**: Abra o CSV manualmente e atualize os padrões em `_identify_columns()`.

### Nenhum voo importado (0 novos)

**Causas possíveis**:
1. Todos os voos já existem no banco (duplicatas)
2. Não houve voos atrasados no período
3. Filtro muito restritivo (ex: `min_delay_minutes` muito alto)

**Solução**: Verifique os logs para detalhes.

## 🔧 Customização Avançada

### Adicionar Nova Companhia Aérea

Edite o dicionário `AIRLINE_MAPPING`:

```python
AIRLINE_MAPPING = {
    # ...
    "XY": "Nova Companhia",  # Adicione aqui
}
```

### Mudar Formato de Data

Edite `parse_datetime()` para aceitar novos formatos:

```python
for date_format in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
    # Adicione novo formato aqui
```

### Adicionar Campos Customizados

No método `_process_row()`, adicione novos campos:

```python
flight = {
    # ... campos existentes ...
    'custom_field': row.get('coluna_anac', ''),
}
```

## 📈 Performance

### Tempos Médios

| Operação                  | Tempo Médio    |
|---------------------------|----------------|
| Download de 1 CSV (50MB)  | ~30-60s        |
| Processamento de 1 CSV    | ~15-30s        |
| Mesclagem com banco       | <5s            |
| **Total (1 mês)**         | **~1-2 minutos**|
| **Total (2 meses)**       | **~3-4 minutos**|

### Otimizações

- Usa `pandas` para processamento eficiente
- Download com streaming (não sobrecarrega RAM)
- Cache de voos existentes em memória
- Logs com níveis (INFO/DEBUG)

## 🎯 Próximos Passos

Após importar os dados históricos:

1. **Gere as páginas HTML**:
   ```bash
   python src/generator.py
   ```

2. **Verifique o resultado**:
   ```bash
   open docs/index.html
   ```

3. **Deploy para produção**:
   ```bash
   # Se usando GitHub Actions
   git add .
   git commit -m "feat: importar dados históricos ANAC"
   git push
   ```

## 📞 Suporte

Para dúvidas ou problemas:

1. Verifique `historical_importer.log`
2. Execute com `python -v src/historical_importer.py` para mais detalhes
3. Consulte a documentação da ANAC: https://www.gov.br/anac/pt-br/assuntos/dados-abertos

---

**Desenvolvido com ❤️ pela equipe MatchFly**

*Última atualização: 12 de Janeiro de 2026*
