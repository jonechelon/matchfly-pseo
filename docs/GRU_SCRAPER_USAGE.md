# GRU Airport Flight Scraper - Guia de Uso

## 📖 Visão Geral

O **GRU Flight Scraper** é um scraper profissional desenvolvido para extrair dados de voos do Aeroporto Internacional de Guarulhos (GRU). O scraper implementa múltiplas estratégias para descobrir e utilizar endpoints de API oculta, sem necessidade de Selenium.

## ✨ Características

### 🔍 Descoberta Inteligente de API
- Tenta múltiplos endpoints comuns de API
- Parseia dados JSON embutidos no HTML quando necessário
- Se a coleta falhar: retorna lista vazia e registra erro crítico (sem dados fake)

### 🛡️ Tratamento Robusto de Erros
- Try-catch em todos os pontos críticos
- Logging detalhado de todos os erros
- Graceful degradation (continua mesmo com falhas parciais)

### 📊 Filtragem Inteligente
- Filtra voos **Cancelados**
- Filtra voos **Atrasados** (atraso > 2 horas)
- Calcula atraso em horas automaticamente

### 📝 Logging Completo
- Logs no console (stdout)
- Logs em arquivo (`gru_scraper.log`)
- Diferentes níveis: INFO, WARNING, ERROR, DEBUG

## 🚀 Como Usar

### 1. Instalação das Dependências

```bash
cd ~/matchfly

# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. Executar o Scraper

**Método 1: Script Runner (Recomendado)**
```bash
python3 run_gru_scraper.py
```

**Método 2: Diretamente**
```bash
python3 src/scrapers/gru_flights_scraper.py
```

**Método 3: Como Módulo**
```bash
python3 -m src.scrapers.gru_flights_scraper
```

### 3. Usar Programaticamente

```python
from src.scrapers.gru_flights_scraper import GRUFlightScraper

# Criar instância do scraper
scraper = GRUFlightScraper(output_file="data/flights-db.json")

# Executar scraping completo
scraper.run()

# Ou usar métodos individuais
flights = scraper.fetch_flights()
filtered = scraper.filter_flights(flights)
scraper.save_to_json(filtered)
```

## 📁 Arquivos Gerados

### `data/flights-db.json`
Arquivo principal com os dados dos voos:

```json
{
  "metadata": {
    "source": "GRU Airport (gru.com.br)",
    "scraped_at": "2026-01-11T18:34:35.005828",
    "total_flights": 5,
    "filters": "Cancelados ou Atrasados > 2h"
  },
  "flights": [
    {
      "flight_number": "LA3090",
      "airline": "LATAM",
      "scheduled_time": "2026-01-11 15:34:34",
      "actual_time": "2026-01-11 18:04:34",
      "status": "Atrasado",
      "delay_hours": 2.5
    }
  ]
}
```

### `gru_scraper.log`
Arquivo de log com histórico de execuções:

```
2026-01-11 18:34:34,243 - scrapers.gru_flights_scraper - INFO - 🚀 GRU Airport Flight Scraper - Iniciando
2026-01-11 18:34:34,246 - scrapers.gru_flights_scraper - INFO - 🔍 Iniciando descoberta de API endpoints...
2026-01-11 18:34:35,008 - scrapers.gru_flights_scraper - INFO - ✅ Scraping concluído com sucesso!
```

## 🔧 Configuração Avançada

### Personalizar Output

```python
# Mudar caminho do arquivo de saída
scraper = GRUFlightScraper(output_file="custom/path/flights.json")

# Modificar filtros
def custom_filter(flight):
    return flight['delay_hours'] > 3  # Apenas atrasos > 3h

all_flights = scraper.fetch_flights()
custom_filtered = [f for f in all_flights if custom_filter(f)]
scraper.save_to_json(custom_filtered)
```

### Adicionar Novos Endpoints

Edite a lista `API_ENDPOINTS` na classe:

```python
API_ENDPOINTS = [
    "/pt-br/api/voos/partidas",
    "/seu/novo/endpoint",
]
```

### Ajustar Logging

```python
import logging

# Mudar nível de log para DEBUG
logging.getLogger('scrapers.gru_flights_scraper').setLevel(logging.DEBUG)

# Desabilitar logs no console
logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.StreamHandler)]
```

## 🏗️ Arquitetura do Código

### Classes Principais

#### `GRUFlightScraper`
Classe principal que gerencia todo o processo de scraping.

**Métodos Públicos:**
- `run()` - Executa o scraper completo
- `fetch_flights()` - Busca dados de voos
- `filter_flights(flights)` - Filtra voos por critérios
- `save_to_json(flights)` - Salva dados em JSON

**Métodos Internos:**
- `_extract_next_build_id(html)` - Captura o `buildId` do Next.js no HTML
- `fetch_next_data_endpoint(build_id)` - Usa `/_next/data/{buildId}/...` para buscar JSON
- `_filter_only_today(flights)` - Mantém apenas voos com data de hoje
- `discover_api_endpoint()` - Descobre endpoints válidos
- `scrape_html_fallback()` - Fallback quando API não está disponível
- `_parse_flight(flight_data)` - Parseia dados individuais de voo
- `_parse_datetime(dt_string)` - Parseia strings de data/hora
- `_parse_embedded_data(data)` - Extrai dados JSON do HTML

### Fluxo de Execução

```
1. Inicialização
   └─ Configura headers e sessão HTTP

