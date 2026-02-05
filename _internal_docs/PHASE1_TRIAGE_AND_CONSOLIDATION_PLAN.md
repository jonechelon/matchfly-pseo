# Fase 1: Análise e Triagem da Documentação MatchFly

**Data:** Fevereiro 2026  
**Objetivo:** Triagem, consolidação e plano de atualização da documentação em `_internal_docs/` para refletir o estado atual do projeto (GitHub Pages via `/docs`, UI Split-Flap, Python Generator V2).

---

## 1. Estado atual do código (referência)

### 1.1 Infraestrutura real

| Aspecto | Estado atual (código) |
|--------|------------------------|
| **Output do site** | `docs/` (não `public/`) |
| **Gerador** | `src/generator.py` → escreve em `docs/`, `docs/voo/`, `docs/destino/` |
| **Deploy** | GitHub Pages via pasta **Source: main → /docs**; workflow faz commit em `docs/` e push na `main` |
| **CNAME** | Gerado em `docs/CNAME` com `matchfly.org` |
| **404** | `docs/404.html` gerado pelo generator |
| **Script de dados** | `voos_proximos_finalbuild.py` (raiz); **não** `run_gru_scraper.py` (está em `_archive/`) |
| **Pipeline** | `run_pipeline.sh` existe; workflow: checkout → Python 3.12 → pip install → `voos_proximos_finalbuild.py` → `python src/generator.py` → git add docs/ → commit → push |
| **Netlify / gh-pages** | Não utilizados; deploy é commit na `main` em `docs/` |

### 1.2 Estrutura de pastas relevante

```
matchfly-pseo/
├── .github/workflows/update-flights.yml   # Único workflow: commit docs/ na main
├── data/                                  # flights-db.json, .xls ANAC
├── docs/                                  # Saída do generator (site estático)
├── src/
│   ├── generator.py                       # Output dir = docs
│   ├── enrichment.py, historical_importer.py, indexer.py, scl_corrections.py
│   ├── scrapers/ (gru_flights_scraper, gru-scraper, gru_proximos/)
│   └── templates/ (base, index, tier2-anac400, 404, atrasados, cancelados, cidades, privacy, components/, includes/)
├── _internal_docs/                        # Documentação interna (não pública)
├── _archive/                              # Scripts antigos (run_gru_scraper, run_historical_import, etc.)
├── voos_proximos_finalbuild.py            # Scraper/sync de dados (usado pelo CI)
├── run_pipeline.sh
└── README.md
```

---

## 2. Arquivos obsoletos (mover para `_internal_docs/archive/`)

Arquivos que descrevem arquitetura antiga, scripts que não existem mais na raiz ou fluxos substituídos.

| Arquivo | Motivo |
|---------|--------|
| **CURSOR_PERPLEXITY_FIX.md** | Fix pontual de configuração Cursor/Perplexity; não é arquitetura do projeto. |
| **teste_escrita.txt** | Arquivo de teste ("O Python consegue escrever aqui!"); sem valor técnico. |
| **SUCCESS_BANNER.txt** | Banner de conclusão de um milestone; referências a `public/`, `run_historical_import.py`, `open public/index.html`. |
| **FINAL_OVERVIEW.txt** | Estrutura antiga: `public/` como output, `run_gru_scraper.py`, Netlify, gh-pages. |
| **GITHUB_ACTIONS_GUIDE.md** | Guia completo baseado em **Netlify** (NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID); fluxo atual é commit em `docs/` na main, sem Netlify. |
| **CLOUD_COST_OPTIMIZATION.md** | Descreve migração Netlify → gh-pages com `peaceiris/actions-gh-pages`; hoje o deploy é via pasta `/docs` na main, não gh-pages. |

**Ação:** Criar `_internal_docs/archive/` e **mover** (não apagar) os 6 arquivos acima.

---

## 3. Redundâncias e fusões propostas

