# 🎨 Guia do Gerador de Páginas ANAC 400

## 📖 Visão Geral

O **MatchFly Page Generator** é um sistema de geração de páginas estáticas orientado a CRO (Conversion Rate Optimization) que transforma dados de voos com problemas em landing pages otimizadas para conversão e SEO.

## ✨ Características do Template

### 🎯 Template: tier2-anac400.html

**Estilo:** Utilidade Pública (Clean, Oficial)
**Paleta de Cores:**
- Azul Escuro (#1e3a8a) - Brand principal
- Azul Claro (#3b82f6) - Destaques
- Cinza Leve (#f3f4f6) - Background
- Branco - Base

### 📊 Elementos de CRO Implementados

#### 1. **Badge de Frescor de Dados**
```html
<span class="text-xs text-gray-600 font-medium">
    Atualizado há {{ hours_ago }}h
</span>
```
- Cria urgência e confiança
- Atualização automática baseada no timestamp do scraping

#### 2. **H1 de Alto Impacto**
```html
Voo {{ flight_number }} da {{ airline }} foi Cancelado ou Atrasou?
```
- Específico para o voo
- Personalizado por companhia
- Foco na dor do usuário

#### 3. **Auto-Avaliação com Checkboxes Interativos**
```javascript
function checkAllBoxes() {
    // Quando todas as 3 caixas são marcadas:
    // ✅ Adiciona animação pulse no CTA
    // ✅ Mostra mensagem de sucesso
    // ✅ Scroll automático para CTA
}
```

**Checkboxes:**
- [ ] Companhia não ofereceu assistência?
- [ ] Voo cancelado ou atrasado > 4h?
- [ ] Ocorreu nos últimos 2 anos?

**Comportamento:**
- ✅ Compromisso gradual (foot-in-the-door)
- ✅ Animação de pulse quando completo
- ✅ Auto-check se atraso >= 4h

#### 4. **Tabela de Direitos ANAC**
Informação educacional clara:
- ⏱️ 1h: Comunicação
- 🍔 2h: Alimentação
- 🏨 4h: Hospedagem + **Indenização**

#### 5. **CTA Otimizado**
```html
VERIFICAR MINHA INDENIZAÇÃO →
```
- Cor vibrante com contraste
- Largura total no mobile
- Trust badges (100% Seguro, Sem Custos, 97% Sucesso)
- Disclaimer claro

#### 6. **SEO & Schema.org**

**BroadcastEvent Schema:**
```json
{
    "@type": "BroadcastEvent",
    "eventStatus": "EventCancelled",
    "startDate": "{{ departure_time }}",
    "location": "{{ origin }}"
}
```

**FAQPage Schema:**
3 perguntas otimizadas para featured snippets:
1. Como receber indenização ANAC 400?
2. Quanto tempo demora?
3. Preciso pagar algo?

## 🔧 Como Usar o Gerador

### 1️⃣ Configuração Inicial

#### Editar Affiliate Link

**Arquivo:** `src/generator.py`

```python
# Linha ~350
AFFILIATE_LINK = "https://www.compensair.com/compensation?ref=matchfly&flight={flight_number}"
```

⚠️ **IMPORTANTE:** O gerador NÃO executará sem um affiliate link válido!

### 2️⃣ Executar Geração

```bash
# Método 1: Diretamente
cd ~/matchfly
source venv/bin/activate
python3 src/generator.py

# Método 2: Via import
from src.generator import FlightPageGenerator

generator = FlightPageGenerator(
    data_file="data/flights-db.json",
    template_file="src/templates/tier2-anac400.html",
    output_dir="public",
    affiliate_link="https://..."
)

stats = generator.run()
```

### 3️⃣ Verificar Output

```bash
# Listar páginas geradas
ls -la public/

# Abrir no navegador
open public/index.html  # macOS
xdg-open public/index.html  # Linux
start public/index.html  # Windows
```

## 📁 Estrutura de Arquivos Gerados

```
public/
├── index.html                          # Página índice com todos os voos
├── voo-latam-la3090-gru-atrasado.html  # Página individual
├── voo-gol-g31447-gru-cancelado.html
├── voo-azul-ad4123-gru-atrasado.html
└── ...
```

### Formato de Slug

**Padrão:** `voo-{airline}-{flight_number}-{origin}-{status}.html`

**Exemplos:**
- `voo-latam-la3090-gru-atrasado.html`
- `voo-gol-g31447-gru-cancelado.html`
- `voo-azul-ad4123-gru-atrasado.html`

**Otimizações SEO:**
- ✅ Slugify automático (remove acentos, caracteres especiais)
- ✅ Lowercase para consistência
- ✅ Palavras-chave relevantes (voo, airline, número, origem, status)

## 🎨 Variáveis do Template

### Variáveis Obrigatórias

| Variável | Tipo | Descrição | Exemplo |
|----------|------|-----------|---------|
| `flight_number` | string | Número do voo | "LA3090" |
| `airline` | string | Companhia aérea | "LATAM" |
| `status` | string | Status do voo | "Atrasado" |
| `delay_hours` | float | Horas de atraso | 2.5 |
| `hours_ago` | int | Horas desde scraping | 0 |
| `affiliate_link` | string | Link de conversão | "https://..." |

### Variáveis Opcionais

| Variável | Tipo | Padrão | Descrição |
|----------|------|--------|-----------|
| `origin` | string | "GRU" | Aeroporto de origem |
| `destination` | string | "N/A" | Aeroporto de destino |
| `scheduled_time` | string | "N/A" | Horário previsto |
| `actual_time` | string | "N/A" | Horário real |
| `departure_time` | string | now() | Para schema.org |
| `scraped_at` | string | now() | Timestamp do scraping |
| `generated_at` | string | now() | Timestamp da geração |

## 🛡️ Validações Implementadas

### 1. Validação de Affiliate Link

```python
if not self.affiliate_link or self.affiliate_link.strip() == "":
    logger.error("❌ ERRO CRÍTICO: affiliate_link está vazio!")
    return self.stats
```

**Motivo:** Evitar páginas sem monetização.

### 2. Validação de Voo

```python
def validate_flight(self, flight: Dict) -> bool:
    required_fields = ['flight_number', 'airline', 'status']
    for field in required_fields:
        if not flight.get(field):
            return False
    return True
```

**Campos Obrigatórios:**
- `flight_number`
- `airline`
- `status`

### 3. Cálculo de Hours Ago

```python
def calculate_hours_ago(self, scraped_at: str) -> int:
    scraped_dt = datetime.fromisoformat(scraped_at)
    now = datetime.now()
    delta = now - scraped_dt
    hours = int(delta.total_seconds() / 3600)
    return max(0, hours)
```

**Tratamento:**
- Parse flexível de timestamps
- Não retorna valores negativos
- Fallback para 0 em caso de erro

## 📊 Estatísticas de Geração

O gerador fornece estatísticas detalhadas:

```python
{
    'total_flights': 5,
    'pages_generated': 5,
    'skipped_no_affiliate': 0,
    'skipped_invalid': 0,
    'errors': 0
}
```

**Logs Gerados:**
- `generator.log` - Histórico completo de execuções
- Console output - Status em tempo real

## 🎯 Otimizações de CRO

### Psicologia Aplicada

#### 1. **Compromisso Gradual (Foot-in-the-Door)**
Checkboxes criam micro-compromissos antes do CTA principal.

#### 2. **Urgência & Escassez**
- Badge "Atualizado há Xh"
- Status em vermelho (Cancelado/Atrasado)

#### 3. **Prova Social**
- "97% Taxa de Sucesso"
- Trust badges

#### 4. **Redução de Risco**
- "100% Gratuito"
- "Sem custos iniciais"
- "Você só paga se ganhar"

### Mobile-First Design

- ✅ Checkboxes grandes (fácil de tocar)
- ✅ CTA largura total no mobile
- ✅ Espaçamento generoso
- ✅ Fonte legível (>16px)
- ✅ Sticky header

### Performance

- ✅ Tailwind CSS via CDN (cache do navegador)
- ✅ Sem JavaScript pesado
- ✅ HTML estático (rápido)
- ✅ Lazy loading de imagens (se adicionar)

## 🚀 Workflow Completo

### Passo a Passo

```bash
# 1. Executar scraper
python3 run_gru_scraper.py

# Output: data/flights-db.json

# 2. Configurar affiliate link
# Editar src/generator.py linha ~350

# 3. Gerar páginas
python3 src/generator.py

# Output: public/*.html

# 4. Testar localmente
open public/index.html

# 5. Deploy (escolha um):
# - Netlify: arraste pasta public/
# - Vercel: vercel --prod
# - GitHub Pages: git push
# - S3 + CloudFront: aws s3 sync public/ s3://bucket
```

## 📈 Métricas Recomendadas

### Tracking de Conversão

**Adicionar ao template:**

```javascript
// Google Analytics 4
gtag('event', 'click', {
    'event_category': 'CTA',
    'event_label': 'Verificar Indenização',
    'flight_number': '{{ flight_number }}',
    'airline': '{{ airline }}'
});

// Facebook Pixel
fbq('track', 'Lead', {
    flight: '{{ flight_number }}',
    value: 10000,
    currency: 'BRL'
});
```

### A/B Testing Ideas

1. **Headline:**
   - A: "Voo X foi cancelado?"
   - B: "Você perdeu o voo X?"

2. **CTA:**
   - A: "Verificar Indenização"
   - B: "Calcular Minha Compensação"

3. **Cores:**
   - A: Azul profissional
   - B: Verde "dinheiro"

## 🐛 Troubleshooting

### Erro: "affiliate_link está vazio"

**Causa:** AFFILIATE_LINK não configurado

**Solução:**
```python
# src/generator.py, linha ~350
AFFILIATE_LINK = "https://seu-link-aqui.com"
```

### Erro: "Template não encontrado"

**Causa:** Caminho incorreto

**Solução:**
```bash
# Verificar estrutura
ls -la src/templates/tier2-anac400.html
```

### Páginas não geram

**Causa:** Dados inválidos

**Solução:**
```bash
# Verificar JSON
python3 -m json.tool data/flights-db.json

# Verificar campos obrigatórios
cat data/flights-db.json | jq '.flights[] | {flight_number, airline, status}'
```

### Hours_ago sempre 0

**Causa:** Formato de timestamp

**Solução:**
```python
# Verificar formato em flights-db.json
# Deve ser: "2026-01-11T18:34:35.005828"
```

## 📚 Recursos Adicionais

### Referências

- [ANAC Resolução 400](https://www.gov.br/anac/pt-br)
- [Schema.org Event](https://schema.org/Event)
- [Schema.org FAQPage](https://schema.org/FAQPage)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Jinja2 Template Designer](https://jinja.palletsprojects.com/)

### Exemplos de Affiliate Programs

- **CompensAir:** Até 25% de comissão
- **AirHelp:** €25-30 por caso aprovado
- **ClaimCompass:** 20-30% de comissão
- **FlightRight:** Modelo de CPA

## 🎓 Boas Práticas

### DO ✅

- ✅ Sempre configurar affiliate_link
- ✅ Testar páginas localmente antes do deploy
- ✅ Manter dados atualizados (rodar scraper regularmente)
- ✅ Monitorar métricas de conversão
- ✅ Fazer A/B testing de headlines e CTAs
- ✅ Otimizar para mobile-first

### DON'T ❌

- ❌ Gerar páginas sem affiliate link
- ❌ Usar dados desatualizados (> 24h)
- ❌ Ignorar validações de SEO
- ❌ Esquecer de testar em mobile
- ❌ Deploy sem testar localmente
- ❌ Ignorar logs de erro

## 🚀 Próximos Passos

### Melhorias Futuras

1. **Template Variations:**
   - Tier 1: Listagem simples
   - Tier 2: ANAC 400 (atual)
   - Tier 3: História emocional + testemunhos

2. **Personalização:**
   - Detectar cidade do usuário (geo-targeting)
   - Preços dinâmicos baseados em rota
   - Histórico de problemas da companhia

3. **Automação:**
   - Cronjob para scraping + geração automática
   - Webhook para notificações de novos voos
   - Auto-deploy para produção

4. **Analytics:**
   - Dashboard de conversões por voo
   - Heatmaps de cliques
   - Funil de conversão detalhado

---

**Versão:** 1.0.0  
**Última Atualização:** 2026-01-11  
**Autor:** MatchFly Team

