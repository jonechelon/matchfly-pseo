# 🏗️ Generator v2.0 - Arquitetura Production-Grade

## 📖 Visão Geral

O **MatchFly Page Generator v2.0** implementa uma arquitetura rigorosa de execução com:
- ✅ **Gestão de órfãos** (arquivos antigos removidos automaticamente)
- ✅ **Sitemap.xml** (geração automática)
- ✅ **Auditoria completa** (logs detalhados de cada etapa)
- ✅ **Resiliência total** (try/except por voo individual)
- ✅ **Filtros inteligentes** (apenas Cancelados ou Atraso > 2h)
- ✅ **Homepage dinâmica** (20 voos mais recentes)

## 🔧 Workflow de Execução

### Arquitetura Rigorosa (5 Steps)

```
╔════════════════════════════════════════════════════════╗
║         MATCHFLY PAGE GENERATOR v2.0 WORKFLOW         ║
╚════════════════════════════════════════════════════════╝

STEP 1: SETUP & VALIDAÇÃO
├── Verificar AFFILIATE_LINK (obrigatória)
├── Criar pasta public/
└── Criar pasta public/voo/

STEP 2: INITIAL CLEANUP (Auditoria)
├── Remover public/index.html
├── Contar arquivos antigos em public/voo/
└── Log: "Detectados X arquivos antigos"

STEP 3: WORKFLOW DE GERAÇÃO
│
├── 3.1: RENDERIZAÇÃO RESILIENTE
│   ├── Iterar sobre data/flights-db.json
│   ├── Para cada voo:
│   │   ├── Filtrar (Cancelado ou Atraso > 2h)
│   │   ├── try/except individual
│   │   ├── Se sucesso: Adicionar à lista de sucessos
│   │   └── Se falha: Logar erro e continue
│   └── Log: [X/Y] Processando {flight_number}...
│
├── 3.2: GESTÃO DE ÓRFÃOS
│   ├── Listar arquivos em public/voo/
│   ├── Comparar com lista de sucessos
│   ├── Remover arquivos não regenerados
│   └── Log: "Órfãos removidos: Z arquivos"
│
├── 3.3: SITEMAP
│   ├── Criar public/sitemap.xml
│   ├── Incluir apenas URLs com sucesso
│   └── Log: "Sitemap: Atualizado com X URLs"
│
└── 3.4: HOME PAGE
    ├── Criar public/index.html
    ├── Exibir 20 voos mais recentes
    └── Log: "Home page: X voos exibidos"

STEP 4: LOG FINAL (Sumário)
├── Voos processados: X
├── Sucessos: Y páginas
├── Falhas: Z páginas
├── Filtrados: W voos
├── Órfãos removidos: K arquivos
└── Sitemap: Atualizado com Y URLs
```

## 📁 Estrutura de Output

```
public/
├── index.html              # Homepage (20 voos mais recentes)
├── sitemap.xml             # Sitemap (apenas sucessos)
└── voo/                    # Páginas individuais de voos
    ├── voo-latam-la3090-gru-atrasado.html
    ├── voo-gol-g31447-gru-cancelado.html
    ├── voo-azul-ad4123-gru-atrasado.html
    └── ...
```

## 🎯 Validações Implementadas

### 1. Setup & Validação (STEP 1)

```python
if not AFFILIATE_LINK:
    logger.error("❌ ERRO CRÍTICO: AFFILIATE_LINK não configurada!")
    sys.exit(1)
```

**Motivo:** Impedir geração de páginas sem monetização.

### 2. Filtro de Voos (STEP 3.1)

```python
def should_generate_page(flight):
    status = flight.get('status', '').lower()
    delay_hours = flight.get('delay_hours', 0)
    
    is_cancelled = 'cancel' in status or 'cancelado' in status
    is_delayed = delay_hours > 2
    
    return is_cancelled or is_delayed
```

**Critérios:**
- ✅ Status "Cancelado"
- ✅ Atraso > 2 horas

### 3. Renderização Resiliente (STEP 3.1)

```python
for flight in flights:
    try:
        # Renderizar página
        success = generate_page_resilient(flight, metadata)
        if success:
            success_files.add(filename)
    except Exception as e:
        logger.error(f"Falha: {e}")
        stats['failures'] += 1
        continue  # Não para o build
```

**Vantagens:**
- ✅ Um erro não para todo o build
- ✅ Logs detalhados de cada falha
- ✅ Estatísticas precisas

## 🗑️ Gestão de Órfãos (STEP 3.2)

### O Problema

