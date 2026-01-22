# 🎨 Guia Visual - Historical Importer

## 📺 O Que Você Verá na Tela

### 1️⃣ Executando a Importação

```bash
$ python run_historical_import.py
```

**Saída Esperada**:

```
╔════════════════════════════════════════════════════════════════════╗
║               🔄 MATCHFLY - IMPORTAÇÃO HISTÓRICA                  ║
╚════════════════════════════════════════════════════════════════════╝

Este script vai:
  1. Importar dados históricos da ANAC (últimos 30 dias)
  2. Gerar páginas HTML com os dados importados
  3. Validar o resultado

Deseja continuar? [S/n]: s

======================================================================
🚀 STEP 1: Importando dados históricos da ANAC
======================================================================


╔════════════════════════════════════════════════════════════════════╗
║            🚀 MATCHFLY HISTORICAL IMPORTER - ANAC VRA             ║
╚════════════════════════════════════════════════════════════════════╝

🎯 Configuração:
   • Aeroporto:      SBGR (Guarulhos)
   • Atraso mínimo:  15 minutos
   • Período:        Últimos 30 dias
   • Output:         data/flights-db.json

======================================================================
STEP 1: CARREGANDO BANCO DE DADOS EXISTENTE
======================================================================
📚 Voos existentes carregados: 2

======================================================================
STEP 2: IDENTIFICANDO ARQUIVOS DA ANAC
======================================================================
🔍 Identificando arquivos ANAC disponíveis...
📅 Períodos a buscar: 202601, 202512
   • https://sistemas.anac.gov.br/.../VRA_202601.csv
   • https://sistemas.anac.gov.br/.../VRA_202512.csv

======================================================================
STEP 3: DOWNLOAD E PROCESSAMENTO
======================================================================
📥 Baixando: https://sistemas.anac.gov.br/.../VRA_202601.csv
✅ Download concluído: VRA_202601.csv (45.32 MB)
📊 Processando: VRA_202601.csv
   ✅ Encoding detectado: latin-1
   📈 Total de linhas: 123,456
   🔑 Colunas identificadas: ['airline_code', 'flight_number', ...]
   🛫 Voos de SBGR: 8,234
   ⏱️  Calculando atrasos...
   ✅ Voos atrasados (>15min): 1,456

📥 Baixando: https://sistemas.anac.gov.br/.../VRA_202512.csv
✅ Download concluído: VRA_202512.csv (48.91 MB)
📊 Processando: VRA_202512.csv
   ✅ Encoding detectado: latin-1
   📈 Total de linhas: 134,567
   🔑 Colunas identificadas: ['airline_code', 'flight_number', ...]
   🛫 Voos de SBGR: 9,123
   ⏱️  Calculando atrasos...
   ✅ Voos atrasados (>15min): 1,234

======================================================================
STEP 4: MESCLANDO COM BANCO DE DADOS
======================================================================
🔄 Mesclando 2,690 novos voos com banco existente...
✅ Banco de dados atualizado: 2,690 novos voos adicionados
   Total no banco: 2,692 voos

======================================================================
STEP 5: LIMPEZA
======================================================================
🧹 Arquivos temporários removidos

╔════════════════════════════════════════════════════════════════════╗
║                     ✅ IMPORTAÇÃO FINALIZADA!                     ║
╚════════════════════════════════════════════════════════════════════╝

📊 SUMÁRIO DA IMPORTAÇÃO:
   • Arquivos baixados:        2
   • Total de linhas lidas:    258,023
   • Voos de SBGR:             17,357
   • Voos com atraso >15min:   2,690
   • Voos importados (novos):  2,690
   • Duplicatas ignoradas:     0
   • Erros:                    12

📁 Banco de dados: data/flights-db.json

🎉 SUCESSO! Dados históricos importados com sucesso!
🚀 Execute python src/generator.py para gerar as páginas.
🔔 Som de sucesso tocado!


======================================================================
🚀 STEP 2: Gerando páginas HTML
======================================================================


╔════════════════════════════════════════════════════════════════════╗
║               🚀 MATCHFLY PAGE GENERATOR v2.0                     ║
╚════════════════════════════════════════════════════════════════════╝


======================================================================
STEP 1: SETUP & VALIDAÇÃO
======================================================================
✅ Affiliate link configurada: https://www.airhelp.com/...
✅ Pasta public/voo pronta

======================================================================
STEP 2: INITIAL CLEANUP (Auditoria)
======================================================================
🗑️  Removido: public/index.html (será regenerado)
📊 Detectados 2 arquivos antigos em public/voo/
   Serão removidos automaticamente quando não regenerados.

======================================================================
STEP 3: WORKFLOW DE GERAÇÃO
======================================================================
📊 Total de voos carregados: 2692

🔄 Iniciando renderização resiliente...
----------------------------------------------------------------------
[1/2692] Processando 1234...
✅ Sucesso: voo-gol-1234-gru-atrasado.html
[2/2692] Processando 5678...
✅ Sucesso: voo-azul-5678-gru-cancelado.html
[3/2692] Processando 9012...
✅ Sucesso: voo-latam-9012-gru-atrasado.html
...
[2690/2692] Processando 4567...
✅ Sucesso: voo-gol-4567-gru-atrasado.html
[2691/2692] Processando 8901...
✅ Sucesso: voo-azul-8901-gru-atrasado.html
[2692/2692] Processando 2345...
✅ Sucesso: voo-latam-2345-gru-cancelado.html

======================================================================
STEP 3.2: GESTÃO DE ÓRFÃOS
======================================================================
🗑️  Encontrados 2 arquivos órfãos para remoção:
   • Removido: voo-air-france-0459-gru-atrasado.html
   • Removido: voo-klm-0792-gru-atrasado.html

======================================================================
STEP 3.3: GERAÇÃO DE SITEMAP
======================================================================
✅ Sitemap gerado: public/sitemap.xml
   • URLs incluídas: 2691 (1 home + 2690 voos)

======================================================================
STEP 3.4: GERAÇÃO DE HOME PAGE
======================================================================
✅ Home page gerada: public/index.html
   • Voos exibidos: 20 (dos 2690 totais)
   • Growth Variables:
     - Heróis (social proof): 4868
     - Gate context: Portão B12
     - UTM suffix: ?utm_source=hero_gru

╔════════════════════════════════════════════════════════════════════╗
║                       ✅ BUILD FINALIZADO!                        ║
╚════════════════════════════════════════════════════════════════════╝

📊 SUMÁRIO DO BUILD:
   • Voos processados:     2692
   • Sucessos:             2690 páginas
   • Falhas:               2 páginas
   • Filtrados (< 15min):  0 voos
   • Órfãos removidos:     2 arquivos
   • Sitemap:              Atualizado com 2690 URLs

📁 Output:
   • Páginas de voos:      public/voo/
   • Home page:            public/index.html
   • Sitemap:              public/sitemap.xml

🎉 Build concluído com sucesso!
🌐 Abra public/index.html no navegador

✅ MatchFly: Dicionário IATA expandido com sucesso!


======================================================================
🔍 STEP 3: Validando resultado
======================================================================

✅ Validação concluída!

📊 Resultado:
   • Páginas de voos geradas: 2690
   • Index.html: ✓
   • Sitemap.xml: ✓

🎉 SUCESSO! Importação e geração concluídas!

🌐 Para visualizar:
   open public/index.html

📦 Para fazer deploy:
   git add .
   git commit -m "feat: importar dados históricos ANAC"
   git push

```

