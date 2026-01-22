# 📋 Panorama Técnico Completo - MatchFly PSEO

**Versão:** 2.0.0  
**Data:** Janeiro 2026  
**Autor:** Análise Arquitetural Completa

---

## 📌 Índice

1. [Objetivo do Projeto](#1-objetivo-do-projeto)
2. [Arquitetura de Dados](#2-arquitetura-de-dados)
3. [Estrutura de Pastas](#3-estrutura-de-pastas)
4. [Infraestrutura e Deploy](#4-infraestrutura-e-deploy)
5. [Stack Tecnológico](#5-stack-tecnológico)
6. [Fluxo de Execução Completo](#6-fluxo-de-execução-completo)
7. [Componentes Principais](#7-componentes-principais)

---

## 1. Objetivo do Projeto

### 1.1 Visão Geral

**MatchFly PSEO** é uma plataforma automatizada de agregação e análise de status de voos com foco em **SEO (Search Engine Optimization)** e **monetização via afiliados**. O sistema:

- **Coleta dados** de voos atrasados/cancelados do Aeroporto de Guarulhos (GRU)
- **Processa e normaliza** informações de múltiplas fontes (APIs, scrapers, dados históricos ANAC)
- **Gera páginas estáticas HTML** otimizadas para SEO, uma por voo problemático
- **Monetiza** através de links de afiliado (AirHelp) para verificação de indenização ANAC 400/EC 261
- **Publica automaticamente** via GitHub Pages com atualizações a cada 15 minutos

### 1.2 Casos de Uso

1. **Passageiro afetado** busca no Google: "voo KLM 0792 cancelado GRU"
2. **Sistema MatchFly** já possui página estática otimizada: `/voo/voo-klm-0792-gru-cancelado.html`
3. **Página exibe** informações do voo + link para verificar direito a indenização (R$ 10.000)
4. **Conversão** → Passageiro clica no link afiliado → AirHelp processa → MatchFly recebe comissão

### 1.3 Modelo de Negócio

- **Receita:** Comissão por conversão via afiliado (AirHelp)
- **Custo:** Infraestrutura gratuita (GitHub Actions + GitHub Pages)
- **Escalabilidade:** Geração automática de milhares de páginas (uma por voo problemático)

---

## 2. Arquitetura de Dados

### 2.1 Fluxo de Dados Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                    FONTES DE DADOS                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. GRU Scraper (Playwright)                                     │
│     └─> API do Aeroporto de Guarulhos                            │
│         └─> Extrai voos em tempo real                            │
│                                                                   │
│  2. voos_proximos_finalbuild.py                                  │
│     └─> CSV remoto (GitHub externo)                              │
│         └─> Sincroniza dados de outro monitor                    │
│                                                                   │
│  3. historical_importer.py                                       │
│     └─> ANAC SIROS (Registros Oficiais)                          │
│         └─> Dados históricos diários (últimos 30 dias)           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              CAMADA DE PROCESSAMENTO                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  • Normalização de campos                                        │
│  • Validação de dados                                            │
│  • Filtragem (apenas cancelados/atrasados >15min)               │
│  • Dedução de companhias aéreas (prefixos IATA)                  │
│  • Mapeamento IATA (cidades → códigos)                           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              ARMAZENAMENTO (JSON)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Arquivo: data/flights-db.json                                   │
│                                                                   │
│  {                                                               │
│    "flights": [                                                  │
│      {                                                           │
│        "flight_number": "0792",                                  │
│        "airline": "KLM",                                         │
│        "status": "Cancelado",                                    │
│        "scheduled_time": "2026-01-22 01:50",                     │
│        "delay_hours": 0,                                         │
│        "origin": "GRU",                                          │
│        "destination": "Amsterdam",                               │
│        ...                                                       │
│      }                                                           │
│    ],                                                            │
│    "metadata": {                                                 │
│      "scraped_at": "2026-01-22T10:30:00Z",                      │
│      "source": "gru_scraper",                                    │
│      "count": 150                                                │
│    }                                                             │
│  }                                                               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              GERAÇÃO DE PÁGINAS (Generator)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  src/generator.py                                                │
│                                                                   │
│  1. Carrega data/flights-db.json                                 │
│  2. Filtra voos (cancelados OU atraso >15min)                   │
│  3. Para cada voo:                                               │
│     a. Gera slug SEO: voo-klm-0792-gru-cancelado                │
│     b. Prepara contexto (template variables)                    │
│     c. Renderiza template Jinja2                                │
│     d. Salva: public/voo/voo-klm-0792-gru-cancelado.html        │
│  4. Gera sitemap.xml                                             │
│  5. Gera index.html (homepage com 20 voos recentes)              │
│  6. Remove arquivos órfãos (voos que não existem mais)         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              PUBLICAÇÃO (GitHub Pages)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Pasta: public/                                                  │
│                                                                   │
│  • index.html (homepage)                                         │
│  • sitemap.xml (SEO)                                             │
│  • voo/                                                          │
│    ├─ voo-klm-0792-gru-cancelado.html                           │
│    ├─ voo-latam-la3090-gru-atrasado.html                        │
│    └─ ... (milhares de páginas)                                  │
│                                                                   │
│  → Servido via GitHub Pages (matchfly.org)                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Formato de Dados JSON

**Estrutura do arquivo `data/flights-db.json`:**

```json
{
  "flights": [
    {
      "flight_number": "0792",
      "airline": "KLM",
      "status": "Cancelado",
      "scheduled_time": "2026-01-22 01:50",
      "actual_time": "N/A",
      "delay_hours": 0,
      "delay_min": 0,
      "origin": "GRU",
      "destination": "Amsterdam",
      "destination_iata": "AMS",
      "scheduled_date": "2026-01-22",
      "data_partida": "22/01",
      "hora_partida": "01:50"
    }
  ],
  "metadata": {
    "scraped_at": "2026-01-22T10:30:00Z",
    "generated_at": "2026-01-22T10:35:00Z",
    "source": "gru_scraper",
    "count": 150,
    "last_import": "2026-01-22T10:30:00Z"
  }
}
```

### 2.3 Transformação de Dados

#### 2.3.1 Normalização

- **Companhias aéreas:** Dedução via prefixos IATA (ex: "LA" → "LATAM", "KL" → "KLM")
- **Cidades → IATA:** Mapeamento automático (ex: "Amsterdam" → "AMS", "Rio de Janeiro" → "GIG")
- **Status:** Normalização para "Cancelado" ou "Atrasado"
- **Datas:** Conversão para formato ISO (YYYY-MM-DD HH:MM)

#### 2.3.2 Filtragem

Apenas voos que atendem **pelo menos uma** condição são processados:

- Status contém "cancel" ou "cancelado"
- **OU** atraso > 15 minutos (`delay_hours > 0.25`)

#### 2.3.3 Enriquecimento

- **Cálculo de `hours_ago`:** Tempo desde o scraping
- **Deep links afiliados:** URLs pré-preenchidas com destino IATA
- **Regulamentação:** ANAC 400 (nacional) ou EC 261 (internacional)

---

## 3. Estrutura de Pastas

### 3.1 Visão Geral

```
matchfly-pseo/
├── .github/                    # CI/CD e automação
├── data/                       # Armazenamento de dados
├── docs/                       # Documentação técnica
├── public/                     # Site estático gerado
├── src/                        # Código-fonte Python
├── tests/                      # Testes automatizados
├── examples/                   # Exemplos de uso
└── [scripts root]              # Scripts executáveis
```

### 3.2 Detalhamento por Pasta

#### `.github/workflows/`

**Função:** Automação CI/CD via GitHub Actions

**Arquivos:**
- `update-flights.yml` - **Workflow principal** (executa a cada 15 minutos)
  - Sincroniza dados (`voos_proximos_finalbuild.py`)
  - Gera páginas (`src/generator.py`)
  - Faz commit automático das mudanças
- `static.yml` - Deploy para GitHub Pages (quando há push em `main`)

**Fluxo:**
```
Cron (15min) → Checkout → Setup Python → Sync Data → Generate HTML → Auto Commit → Deploy
```

#### `data/`

**Função:** Armazenamento persistente de dados processados

**Arquivos:**
- `flights-db.json` - **Banco de dados principal** (formato JSON)
  - Contém todos os voos coletados
  - Metadados de scraping
  - Estrutura normalizada

**Características:**
- Versionado no Git (para histórico)
- Cache para builds quando scraper falha
- Base de dados para geração de páginas

#### `public/`

**Função:** Site estático servido via GitHub Pages

**Estrutura:**
```
public/
├── index.html              # Homepage (20 voos recentes)
├── sitemap.xml             # Sitemap para SEO
└── voo/                    # Páginas individuais de voos
    ├── voo-klm-0792-gru-cancelado.html
    ├── voo-latam-la3090-gru-atrasado.html
    └── ... (milhares de páginas)
```

**Características:**
- Gerado automaticamente pelo `generator.py`
- Totalmente estático (HTML puro)
- Otimizado para SEO (meta tags, schemas JSON-LD)
- Design responsivo (Tailwind CSS)

#### `src/`

**Função:** Código-fonte Python do projeto

**Estrutura:**
```
src/
├── generator.py                    # Gerador de páginas estáticas
├── historical_importer.py          # Importador de dados históricos ANAC
├── perplexity_search_service.js    # Serviço de busca (opcional)
├── scrapers/                       # Módulos de scraping
│   ├── gru_flights_scraper.py     # Scraper principal GRU
│   ├── gru-scraper.py             # Scraper legado
│   └── gru_proximos/               # Scraper modular avançado
│       ├── scraper_engine.py      # Engine Playwright
│       ├── data_processor.py      # Processamento de dados
│       ├── config.py               # Configurações
│       └── validators.py           # Validações
└── templates/                      # Templates Jinja2
    ├── index.html                  # Template da homepage
    └── tier2-anac400.html         # Template de páginas de voos
```

**Componentes principais:**

1. **`generator.py`** (1.070 linhas)
   - Classe `FlightPageGenerator`
   - Geração de slugs SEO
   - Renderização Jinja2
   - Gestão de órfãos
   - Geração de sitemap

2. **`historical_importer.py`** (1.091 linhas)
   - Download de CSVs da ANAC/SIROS
   - Processamento em chunks (otimizado para memória)
   - Mesclagem com banco existente
   - Deduplicação

3. **`scrapers/`**
   - Múltiplos scrapers para diferentes fontes
   - Playwright para JavaScript-heavy sites
   - Rate limiting e retry logic

#### `docs/`

**Função:** Documentação técnica completa

**Arquivos principais:**
- `PANORAMA_TECNICO_COMPLETO.md` (este arquivo)
- `GENERATOR_V2_ARCHITECTURE.md` - Arquitetura do gerador
- `GITHUB_ACTIONS_GUIDE.md` - Guia de workflows
- `GRU_SCRAPER_USAGE.md` - Documentação do scraper
- `DEPLOYMENT_SUMMARY.md` - Resumo de deploy
- `CLOUD_COST_OPTIMIZATION.md` - Otimizações de custo

#### `tests/`

**Função:** Testes automatizados

**Arquivos:**
- `test_generator.py` - Testes do gerador
- `test_gru_flights_scraper.py` - Testes do scraper
- `test_historical_importer.py` - Testes do importador
- `mock_data.py` - Dados mockados para testes

#### Scripts Root

**Arquivos executáveis na raiz:**

- `voos_proximos_finalbuild.py` - **Sincronizador principal**
  - Baixa CSV remoto
  - Converte para JSON
  - Salva em `data/flights-db.json`
  
- `run_pipeline.sh` - Pipeline local completo
  - Executa scraper
  - Gera páginas
  - Mostra estatísticas

---

## 4. Infraestrutura e Deploy

### 4.1 Arquitetura de Deploy

```
┌─────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS (CI/CD)                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Trigger: Cron (a cada 15 minutos)                           │
│  Runner: ubuntu-latest                                        │
│                                                               │
│  Steps:                                                       │
│  1. Checkout código                                          │
│  2. Setup Python 3.12                                        │
│  3. Install dependencies (requests, pandas, jinja2, etc)     │
│  4. Sync Data (voos_proximos_finalbuild.py)                 │
│  5. Generate HTML (src/generator.py)                         │
│  6. Auto Commit (git-auto-commit-action)                     │
│  7. Deploy (via static.yml quando há push)                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    GITHUB PAGES (Hosting)                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Source: Branch main (pasta public/)                         │
│  URL: https://matchfly.org                                   │
│  CDN: Cloudflare (opcional, via DNS)                         │
│                                                               │
│  Características:                                            │
│  • Deploy automático a cada push em main                     │
│  • HTTPS automático                                          │
│  • CDN global (via GitHub)                                   │
│  • Custo: $0 (gratuito)                                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Workflow Detalhado

#### 4.2.1 `update-flights.yml` (Principal)

**Frequência:** A cada 15 minutos (`*/15 * * * *`)

**Jobs:**
1. **monitor-operations**
   - Permissões: `contents: write` (para commits automáticos)
   - Steps:
     - Checkout repositório
     - Setup Python 3.12
     - Install dependencies
     - **Sync Data:** `python voos_proximos_finalbuild.py`
       - Baixa CSV remoto
       - Converte para JSON
       - Salva em `data/flights-db.json`
     - **Generate HTML:** `python src/generator.py`
       - Lê `data/flights-db.json`
       - Gera páginas em `public/`
       - Cria `sitemap.xml`
       - Cria `index.html`
     - **Auto Commit:** `stefanzweifel/git-auto-commit-action@v5`
       - Commita mudanças em `public/`, `data/`, `voos_atrasados_gru.csv`
       - Mensagem: "deploy: update site content"

#### 4.2.2 `static.yml` (Deploy)

**Trigger:** Push para branch `main`

**Jobs:**
1. **deploy**
   - Environment: `github-pages`
   - Steps:
     - Checkout
     - Setup Pages
     - Upload artifact (pasta `public/`)
     - Deploy to GitHub Pages

**Resultado:** Site atualizado em `https://matchfly.org`

### 4.3 Otimizações de Infraestrutura

#### 4.3.1 Migração para GitHub Pages

**Antes:** Netlify (custos de build)
**Depois:** GitHub Pages (gratuito, ilimitado)

**Benefícios:**
- ✅ Deploys ilimitados
- ✅ Sem custos de build minutes
- ✅ CDN global incluído
- ✅ HTTPS automático

#### 4.3.2 Cache de Dados

- **Cache do GitHub Actions:** `data/flights-db.json`
- **Fallback:** Se scraper falhar, usa cache (evita site vazio)
- **TTL:** Cache válido por 2 horas

#### 4.3.3 Rate Limiting

- **Scrapers:** Delay de 1.5s entre requisições
- **ANAC SIROS:** Rate limiting para evitar bloqueios
- **User-Agents rotativos:** Evita detecção

### 4.4 Monitoramento

**Logs:**
- GitHub Actions logs (disponíveis na UI)
- Arquivos de log locais:
  - `generator.log` (gerador)
  - `historical_importer.log` (importador)

**Métricas:**
- Número de voos coletados
- Páginas geradas
- Taxa de sucesso do scraper
- Tempo de execução do workflow

---

## 5. Stack Tecnológico

### 5.1 Linguagens e Runtimes

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **Python** | 3.12 | Linguagem principal (scrapers, gerador, importador) |
| **JavaScript** | ES6+ | Serviços auxiliares (Perplexity, validações) |
| **Bash** | POSIX | Scripts de automação (`run_pipeline.sh`) |

### 5.2 Bibliotecas Python Principais

| Biblioteca | Versão | Função |
|------------|--------|--------|
| **requests** | ≥2.25.0 | Cliente HTTP (downloads, APIs) |
| **pandas** | ≥1.0.0 | Processamento de dados (CSV, DataFrames) |
| **playwright** | latest | Web scraping (navegador headless) |
| **jinja2** | latest | Templates HTML (renderização) |
| **python-slugify** | latest | Geração de URLs SEO-friendly |
| **urllib3** | latest | Requisições HTTP (com SSL disable para macOS) |

### 5.3 Ferramentas de Frontend

| Tecnologia | Uso |
|------------|-----|
| **Tailwind CSS** | Framework CSS (via CDN) |
| **Vanilla JavaScript** | Interatividade (checkboxes, animações) |
| **JSON-LD** | Schemas estruturados (SEO) |

### 5.4 Infraestrutura

| Serviço | Função |
|---------|--------|
| **GitHub Actions** | CI/CD (execução automatizada) |
| **GitHub Pages** | Hosting estático (deploy) |
| **Cloudflare** | CDN/DNS (opcional, via configuração DNS) |

### 5.5 Ferramentas de Desenvolvimento

| Ferramenta | Uso |
|------------|-----|
| **Git** | Controle de versão |
| **Jinja2** | Engine de templates |
| **Playwright** | Automação de navegador |
| **pytest** | Testes (estrutura preparada) |

### 5.6 Dependências Externas

**APIs/Serviços:**
- Aeroporto de Guarulhos (API não documentada, descoberta automática)
- ANAC SIROS (Registros oficiais de voos)
- GitHub (CSV remoto via `raw.githubusercontent.com`)

**CDNs:**
- Tailwind CSS (via CDN)
- Google Fonts (Inter)

---

## 6. Fluxo de Execução Completo

### 6.1 Fluxo Automatizado (GitHub Actions)

```
┌─────────────────────────────────────────────────────────────┐
│  CRON TRIGGER (a cada 15 minutos)                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: CHECKOUT & SETUP                                   │
│  • Checkout código do repositório                           │
│  • Setup Python 3.12                                        │
│  • Install dependencies (pip install ...)                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: SYNC DATA                                           │
│  • Executa: python voos_proximos_finalbuild.py               │
│  • Baixa CSV remoto (GitHub externo)                        │
│  • Converte CSV → JSON                                       │
│  • Salva: data/flights-db.json                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: GENERATE HTML                                      │
│  • Executa: python src/generator.py                         │
│  • Carrega: data/flights-db.json                             │
│  • Filtra voos (cancelados/atrasados >15min)                │
│  • Para cada voo:                                            │
│    - Gera slug SEO                                          │
│    - Renderiza template Jinja2                              │
│    - Salva: public/voo/voo-XXX.html                         │
│  • Gera: public/index.html (homepage)                       │
│  • Gera: public/sitemap.xml                                 │
│  • Remove arquivos órfãos                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: AUTO COMMIT                                        │
│  • git-auto-commit-action                                   │
│  • Commita mudanças em:                                     │
│    - public/*.html                                          │
│    - data/flights-db.json                                   │
│    - voos_atrasados_gru.csv                                 │
│  • Push para branch main                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: DEPLOY (static.yml)                                │
│  • Trigger: Push em main                                     │
│  • Upload artifact: public/                                  │
│  • Deploy to GitHub Pages                                    │
│  • Site atualizado: https://matchfly.org                    │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Fluxo Manual (Local)

```bash
# 1. Ativar ambiente virtual
source venv/bin/activate

# 2. Sincronizar dados (opcional, se não usar GitHub Actions)
python voos_proximos_finalbuild.py

# 3. Gerar páginas
python src/generator.py

# 4. Visualizar localmente
open public/index.html
```

### 6.3 Fluxo de Importação Histórica

```bash
# Importar dados históricos da ANAC (últimos 30 dias)
python src/historical_importer.py

# Processo:
# 1. Gera URLs de download (SIROS - registros diários)
# 2. Baixa CSVs (um por dia, últimos 30 dias)
# 3. Processa em chunks (otimizado para memória)
# 4. Filtra voos SBGR (Guarulhos) com atraso >15min
# 5. Mescla com data/flights-db.json (evita duplicatas)
# 6. Salva resultado atualizado
```

---

## 7. Componentes Principais

### 7.1 FlightPageGenerator (`src/generator.py`)

**Responsabilidade:** Geração de páginas estáticas HTML

**Métodos principais:**
- `setup_and_validate()` - Validação e criação de pastas
- `load_flight_data()` - Carrega JSON de voos
- `should_generate_page()` - Filtra voos (cancelados/atrasados)
- `generate_slug()` - Gera URLs SEO-friendly
- `prepare_template_context()` - Prepara variáveis para template
- `generate_page_resilient()` - Gera página com try/except
- `manage_orphans()` - Remove arquivos antigos
- `generate_sitemap()` - Cria sitemap.xml
- `generate_homepage()` - Cria index.html

**Características:**
- Resiliência total (try/except por voo)
- Gestão de órfãos (remove páginas de voos que não existem mais)
- Geração de sitemap automática
- Logging detalhado

### 7.2 ANACHistoricalImporter (`src/historical_importer.py`)

**Responsabilidade:** Importação de dados históricos da ANAC

**Métodos principais:**
- `get_anac_download_urls()` - Gera URLs de download (SIROS)
- `download_csv()` - Baixa arquivos CSV com rate limiting
- `process_csv_file()` - Processa CSV em chunks
- `_process_row()` - Converte linha CSV → formato MatchFly
- `merge_flights()` - Mescla com banco existente (deduplicação)

**Características:**
- Processamento em chunks (otimizado para 16GB RAM)
- Rate limiting (1.5s entre downloads)
- Deduplicação inteligente
- Suporte a múltiplos formatos de data/hora

### 7.3 ScraperEngine (`src/scrapers/gru_proximos/scraper_engine.py`)

**Responsabilidade:** Web scraping com Playwright

**Características:**
- Modo headless (sem interface gráfica)
- Carregamento de páginas dinâmicas (JavaScript)
- Cliques automáticos em "Carregar mais"
- Rate limiting e User-Agents rotativos
- Modo offline (congelamento de DOM)

### 7.4 Templates Jinja2

**`src/templates/tier2-anac400.html`**
- Template de páginas individuais de voos
- SEO completo (meta tags, JSON-LD schemas)
- Design responsivo (Tailwind CSS)
- CRO-optimized (call-to-actions, affiliate links)

**`src/templates/index.html`**
- Template da homepage
- Lista 20 voos mais recentes
- Variáveis dinâmicas para growth/referral

### 7.5 Scripts de Sincronização

**`voos_proximos_finalbuild.py`**
- Baixa CSV remoto
- Normaliza colunas
- Combina data + hora para ordenação
- Converte para JSON
- Salva em `data/flights-db.json`

---

## 8. Considerações Técnicas

### 8.1 Performance

**Otimizações:**
- Processamento em chunks (pandas) para arquivos grandes
- Cache de dados (GitHub Actions)
- Geração paralela de páginas (futuro: async)
- CDN global (GitHub Pages)

**Métricas típicas:**
- Geração de 100 páginas: ~5-10 segundos
- Processamento de CSV ANAC (1 dia): ~30-60 segundos
- Deploy GitHub Pages: ~1-2 minutos

### 8.2 Escalabilidade

**Limitações atuais:**
- Processamento sequencial de voos
- Memória: ~500MB para processar 1000 voos

**Melhorias futuras:**
- Processamento paralelo (multiprocessing)
- Geração assíncrona de páginas
- Cache de templates Jinja2

### 8.3 Segurança

**Práticas implementadas:**
- Validação de input em todos os scrapers
- Sanitização de dados antes do processamento
- Rate limiting para evitar bloqueios
- Sem armazenamento de credenciais em código
- SSL verification desabilitada apenas para macOS (desenvolvimento)

### 8.4 Manutenibilidade

**Boas práticas:**
- Código modular (separação de responsabilidades)
- Logging detalhado (arquivo + console)
- Documentação completa (docs/)
- Type hints (Python)
- Testes automatizados (estrutura preparada)

---

## 9. Próximos Passos para Novos Desenvolvedores

### 9.1 Setup Inicial

```bash
# 1. Clone o repositório
git clone <repository-url>
cd matchfly-pseo

# 2. Crie ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows

# 3. Instale dependências
pip install -r requirements.txt

# 4. Execute pipeline local
./run_pipeline.sh
```

### 9.2 Entendendo o Código

1. **Comece por:** `src/generator.py` (gerador de páginas)
2. **Depois:** `voos_proximos_finalbuild.py` (sincronização de dados)
3. **Explore:** `src/scrapers/` (diferentes scrapers)
4. **Leia:** `docs/` (documentação técnica)

### 9.3 Adicionando Novos Scrapers

1. Crie arquivo em `src/scrapers/novo_scraper.py`
2. Implemente classe com método `fetch_flights()`
3. Retorne lista de dicionários no formato MatchFly
4. Integre no pipeline (`voos_proximos_finalbuild.py` ou workflow)

### 9.4 Modificando Templates

⚠️ **ATENÇÃO:** Siga as regras em `.cursorrules`:
- NUNCA altere estrutura HTML ou classes CSS dos templates existentes
- Apenas injete dados dinâmicos nos locais corretos
- Mantenha scripts de animação e FAQ intactos

---

## 10. Glossário Técnico

- **ANAC 400:** Resolução da ANAC que garante indenização para voos nacionais
- **EC 261:** Regulamentação europeia para voos internacionais
- **IATA:** Código de 3 letras para aeroportos (ex: GRU, AMS, GIG)
- **ICAO:** Código de 4 letras para aeroportos (ex: SBGR, EHAM)
- **SIROS:** Sistema de Registro de Operações da ANAC
- **Slug:** URL amigável (ex: `voo-klm-0792-gru-cancelado`)
- **Orfão:** Arquivo HTML de voo que não existe mais no banco de dados
- **Deep Link:** URL pré-preenchida com parâmetros (aumenta conversão)

---

## 11. Referências

- [Documentação GitHub Actions](https://docs.github.com/en/actions)
- [GitHub Pages](https://pages.github.com/)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)
- [Playwright](https://playwright.dev/python/)
- [ANAC SIROS](https://siros.anac.gov.br/)

---

**Fim do Panorama Técnico Completo**

*Este documento serve como referência técnica completa para desenvolvedores que irão trabalhar no projeto MatchFly PSEO.*