### 3.1 Resumos e guias duplicados

- Vários `*_SUMMARY.md`, `*_GUIDE.md`, `*_OVERVIEW.txt` cobrem os mesmos temas com níveis de detalhe diferentes.
- Proposta: reduzir a **quantidade** de arquivos e criar **poucos mestres** atualizados.

### 3.2 Fusão → ARCHITECTURE.md (arquitetura e fluxo)

**Fundir em um único `_internal_docs/ARCHITECTURE.md` atualizado:**

| Origem | Conteúdo a aproveitar |
|--------|----------------------|
| **GENERATOR_V2_ARCHITECTURE.md** | Steps do generator, validações, filtros; **atualizar** todas as menções de `public/` → `docs/`. |
| **PANORAMA_TECNICO_COMPLETO.md** | Visão geral, fluxo de dados, stack, componentes; **atualizar** seção de deploy e estrutura (docs/ como output, sem Netlify). |
| **PROJECT_STRUCTURE.txt** | Árvore de pastas; **substituir** por árvore atual (docs/, _internal_docs/, voos_proximos_finalbuild.py). |
| **PROJECT_STRUCTURE_UPDATED.txt** | Idem; consolidar na árvore única em ARCHITECTURE.md. |

**Conteúdo alvo:**  
Fluxo **Dados (JSON/CSV) → Python Generator (Jinja2) → docs/ → GitHub Pages (Source: main, /docs)**. Estrutura de pastas atual, componentes em `src/`, papel de `CNAME` e `.nojekyll` em `docs/`.

**Após fusão:** Os 4 arquivos acima podem ser movidos para `_internal_docs/archive/` (manter como referência histórica).

### 3.3 Fusão → DEPLOY.md (deploy e CI)

**Fundir em um único `_internal_docs/DEPLOY.md`:**

| Origem | Conteúdo a aproveitar |
|--------|----------------------|
| **DEPLOYMENT_SUMMARY.md** | Conceitos de deploy, comandos locais; **reescrever** para output em `docs/`, sem Netlify. |
| **GITHUB_ACTIONS_SUMMARY.md** | Descrição do workflow; **atualizar** para o workflow real (sem cache de JSON, sem Netlify): checkout → pip → voos_proximos_finalbuild → generator → git add docs/ → commit → push. |

**Conteúdo alvo:**  
Deploy via **GitHub Pages com pasta `/docs`**: configuração em Settings → Pages (main, /docs), papel do `CNAME` em `docs/`, passo a passo do workflow atual e como rodar localmente (`python src/generator.py`, visualizar `docs/`).

**Após fusão:** Os 2 arquivos podem ir para `_internal_docs/archive/`.

### 3.4 Arquivos que permanecem (com atualizações pontuais)