---

## 🗂️ Estrutura de Arquivos Gerados

### Antes da Importação:

```
data/
  └── flights-db.json (2 voos)

public/
  ├── index.html
  ├── sitemap.xml
  └── voo/
      ├── voo-air-france-0459-gru-atrasado.html
      └── voo-klm-0792-gru-atrasado.html
```

### Depois da Importação:

```
data/
  └── flights-db.json (2.692 voos) ← ✨ Atualizado!

public/
  ├── index.html ← ✨ Regenerado!
  ├── sitemap.xml ← ✨ Atualizado com 2.690 URLs!
  └── voo/
      ├── voo-gol-1234-gru-atrasado.html ← 🆕 Novo!
      ├── voo-gol-1235-gru-atrasado.html ← 🆕 Novo!
      ├── voo-azul-5678-gru-cancelado.html ← 🆕 Novo!
      ├── voo-azul-5679-gru-atrasado.html ← 🆕 Novo!
      ├── voo-latam-9012-gru-atrasado.html ← 🆕 Novo!
      ├── voo-latam-9013-gru-atrasado.html ← 🆕 Novo!
      └── ... (2.690 páginas HTML!) ← 🆕 Novo!

historical_importer.log ← 🆕 Log detalhado
```

---

## 📄 Exemplo de Arquivo `flights-db.json` Atualizado

