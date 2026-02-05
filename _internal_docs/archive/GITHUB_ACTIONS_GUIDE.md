# 🚀 GitHub Actions - Guia Completo

## 📖 Visão Geral

O workflow **Update Flights & Deploy** automatiza completamente o pipeline MatchFly:

```
Scraper GRU → Generator → Deploy Netlify
```

**Características:**
- ✅ Execução automática a cada 2 horas
- ✅ Trigger manual para testes
- ✅ Cache inteligente (sem commits!)
- ✅ Resiliência total (continua mesmo com scraper offline)
- ✅ Deploy direto para produção

## 🔧 Configuração Inicial

### 1. Secrets do GitHub

Configure as secrets no seu repositório:

**Navegue:** `Settings → Secrets and variables → Actions → New repository secret`

#### Secrets Obrigatórias:

| Secret | Descrição | Como Obter |
|--------|-----------|------------|
| `NETLIFY_AUTH_TOKEN` | Token de autenticação Netlify | [Netlify Dashboard](https://app.netlify.com/user/applications#personal-access-tokens) |
| `NETLIFY_SITE_ID` | ID do site Netlify | Settings → Site details → Site ID |

#### Secrets Opcionais:

| Secret | Descrição | Uso |
|--------|-----------|-----|
| `SLACK_WEBHOOK` | Webhook do Slack | Notificações |
| `DISCORD_WEBHOOK` | Webhook do Discord | Notificações |

### 2. Obter Netlify Tokens

#### **NETLIFY_AUTH_TOKEN**

```bash
# Opção 1: Via Dashboard
1. Acesse: https://app.netlify.com/user/applications
2. Clique em "New access token"
3. Nome: "GitHub Actions MatchFly"
4. Copie o token gerado

# Opção 2: Via CLI
netlify login
netlify token
```

#### **NETLIFY_SITE_ID**

```bash
# Opção 1: Via Dashboard
1. Acesse seu site: https://app.netlify.com/sites/seu-site
2. Settings → Site details
3. Copie "Site ID" (ex: abc123-xyz-456)

# Opção 2: Via CLI
cd ~/matchfly
netlify status
# Procure por "Site Id:"
```

### 3. Adicionar Secrets

```bash
# Via GitHub CLI (recomendado)
gh secret set NETLIFY_AUTH_TOKEN
# Cole o token quando solicitado

gh secret set NETLIFY_SITE_ID
# Cole o site ID quando solicitado

# Verificar
gh secret list
```

Ou manualmente:
1. Vá para `https://github.com/SEU_USER/matchfly/settings/secrets/actions`
2. Click "New repository secret"
3. Name: `NETLIFY_AUTH_TOKEN`
4. Value: Cole seu token
5. Repita para `NETLIFY_SITE_ID`

## 🎯 Workflow Architecture

### Fluxo de Execução

```
╔══════════════════════════════════════════════════════════════╗
║         GITHUB ACTIONS - UPDATE FLIGHTS WORKFLOW            ║
╚══════════════════════════════════════════════════════════════╝

⏰ TRIGGER: Cron (a cada 2h) ou Manual (workflow_dispatch)
│
├─ STEP 1: Checkout Code
│  └─ Shallow clone (fetch-depth: 1)
│
├─ STEP 2: Setup Python 3.9
│  └─ Cache automático de pip
│
├─ STEP 3: Install Dependencies
│  └─ pip install -r requirements.txt
│
├─ STEP 4: Restore Cache
│  ├─ Tenta restaurar data/flights-db.json
│  ├─ Key: matchfly-flights-{run_id}
│  └─ Fallback: matchfly-flights-* (última rodada)
│
├─ STEP 5: Scraper GRU (continue-on-error)
│  ├─ Executa: python3 run_gru_scraper.py
│  ├─ Se SUCESSO: SCRAPER_STATUS=success
│  └─ Se FALHA: SCRAPER_STATUS=failed (continua)
│
├─ STEP 6: Validação de Dados (DECISÃO CRÍTICA)
│  ├─ Scraper OK? → Usar dados frescos
│  ├─ Scraper falhou + Cache existe? → Usar cache
│  └─ Scraper falhou + Sem cache? → ABORTAR BUILD ❌
│
├─ STEP 7: Generator
│  ├─ Executa: python3 src/generator.py
│  ├─ Gera: public/index.html + voo/*.html + sitemap.xml
│  └─ Valida output
│
├─ STEP 8: Deploy Netlify ⭐
│  ├─ Deploy de: ./public
│  ├─ Produção: true
│  ├─ Secrets: NETLIFY_AUTH_TOKEN + NETLIFY_SITE_ID
│  └─ Timeout: 10 minutos
│
├─ STEP 9: Save Cache
│  ├─ SE scraper foi sucesso:
│  └─ Salva data/flights-db.json para próxima rodada
│
└─ STEP 10: Build Summary
   └─ Log completo de estatísticas

📊 RESULTADO:
   ✅ Site atualizado em: https://matchfly.com
   💾 Cache salvo para próxima execução (2h)
```

## 🛡️ Resiliência & Estratégias

### Cenário 1: Scraper Funciona Normalmente ✅

```yaml
Scraper: ✅ Sucesso (5 voos coletados)
Cache: Não necessário
Generator: ✅ Gera 5 páginas
Deploy: ✅ Produção
Cache Save: ✅ Salva para próxima rodada

Resultado: Site atualizado com dados frescos
```

### Cenário 2: Scraper Offline (com cache) ⚠️

```yaml
Scraper: ❌ Falhou (gru.com.br offline)
Cache: ✅ Existe (última execução 2h atrás)
Generator: ✅ Usa dados do cache
Deploy: ✅ Produção (com aviso)
Cache Save: ❌ Não atualiza (dados antigos)

Log: "[SCRAPER OFFLINE] Usando dados de 2 hora(s) atrás"
Resultado: Site permanece online com dados de 2h atrás
```

### Cenário 3: Scraper Offline (sem cache) ❌

```yaml
Scraper: ❌ Falhou
Cache: ❌ Não existe (primeira execução)
Generator: 🚫 Não executado
Deploy: 🚫 Não executado

Resultado: Build abortado para evitar site vazio
Ação: Aguardar próxima execução (2h)
```

## 💾 Cache Strategy - "Clean Git"

### Por Que Usar Cache?

**Problema com Commits:**
```bash
# Commits a cada 2 horas = 12 commits/dia
# Em 1 mês = 360 commits poluindo histórico
# Apenas para atualizar data/flights-db.json

git log --oneline
abc123 Update flights data (19:00)
def456 Update flights data (17:00)
ghi789 Update flights data (15:00)
... (360 commits)
```

**Solução com Cache:**
```yaml
# Cache persiste entre workflows
# SEM commits
# Histórico Git limpo
# Dados disponíveis para fallback
```

### Como Funciona o Cache

#### **Save (após scraper sucesso):**
```yaml
- uses: actions/cache/save@v4
  with:
    path: data/flights-db.json
    key: matchfly-flights-12345
```

#### **Restore (início do workflow):**
```yaml
- uses: actions/cache@v4
  with:
    path: data/flights-db.json
    key: matchfly-flights-${{ github.run_id }}
    restore-keys: |
      matchfly-flights-
```

**Comportamento:**
- Tenta restaurar cache exato (`matchfly-flights-12345`)
- Se não encontrar, usa `restore-keys` (última rodada disponível)
- Se cache não existe, variável `HAS_CACHE=false`

### Vantagens do Cache

| Aspecto | Com Commits | Com Cache |
|---------|-------------|-----------|
| Histórico Git | 🔴 Poluído | ✅ Limpo |
| Performance | 🟡 Clone completo | ✅ Shallow clone |
| Fallback | ❌ Precisa checkout | ✅ Restore automático |
| CI/CD Cost | 🔴 Alto | ✅ Baixo |

## ⏰ Agendamento

### Cron Expression

```yaml
schedule:
  - cron: '0 */2 * * *'
```

**Tradução:** A cada 2 horas, no minuto 0

**Horários (UTC):**
- 00:00, 02:00, 04:00, 06:00, 08:00, 10:00
- 12:00, 14:00, 16:00, 18:00, 20:00, 22:00

**Horários (BRT - UTC-3):**
- 21:00, 23:00, 01:00, 03:00, 05:00, 07:00
- 09:00, 11:00, 13:00, 15:00, 17:00, 19:00

### Alterar Frequência

```yaml
# A cada hora
cron: '0 * * * *'

# A cada 30 minutos
cron: '*/30 * * * *'

# A cada 4 horas
cron: '0 */4 * * *'

# Apenas dias úteis, a cada 2h
cron: '0 */2 * * 1-5'

# Horário específico (ex: 09:00 UTC)
cron: '0 9 * * *'
```

## 🎮 Execução Manual

### Via GitHub UI

1. Vá para: `Actions → Update Flights & Deploy`
2. Click "Run workflow"
3. Selecione branch (main)
4. (Opcional) Marque "Force scraper"
5. Click "Run workflow"

### Via GitHub CLI

```bash
# Execução padrão
gh workflow run update-flights.yml

# Com input (force scraper)
gh workflow run update-flights.yml \
  -f force_scraper=true

# Ver status
gh run list --workflow=update-flights.yml

# Ver logs em tempo real
gh run watch
```

### Via API

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/SEU_USER/matchfly/actions/workflows/update-flights.yml/dispatches \
  -d '{"ref":"main","inputs":{"force_scraper":"false"}}'
```

## 📊 Monitoramento

### Verificar Logs

```bash
# Via GitHub CLI
gh run list --workflow=update-flights.yml --limit 10
gh run view <run_id> --log

# Ver última execução
gh run view --log
```

### Status Badge

Adicione ao README.md:

```markdown
![Update Flights](https://github.com/SEU_USER/matchfly/actions/workflows/update-flights.yml/badge.svg)
```

### Logs Importantes

**Scraper Status:**
```
✅ Scraper executado com sucesso
📊 5 voos coletados
```

**Cache Status:**
```
✅ Cache restaurado com sucesso
📅 Dados do cache têm 2 hora(s)
```

**Generator Status:**
```
✅ Páginas geradas com sucesso
📄 5 páginas de voos
```

**Deploy Status:**
```
✅ Deploy matchfly.com finalizado com sucesso!
💾 Dados persistidos no cache para próxima rodada.
```

**Warning (Scraper Offline):**
```
⚠️ [SCRAPER OFFLINE] Usando dados de 2 hora(s) atrás
⏰ Próxima verificação em 2h
```

## 🚨 Troubleshooting

### Erro: "NETLIFY_AUTH_TOKEN not found"

**Causa:** Secret não configurada

**Solução:**
```bash
gh secret set NETLIFY_AUTH_TOKEN
# Cole o token
```

### Erro: "Build failed: no cache and scraper failed"

**Causa:** Primeira execução + scraper offline

**Solução:**
1. Espere 2h (próxima tentativa automática)
2. OU execute manualmente quando site estiver online
3. OU adicione dados de exemplo em `data/flights-db.json`

### Warning: "Scraper offline, using cache"

**Causa:** Site gru.com.br temporariamente offline

**Ação:** Nenhuma! O workflow usa cache automaticamente.

**Duração:** Dados podem ficar desatualizados por algumas horas até scraper voltar.

### Erro: "Deploy failed: timeout"

**Causa:** Netlify deployment timeout

**Solução:**
```yaml
# Aumentar timeout no workflow
timeout-minutes: 15  # Padrão é 10
```

### Cache Muito Antigo

**Problema:** Cache com dados de 1 semana atrás

**Solução:**
```bash
# Limpar cache via GitHub API
gh api -X DELETE /repos/SEU_USER/matchfly/actions/caches?key=matchfly-flights

# Executar workflow manualmente para criar cache novo
gh workflow run update-flights.yml
```

## 🔔 Notificações (Opcional)

### Slack Integration

```yaml
- name: 🔔 Notify Slack
  if: always()
  run: |
    STATUS="${{ job.status }}"
    COLOR=$( [ "$STATUS" = "success" ] && echo "good" || echo "danger" )
    
    curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
      -H 'Content-Type: application/json' \
      -d '{
        "attachments": [{
          "color": "'$COLOR'",
          "title": "MatchFly Build '$STATUS'",
          "fields": [
            {"title": "Voos", "value": "${{ env.FLIGHT_COUNT }}", "short": true},
            {"title": "Páginas", "value": "${{ env.PAGE_COUNT }}", "short": true}
          ]
        }]
      }'
```

### Discord Integration

```yaml
- name: 🔔 Notify Discord
  if: always()
  run: |
    curl -X POST ${{ secrets.DISCORD_WEBHOOK }} \
      -H 'Content-Type: application/json' \
      -d '{
        "content": "🛫 MatchFly Deploy ${{ job.status }}",
        "embeds": [{
          "title": "Build #${{ github.run_number }}",
          "description": "Voos: ${{ env.FLIGHT_COUNT }}\nPáginas: ${{ env.PAGE_COUNT }}",
          "color": ${{ job.status == 'success' && '65280' || '16711680' }}
        }]
      }'