| Arquivo | Ação |
|---------|------|
| **GENERATOR_GUIDE.md** | Manter; **atualizar** todas as referências `public/` → `docs/`, comandos de abertura (`open docs/index.html`). |
| **GRU_SCRAPER_USAGE.md** | Manter se descrever `src/scrapers/` e fontes de dados; **verificar** se menciona `run_gru_scraper.py` e atualizar para `voos_proximos_finalbuild.py` ou run_pipeline onde fizer sentido. |
| **QUICKSTART.md** | Manter; **atualizar** para: ambiente virtual → `pip install -r requirements.txt` → `python voos_proximos_finalbuild.py` (ou run_pipeline) → `python src/generator.py` → `open docs/index.html`. |
| **QUICK_REFERENCE.md** | Manter; **atualizar** comandos e paths para `docs/` e scripts atuais; remover/ajustar referências a `run_historical_import.py` se estiver em _archive. |
| **GOOGLE_INDEXING_SETUP.md** | Manter; **atualizar** path do sitemap: `public/sitemap.xml` → `docs/sitemap.xml`. |
| **INDEXER_IMPLEMENTATION_SUMMARY.md** | Manter; **atualizar** paths: `public/` → `docs/`. |
| **HISTORICAL_IMPORT_README.md** | Manter; **atualizar** para: script em `_archive/run_historical_import.py` ou uso de `src/historical_importer.py`; output do generator em `docs/`. |
| **HISTORICAL_IMPORT_SUMMARY.md** | Manter; **atualizar** paths e comandos para `docs/`. |
| **HISTORICAL_IMPORTER_GUIDE.md** | Manter; **atualizar** `open public/` → `docs/`. |
| **IATA_DICTIONARY_GUIDE.md** | Manter; **atualizar** exemplos com `public/` → `docs/` se houver. |
| **IATA_EXPANSION_SUMMARY.md** | Manter; **atualizar** referências a `public/` → `docs/`. |
| **IMPLEMENTATION_COMPLETE.md** | Manter como registro histórico; opcional: nota no topo "Documento histórico; ver ARCHITECTURE.md e DEPLOY.md para estado atual." |
| **PERPLEXITY_INTEGRATION_SUMMARY.md** | Manter se o serviço Perplexity ainda for usado no projeto. |
| **VISUAL_GUIDE.md** | Manter; **atualizar** todos os paths e exemplos para `docs/` e UI atual (Split-Flap quando aplicável). |
| **CLOUD_COST_OPTIMIZATION.md** | **Arquivar** (já listado em obsoletos); fala de Netlify e gh-pages antigos. |

---

## 4. Plano de ação consolidado (para aprovação)

### 4.1 Arquivar (mover para `_internal_docs/archive/`)

1. Criar diretório `_internal_docs/archive/`.
2. Mover para `archive/`:
   - CURSOR_PERPLEXITY_FIX.md  
   - teste_escrita.txt  
   - SUCCESS_BANNER.txt  
   - FINAL_OVERVIEW.txt  
   - GITHUB_ACTIONS_GUIDE.md  
   - CLOUD_COST_OPTIMIZATION.md  

### 4.2 Criar arquivos mestres (novos/reescritos)

3. **README.md (raiz)**  
   - O que é o MatchFly (agregação de voos GRU, páginas estáticas SEO, afiliado).  
   - Descrição da UI atual (Split-Flap / Flip Cards).  
   - Como rodar localmente: `python voos_proximos_finalbuild.py` (dados) e `python src/generator.py` (site).  
   - Estrutura resumida: `src/`, `docs/` (output do site), `data/`, `_internal_docs/`.  
   - Link para documentação interna em `_internal_docs/` (ARCHITECTURE, DEPLOY, QUICKSTART).

4. **_internal_docs/ARCHITECTURE.md**  
   - Fusão de GENERATOR_V2_ARCHITECTURE, PANORAMA_TECNICO_COMPLETO, PROJECT_STRUCTURE, PROJECT_STRUCTURE_UPDATED.  
   - Fluxo: Dados → Generator (Jinja2) → docs/ → GitHub Pages.  
   - Estrutura de pastas atual; sem referência a `public/` ou Netlify.

5. **_internal_docs/DEPLOY.md**  
   - Fusão de DEPLOYMENT_SUMMARY e GITHUB_ACTIONS_SUMMARY.  
   - Deploy via `/docs` (main), CNAME, workflow atual (commit + push em `docs/`).

### 4.3 Arquivar após fusão

6. Após criar ARCHITECTURE.md e DEPLOY.md, mover para `_internal_docs/archive/`:  
   - GENERATOR_V2_ARCHITECTURE.md  
   - PANORAMA_TECNICO_COMPLETO.md  
   - PROJECT_STRUCTURE.txt  
   - PROJECT_STRUCTURE_UPDATED.txt  
   - DEPLOYMENT_SUMMARY.md  
   - GITHUB_ACTIONS_SUMMARY.md  

### 4.4 Atualizações pontuais (sem fusão)