### Antes (2 voos):

```json
{
  "flights": [
    {
      "flight_number": "0459",
      "airline": "Air France",
      "status": "Atrasado",
      "scheduled_time": "20:40",
      "actual_time": "22:40",
      "delay_hours": 2.0,
      "delay_min": 120,
      "origin": "GRU",
      "destination": "Paris",
      "numero": "0459",
      "companhia": "Air France",
      "horario": "20:40"
    },
    {
      "flight_number": "0792",
      "airline": "KLM",
      "status": "Atrasado",
      "scheduled_time": "21:00",
      "actual_time": "21:25",
      "delay_hours": 0.42,
      "delay_min": 25,
      "origin": "GRU",
      "destination": "Amsterdã",
      "numero": "0792",
      "companhia": "KLM",
      "horario": "21:00"
    }
  ],
  "metadata": {
    "scraped_at": "2026-01-12T17:45:15.777435+00:00",
    "source": "playwright_intercept:GetVoos"
  }
}
```

### Depois (2.692 voos):

```json
{
  "flights": [
    {
      "flight_number": "1234",
      "airline": "GOL",
      "status": "Atrasado",
      "scheduled_time": "08:30",
      "actual_time": "09:15",
      "delay_hours": 0.75,
      "delay_min": 45,
      "origin": "GRU",
      "destination": "Rio de Janeiro",
      "numero": "1234",
      "companhia": "GOL",
      "horario": "08:30",
      "scheduled_date": "2025-12-15",
      "actual_date": "2025-12-15"
    },
    {
      "flight_number": "5678",
      "airline": "AZUL",
      "status": "Cancelado",
      "scheduled_time": "10:00",
      "actual_time": "10:00",
      "delay_hours": 0,
      "delay_min": 0,
      "origin": "GRU",
      "destination": "Brasília",
      "numero": "5678",
      "companhia": "AZUL",
      "horario": "10:00",
      "scheduled_date": "2025-12-16",
      "actual_date": "2025-12-16"
    },
    // ... +2.688 voos
  ],
  "metadata": {
    "last_import": "2026-01-12T10:30:15",
    "source": "anac_vra_historical",
    "total_flights": 2692,
    "import_stats": {
      "downloaded_files": 2,
      "total_rows": 258023,
      "filtered_sbgr": 17357,
      "delayed_flights": 2690,
      "imported": 2690,
      "duplicates": 0,
      "errors": 12
    }
  }
}
```

---

## 🌐 Exemplo de `index.html` Gerado

Quando você abrir `public/index.html`, verá:

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│              ✈️ MatchFly - Voos com Problemas               │
│                                                              │
│        Verifique se você tem direito a indenização          │
│                    de até R$ 10.000                          │
│                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ GOL 1234           │  │ AZUL 5678           │          │
│  │ Atrasado           │  │ Cancelado           │          │
│  │ ⏱️ Atraso: 0.75h   │  │ ⏱️ Cancelado        │          │
│  │ 🔗 Ver detalhes → │  │ 🔗 Ver detalhes →  │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ LATAM 9012         │  │ GOL 3456            │          │
│  │ Atrasado           │  │ Atrasado            │          │
│  │ ⏱️ Atraso: 1.2h    │  │ ⏱️ Atraso: 0.5h     │          │
│  │ 🔗 Ver detalhes → │  │ 🔗 Ver detalhes →  │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                              │
│  ... (20 voos mais recentes exibidos)                       │
│                                                              │
│  Gerado em: 12/01/2026 10:45                                │
│  Total de voos: 2690                                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Exemplo de `sitemap.xml` Gerado

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://matchfly.org/</loc>
    <lastmod>2026-01-12</lastmod>
    <changefreq>hourly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://matchfly.org/voo/voo-gol-1234-gru-atrasado.html</loc>
    <lastmod>2026-01-12</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://matchfly.org/voo/voo-azul-5678-gru-cancelado.html</loc>
    <lastmod>2026-01-12</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <!-- ... +2.688 URLs -->