2. Descoberta de API
   ├─ Testa endpoints conhecidos
   ├─ Valida respostas JSON
   └─ Retorna primeiro endpoint válido

3. Coleta de Dados
   ├─ Sessão com Cloudscraper (cookies/JS challenges automaticamente)
   ├─ Carrega `/pt-br/voos` para obter `buildId` e tenta `/_next/data/{buildId}/pt-br/voos.json`
   ├─ Se API encontrada: usa endpoint
   ├─ Se API não encontrada: parseia HTML
   └─ Se falha total: retorna lista vazia e registra erro crítico (sem dados fake)

4. Processamento
   ├─ Normaliza dados de voos
   ├─ Calcula atrasos
   └─ Parseia horários

4b. Filtro de Data
   └─ Mantém apenas voos com data de hoje para evitar persistência de voos antigos

5. Filtragem
   ├─ Identifica voos cancelados
   ├─ Identifica voos atrasados > 2h
   └─ Retorna lista filtrada

6. Persistência
   ├─ Adiciona metadados
   ├─ Formata JSON com indentação
   └─ Salva em arquivo
```

## 🐛 Troubleshooting

### Erro: ModuleNotFoundError

**Causa:** Dependências não instaladas

**Solução:**
```bash
pip install -r requirements.txt
```

### Erro: Permission Denied ao salvar JSON

**Causa:** Pasta `data/` não existe ou sem permissão

**Solução:**
```bash
mkdir -p data
chmod 755 data
```

### Warning: urllib3 OpenSSL

**Causa:** Versão antiga do OpenSSL/LibreSSL

**Solução:** Não afeta funcionalidade, mas pode atualizar:
```bash
pip install --upgrade urllib3
```

### Nenhum dado extraído

**Causa:** Site mudou estrutura ou API indisponível

**Solução:**
1. Verifique logs para detalhes
2. Atualize endpoints na lista `API_ENDPOINTS`
3. Use modo DEBUG para análise:
   ```python
   logger.setLevel(logging.DEBUG)
   ```

### Rate Limiting / Bloqueio

**Causa:** Muitas requisições em curto período

**Solução:** Adicione delays entre requisições:
```python
import time
time.sleep(2)  # 2 segundos entre requisições
```

## 📈 Performance

### Métricas Típicas
- **Tempo de execução:** ~1-5 segundos
- **Requisições HTTP:** 3-10 (dependendo de endpoints testados)
- **Memória:** < 50MB
- **Tamanho do arquivo JSON:** ~1-10KB (varia com número de voos)

### Otimizações Implementadas
- ✅ Sessão HTTP reutilizável
- ✅ Timeout em todas as requisições
- ✅ Lazy evaluation de dados
- ✅ Early return em descoberta de API

## 🔐 Segurança

### Práticas Implementadas
- ✅ Validação de dados de entrada
- ✅ Sanitização de strings
- ✅ Headers de User-Agent realista
- ✅ Timeouts para prevenir hanging
- ✅ Sem credenciais hardcoded

### Recomendações
- 🔸 Respeite robots.txt do site
- 🔸 Implemente rate limiting em produção
- 🔸 Use proxy se necessário
- 🔸 Monitore logs de erro

## 🚀 Próximos Passos

### Melhorias Sugeridas
- [ ] Implementar cache de requisições
- [ ] Adicionar suporte a proxy
- [ ] Criar scheduler para execução automática
- [ ] Adicionar testes unitários
- [ ] Implementar retry com backoff exponencial
- [ ] Adicionar suporte a múltiplos aeroportos
- [ ] Criar API REST para consumir dados
- [ ] Dashboard web para visualização

### Integrações Possíveis
- 📧 Notificações por email (voos cancelados)
- 💬 Bot Telegram/WhatsApp
- 📊 Dashboard Grafana
- 🔔 Alertas em tempo real
- 🗄️ Banco de dados (PostgreSQL/MongoDB)

## 📚 Recursos Adicionais

### Documentação
- [BeautifulSoup4 Docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Cloudscraper](https://github.com/VeNoMouS/cloudscraper)
- [Python Logging](https://docs.python.org/3/library/logging.html)

### Ferramentas Úteis
- **Insomnia/Postman:** Testar APIs manualmente
- **Chrome DevTools:** Inspecionar chamadas de rede
- **jq:** Processar JSON na linha de comando

## 👥 Suporte

Para dúvidas ou problemas:
1. Verifique os logs em `gru_scraper.log`
2. Consulte esta documentação
3. Abra uma issue no repositório

---

**Versão:** 1.0.0  
**Última Atualização:** 2026-01-11  
**Licença:** MIT