7. Nos arquivos **mantidos** (GENERATOR_GUIDE, GRU_SCRAPER_USAGE, QUICKSTART, QUICK_REFERENCE, GOOGLE_INDEXING_SETUP, INDEXER_IMPLEMENTATION_SUMMARY, HISTORICAL_IMPORT_*, IATA_*, VISUAL_GUIDE):  
   - Substituir `public/` por `docs/` onde for path de output do site.  
   - Ajustar comandos para scripts atuais (`voos_proximos_finalbuild.py`, `python src/generator.py`, `open docs/index.html`).  
   - Opcional: remover emojis dos trechos alterados, conforme regra de design.

### 4.5 Fase 2 (após aprovação)

8. Usar Perplexity (ou MCP) para:  
   - Validar práticas de `sitemap.xml` e `robots.txt` (generator.py) vs Google Search Console para sites estáticos.  
   - Verificar se o padrão "commit na main em `/docs`" e permissões do workflow estão alinhados às recomendações atuais do GitHub Actions.

---

## 5. Resumo visual

```
_internal_docs/
├── archive/                          # NOVO: obsoletos + pré-fusão
│   ├── CURSOR_PERPLEXITY_FIX.md
│   ├── teste_escrita.txt
│   ├── SUCCESS_BANNER.txt
│   ├── FINAL_OVERVIEW.txt
│   ├── GITHUB_ACTIONS_GUIDE.md
│   ├── CLOUD_COST_OPTIMIZATION.md
│   ├── GENERATOR_V2_ARCHITECTURE.md  (após fusão)
│   ├── PANORAMA_TECNICO_COMPLETO.md
│   ├── PROJECT_STRUCTURE.txt
│   ├── PROJECT_STRUCTURE_UPDATED.txt
│   ├── DEPLOYMENT_SUMMARY.md
│   └── GITHUB_ACTIONS_SUMMARY.md
│
├── ARCHITECTURE.md                   # NOVO (fusão)
├── DEPLOY.md                         # NOVO (fusão)
├── GENERATOR_GUIDE.md                # ATUALIZAR paths
├── GRU_SCRAPER_USAGE.md             # ATUALIZAR se necessário
├── QUICKSTART.md                    # ATUALIZAR comandos
├── QUICK_REFERENCE.md               # ATUALIZAR paths/comandos
├── GOOGLE_INDEXING_SETUP.md         # ATUALIZAR sitemap path
├── INDEXER_IMPLEMENTATION_SUMMARY.md # ATUALIZAR paths
├── HISTORICAL_IMPORT_README.md       # ATUALIZAR
├── HISTORICAL_IMPORT_SUMMARY.md      # ATUALIZAR
├── HISTORICAL_IMPORTER_GUIDE.md      # ATUALIZAR
├── IATA_DICTIONARY_GUIDE.md         # ATUALIZAR se necessário
├── IATA_EXPANSION_SUMMARY.md         # ATUALIZAR
├── IMPLEMENTATION_COMPLETE.md        # Manter (histórico)
├── PERPLEXITY_INTEGRATION_SUMMARY.md # Manter
├── VISUAL_GUIDE.md                  # ATUALIZAR paths/UI
└── PHASE1_TRIAGE_AND_CONSOLIDATION_PLAN.md  (este arquivo)
```

---

## 6. Próximo passo

Confirmar se este plano está aprovado para:

1. Executar a Fase 1 (criar `archive/`, mover obsoletos, criar ARCHITECTURE.md e DEPLOY.md, mover originais fusionados para archive, atualizar paths nos demais).  
2. Em seguida, executar a Fase 2 (Perplexity/MCP para SEO e GitHub Actions) e, se desejado, a Fase 3 (README raiz e polimento final).

Se quiser alterar algum item (ex.: manter algum arquivo fora do archive ou não fundir algum dos listados), indique e o plano pode ser ajustado antes da execução.