</urlset>
```

---

## 📝 Exemplo de Página de Voo Individual

Quando você abrir `public/voo/voo-gol-1234-gru-atrasado.html`:

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│        🛫 Voo GOL 1234 - Guarulhos → Rio de Janeiro         │
│                                                              │
│  ⚠️ Status: Atrasado (45 minutos)                           │
│                                                              │
│  📅 Data: 15/12/2025                                         │
│  ⏰ Previsto: 08:30                                          │
│  ⏰ Real: 09:15                                              │
│  ⏱️ Atraso: 45 minutos (0.75h)                              │
│                                                              │
│  ✈️ Origem: GRU (Guarulhos)                                 │
│  🏙️ Destino: Rio de Janeiro                                 │
│  🏢 Companhia: GOL                                           │
│                                                              │
│  ┌────────────────────────────────────────────────┐        │
│  │                                                │        │
│  │  💰 Você pode ter direito a indenização       │        │
│  │      de até R$ 10.000!                         │        │
│  │                                                │        │
│  │  📋 Regulamentação: ANAC 400                   │        │
│  │  (voo nacional)                                │        │
│  │                                                │        │
│  │  [Verificar meu direito agora →]              │        │
│  │  ↑ Link para AirHelp com dados pré-preenchidos│        │
│  │                                                │        │
│  └────────────────────────────────────────────────┘        │
│                                                              │
│  📊 Informações reportadas há 2 horas                        │
│  🔔 Última atualização: 12/01/2026 às 10:45                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎯 Métricas de Sucesso

### SEO Impact

**Antes**:
- 2-3 páginas indexáveis
- Pouco conteúdo
- Sitemap com 3 URLs

**Depois**:
- 2.690 páginas indexáveis! 🎉
- Conteúdo rico e único por voo
- Sitemap com 2.691 URLs
- Melhor cobertura de long-tail keywords

### User Experience

**Antes**:
- Apenas voos ativos no momento
- Informação limitada

**Depois**:
- Histórico completo de 30 dias
- Mais chances do usuário encontrar seu voo
- Mais páginas de entrada via Google

### Monetização

**Antes**:
- 2-3 oportunidades de conversão

**Depois**:
- 2.690 oportunidades de conversão! 🎉
- Link de afiliado em cada página
- Dados pré-preenchidos no funil (↑ conversão)

---

## 🚀 Comandos Rápidos

```bash
# Importação completa (recomendado)
python run_historical_import.py

# Ou manual
python src/historical_importer.py  # Importar
python src/generator.py            # Gerar

# Visualizar
open public/index.html

# Testar
pytest tests/test_historical_importer.py -v

# Ver logs
tail -f historical_importer.log
tail -f generator.log
```

---

## 🎉 Resultado Final

```
ANTES: 3 páginas HTML 😐
DEPOIS: 2.690 páginas HTML! 🚀🎉

ANTES: Sitemap com 3 URLs 😐
DEPOIS: Sitemap com 2.691 URLs! 🚀🎉

ANTES: Conteúdo limitado 😐
DEPOIS: Base robusta de conteúdo SEO! 🚀🎉
```

---

**🔔 Som de sucesso tocado ao finalizar!**

*Glass.aiff - o som de vitória do macOS* 🎵

---

**Desenvolvido com ❤️ pela equipe MatchFly**

*12 de Janeiro de 2026*