```

## 📈 Otimizações

### Performance

```yaml
# Cache de dependências pip (já implementado)
- uses: actions/setup-python@v5
  with:
    cache: 'pip'

# Shallow clone (já implementado)
- uses: actions/checkout@v4
  with:
    fetch-depth: 1
```

### Custo (GitHub Actions Minutes)

| Execução | Duração | Minutos/Dia | Minutos/Mês |
|----------|---------|-------------|-------------|
| Sucesso | ~3 min | 36 min | ~1,080 min |
| Com cache | ~2 min | 24 min | ~720 min |

**Free Tier:** 2,000 min/mês (público) ou 3,000 min/mês (privado)

## ✅ Checklist de Deploy

### Antes do Primeiro Deploy:

- [ ] Secrets configuradas (NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID)
- [ ] Workflow file em `.github/workflows/update-flights.yml`
- [ ] Site criado no Netlify
- [ ] Testar workflow manualmente primeiro

### Verificação Pós-Deploy:

- [ ] Workflow executou com sucesso
- [ ] Site acessível em matchfly.com
- [ ] Páginas de voos carregando
- [ ] Sitemap.xml válido
- [ ] Cache salvo para próxima rodada

---

**Versão:** 1.0.0  
**Data:** 2026-01-11  
**Status:** ✅ Production Ready