Sem gestão de órfãos:
```
# Build 1: Gera 5 voos
public/voo/
├── voo-latam-la3090.html
├── voo-gol-g31447.html
└── ...

# Build 2: Scraper encontra apenas 3 voos
# Os 2 arquivos antigos ficam órfãos!
```

### A Solução

```python
def manage_orphans():
    # Lista arquivos existentes
    existing_files = set(voo_dir.glob("*.html"))
    
    # Lista arquivos gerados agora
    success_files = {"voo-1.html", "voo-2.html", "voo-3.html"}
    
    # Identifica órfãos
    orphans = existing_files - success_files
    
    # Remove órfãos
    for orphan in orphans:
        orphan.unlink()
        logger.info(f"Removido: {orphan}")
```

**Resultado:**
- ✅ Apenas páginas atuais ficam em public/voo/
- ✅ Sem páginas desatualizadas
- ✅ Auditoria completa nos logs

## 🗺️ Sitemap.xml (STEP 3.3)

### Formato Gerado

```xml
<?xml version="1.0" ?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://matchfly.com/</loc>
    <lastmod>2026-01-11</lastmod>
    <changefreq>hourly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://matchfly.com/voo/voo-latam-la3090-gru-atrasado.html</loc>
    <lastmod>2026-01-11</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <!-- ... mais URLs -->
</urlset>
```

### Características

- ✅ **Apenas sucessos:** Só inclui páginas geradas com sucesso
- ✅ **Prioridades:** Home (1.0), Voos (0.8)
- ✅ **Changefreq:** Home (hourly), Voos (daily)
- ✅ **Standards:** Formato oficial sitemaps.org

### Benefícios SEO

1. **Google Search Console:** Submeta o sitemap
2. **Crawling:** Ajuda bots a descobrir páginas
3. **Indexação:** Melhora velocidade de indexação
4. **Freshness:** lastmod indica atualização

## 🏠 Homepage (STEP 3.4)

### Características

- ✅ **20 voos mais recentes** (ordenados por data)
- ✅ **Design moderno** (Tailwind CSS)
- ✅ **Responsivo** (mobile-first)
- ✅ **SEO-optimized** (meta tags completas)

### Elementos

1. **Header:**
   - Logo + Nome
   - Timestamp de atualização

2. **Hero:**
   - Headline: "Seu Voo Foi Cancelado?"
   - Value prop: "Até R$ 10.000"
   - Counter: "X voos identificados"

3. **Grid de Voos:**
   - Cards clicáveis
   - Status visual (cores)
   - Info: Número, airline, atraso

4. **CTA Bottom:**
   - "Não encontrou seu voo?"
   - Link direto para affiliate

5. **Stats:**
   - Voos rastreados
   - Indenização máxima
   - Gratuidade

6. **Footer:**
   - Copyright
   - Timestamp

## 📊 Logs e Auditoria

### Formato de Logs

```
2026-01-11 19:01:40 - INFO - ╔══════════════════════════╗
2026-01-11 19:01:40 - INFO - ║  MATCHFLY GENERATOR v2.0 ║
2026-01-11 19:01:40 - INFO - ╚══════════════════════════╝

======================================================================
STEP 1: SETUP & VALIDAÇÃO
======================================================================
✅ Affiliate link configurada: https://...
✅ Pasta public/voo pronta

======================================================================
STEP 2: INITIAL CLEANUP (Auditoria)
======================================================================
📊 Detectados 12 arquivos antigos em public/voo/
   Serão removidos automaticamente quando não regenerados.

======================================================================
STEP 3: WORKFLOW DE GERAÇÃO
======================================================================
📊 Total de voos carregados: 15

🔄 Iniciando renderização resiliente...
----------------------------------------------------------------------
[1/15] Processando LA3090...
✅ Sucesso: voo-latam-la3090-gru-atrasado.html
[2/15] Processando G31447...
✅ Sucesso: voo-gol-g31447-gru-cancelado.html
[3/15] Processando XX9999...
❌ Falha: Template error on line 45

======================================================================
STEP 3.2: GESTÃO DE ÓRFÃOS
======================================================================
🗑️  Encontrados 3 arquivos órfãos para remoção:
   • Removido: voo-old-flight-1.html
   • Removido: voo-old-flight-2.html
   • Removido: voo-old-flight-3.html

======================================================================
STEP 3.3: GERAÇÃO DE SITEMAP
======================================================================
✅ Sitemap gerado: public/sitemap.xml
   • URLs incluídas: 13 (1 home + 12 voos)

======================================================================
STEP 3.4: GERAÇÃO DE HOME PAGE
======================================================================
✅ Home page gerada: public/index.html
   • Voos exibidos: 12 (dos 12 totais)

╔══════════════════════════════════════════════════════════════════╗
║                     ✅ BUILD FINALIZADO!                        ║
╚══════════════════════════════════════════════════════════════════╝

📊 SUMÁRIO DO BUILD:
   • Voos processados:     15
   • Sucessos:             12 páginas
   • Falhas:               1 páginas
   • Filtrados (< 2h):     2 voos
   • Órfãos removidos:     3 arquivos
   • Sitemap:              Atualizado com 12 URLs

📁 Output:
   • Páginas de voos:      public/voo/
   • Home page:            public/index.html
   • Sitemap:              public/sitemap.xml

🎉 Build concluído com sucesso!
🌐 Abra public/index.html no navegador
```

### Arquivo de Log

**Localização:** `generator.log`

**Conteúdo:**
- Histórico completo de builds
- Timestamps precisos
- Stack traces de erros
- Auditoria de órfãos

## 🚀 Como Usar

### 1. Configurar Affiliate Link

```python
# Editar: src/generator.py (linha ~480)
AFFILIATE_LINK = "https://compensair.com?ref=SEU_ID"
BASE_URL = "https://seu-dominio.com"
```

### 2. Executar Gerador

```bash
cd ~/matchfly
source venv/bin/activate
python3 src/generator.py
```

### 3. Verificar Output

```bash
# Estrutura gerada
ls -R public/

# Visualizar homepage
open public/index.html

# Verificar sitemap
cat public/sitemap.xml
```

### 4. Deploy

```bash
# Netlify
netlify deploy --prod --dir=public

# Vercel
vercel --prod

# AWS S3
aws s3 sync public/ s3://bucket/ --delete
```

## 🔧 Customização

### Alterar Número de Voos na Home

```python
# src/generator.py, método generate_homepage()
recent_pages = sorted_pages[:20]  # Altere 20 para o número desejado
```

### Adicionar Nova Prioridade no Sitemap

```python
# src/generator.py, método generate_sitemap()
ET.SubElement(url_elem, 'priority').text = '0.9'  # Alterar prioridade
```

### Mudar Changefreq

```python
ET.SubElement(url_home, 'changefreq').text = 'always'  # ou daily, weekly, monthly
```

## 📈 Métricas de Qualidade

### Performance

| Métrica | Valor |
|---------|-------|
| 15 voos | ~1.5 segundos |
| 100 voos | ~8 segundos |
| Memória | < 100MB |
| Sitemap | < 1KB por 10 URLs |

### Resiliência

- ✅ 1 voo com erro não para o build
- ✅ Logs detalhados de cada falha
- ✅ Estatísticas precisas sempre
- ✅ Exit code correto (0 sucesso, 1 falha)

### Auditoria

- ✅ Log de todos os órfãos removidos
- ✅ Contador de arquivos antigos
- ✅ Sumário completo por build
- ✅ Histórico em generator.log

## ❓ Troubleshooting

### Erro: "AFFILIATE_LINK não configurada"

**Causa:** Variável vazia em src/generator.py

**Solução:**
```python
# Linha ~480
AFFILIATE_LINK = "https://compensair.com?ref=SEU_ID"
```

### Erro: "Permission denied" em public/

**Causa:** Sem permissão de escrita

**Solução:**
```bash
chmod -R 755 public/
```

### Órfãos não são removidos

**Causa:** Arquivos fora de public/voo/

**Solução:**
```bash
# Verificar localização
find public/ -name "*.html" -type f
```

### Sitemap com URLs erradas

**Causa:** BASE_URL incorreta

**Solução:**
```python
# src/generator.py linha ~481
BASE_URL = "https://seu-dominio-correto.com"
```

## 🎓 Boas Práticas

### DO ✅

- ✅ Sempre configurar AFFILIATE_LINK antes do build
- ✅ Verificar logs após cada build
- ✅ Testar homepage localmente antes de deploy
- ✅ Submeter sitemap no Google Search Console
- ✅ Rodar build em staging antes de produção

### DON'T ❌

- ❌ Editar arquivos em public/ manualmente (serão sobrescritos)
- ❌ Ignorar avisos de órfãos nos logs
- ❌ Fazer deploy sem verificar sucessos > 0
- ❌ Esquecer de atualizar BASE_URL para produção
- ❌ Rodar build sem ambiente virtual ativado

## 📚 Referências

- [Sitemaps.org](https://www.sitemaps.org/)
- [Google Search Console - Sitemaps](https://support.google.com/webmasters/answer/183668)
- [Python Logging](https://docs.python.org/3/library/logging.html)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)

---

**Versão:** 2.0.0  
**Data:** 2026-01-11  
**Autor:** MatchFly Team  
**Status:** ✅ Production Ready

