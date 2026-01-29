# Google Indexing API - Guia de Configuração

Este guia explica como configurar e usar o script `src/indexer.py` para enviar URLs recém-geradas automaticamente para a Google Indexing API.

## 📋 Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Configuração da Service Account](#configuração-da-service-account)
3. [Instalação de Dependências](#instalação-de-dependências)
4. [Uso Local](#uso-local)
5. [Configuração no GitHub Actions](#configuração-no-github-actions)
6. [Troubleshooting](#troubleshooting)

---

## Pré-requisitos

- Python 3.8+
- Conta Google Cloud Platform (GCP)
- Projeto no Google Cloud Console
- Google Search Console configurado para o domínio

---

## Configuração da Service Account

### Passo 1: Criar Service Account no Google Cloud Console

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Selecione seu projeto (ou crie um novo)
3. Navegue até **IAM & Admin** → **Service Accounts**
4. Clique em **Create Service Account**
5. Preencha:
   - **Name**: `matchfly-indexing-service`
   - **Description**: `Service account para Google Indexing API`
6. Clique em **Create and Continue**

### Passo 2: Conceder Permissões

1. Na tela de **Grant this service account access to project**:
   - Role: **Editor** (ou mínimo necessário)
2. Clique em **Continue** → **Done**

### Passo 3: Criar e Baixar Chave JSON

1. Na lista de Service Accounts, clique na conta criada
2. Vá para a aba **Keys**
3. Clique em **Add Key** → **Create new key**
4. Selecione **JSON**
5. Clique em **Create**
6. O arquivo JSON será baixado automaticamente

### Passo 4: Habilitar Google Indexing API

1. No Google Cloud Console, vá para **APIs & Services** → **Library**
2. Busque por **"Indexing API"**
3. Clique em **Google Indexing API**
4. Clique em **Enable**

### Passo 5: Verificar Propriedade no Google Search Console

1. Acesse o [Google Search Console](https://search.google.com/search-console)
2. Selecione sua propriedade (domínio)
3. Vá para **Settings** → **Users and permissions**
4. Adicione o email da Service Account (formato: `nome@projeto.iam.gserviceaccount.com`)
5. Conceda permissão de **Owner** ou **Full**

### Passo 6: Salvar Credenciais Localmente

1. Renomeie o arquivo JSON baixado para `service_account.json`
2. Crie o diretório `credentials/` na raiz do projeto (se não existir)
3. Mova o arquivo para `credentials/service_account.json`

```bash
mkdir -p credentials
mv ~/Downloads/seu-projeto-xxxxx.json credentials/service_account.json
```

**⚠️ IMPORTANTE:** O arquivo `credentials/` está no `.gitignore` e **NÃO** será commitado no Git.

---

## Instalação de Dependências

As dependências já estão listadas no `requirements.txt`. Para instalar:

```bash
pip install -r requirements.txt
```

Ou instale apenas as dependências do Google Indexing API:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 requests
```

---

## Uso Local

### Execução Manual

Após gerar as páginas com `src/generator.py`, execute o indexer:

```bash
python3 src/indexer.py
```

### Execução via Pipeline

O script `run_pipeline.sh` já inclui a indexação automaticamente:

```bash
./run_pipeline.sh
```

O script verifica se o arquivo de credenciais existe antes de tentar indexar. Se não existir, ele apenas avisa e continua o pipeline normalmente.

### Comportamento do Script

- ✅ **Lê** `public/sitemap.xml` gerado pelo `generator.py`
- ✅ **Filtra** apenas URLs de voos (contém `/voo/`)
- ✅ **Autentica** usando `credentials/service_account.json`
- ✅ **Envia** requisições `URL_UPDATED` para cada URL
- ✅ **Rate Limiting**: 100ms entre requisições, 1s entre lotes de 100 URLs
- ✅ **Tratamento de Erros**: Continua mesmo se algumas URLs falharem
- ✅ **Logging**: Gera `indexer.log` com detalhes

### Exemplo de Saída

```
╔════════════════════════════════════════════════════════════════════╗
║               🔍 GOOGLE INDEXING API - MatchFly                   ║
╚════════════════════════════════════════════════════════════════════╝

======================================================================
STEP 1: LEITURA DO SITEMAP
======================================================================
📖 Lendo sitemap: public/sitemap.xml
✅ 25 URLs de voos extraídas do sitemap
📊 Total de URLs para indexar: 25

======================================================================
STEP 2: AUTENTICAÇÃO
======================================================================
🔐 Autenticando com Service Account: credentials/service_account.json
✅ Autenticação bem-sucedida

======================================================================
STEP 3: INDEXAÇÃO DE URLs
======================================================================
📤 Iniciando indexação de 25 URLs...
   Rate limiting: 0.1s entre requisições
   Lotes de até 100 URLs

[1/25] Indexando: https://matchfly.org/voo/voo-latam-la3090-gru-atrasado.html
✅ URL indexada: https://matchfly.org/voo/voo-latam-la3090-gru-atrasado.html
[2/25] Indexando: https://matchfly.org/voo/voo-gol-g31447-gru-cancelado.html
...

╔════════════════════════════════════════════════════════════════════╗
║                    ✅ INDEXAÇÃO FINALIZADA!                       ║
╚════════════════════════════════════════════════════════════════════╝

📊 SUMÁRIO:
   • URLs processadas:  25
   • Sucessos:          25
   • Falhas:            0

🎉 URLs enviadas com sucesso para a Google Indexing API!
```

---

## Configuração no GitHub Actions

### Passo 1: Criar GitHub Secret

1. No seu repositório GitHub, vá para **Settings** → **Secrets and variables** → **Actions**
2. Clique em **New repository secret**
3. Configure:
   - **Name**: `GOOGLE_SERVICE_ACCOUNT_JSON`
   - **Secret**: Cole o conteúdo completo do arquivo `service_account.json`
4. Clique em **Add secret**

### Passo 2: Verificar Workflow

O workflow `.github/workflows/update-flights.yml` já está configurado para:

1. ✅ Instalar dependências do Google Auth
2. ✅ Criar arquivo de credenciais a partir do secret
3. ✅ Executar o indexer após gerar as páginas

**O workflow só executa a indexação se o secret estiver configurado.** Se não estiver, o pipeline continua normalmente sem erros.

### Estrutura do Workflow

```yaml
- name: 3. Setup Google Service Account (Optional)
  if: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON != '' }}
  run: |
    mkdir -p credentials
    echo "${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}" > credentials/service_account.json

- name: 4. Index URLs to Google (Optional)
  if: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON != '' }}
  run: |
    python src/indexer.py || echo "⚠️  Indexação falhou ou não configurada (continuando...)"
```

---

## Troubleshooting

### Erro: "Arquivo de credenciais não encontrado"

**Causa:** O arquivo `credentials/service_account.json` não existe.

**Solução:**
1. Verifique se o arquivo foi criado corretamente
2. Verifique o caminho: deve ser `credentials/service_account.json` na raiz do projeto
3. O script continuará normalmente sem indexar (não quebra o pipeline)

---

### Erro: "Invalid credentials" ou "Authentication failed"

**Causa:** O arquivo JSON está corrompido ou inválido.

**Solução:**
1. Verifique se o arquivo JSON está completo e válido
2. Tente abrir o JSON em um editor para validar a sintaxe
3. Refaça o download da chave no Google Cloud Console

---

### Erro: "Permission denied" ou "403 Forbidden"

**Causa:** A Service Account não tem permissão no Google Search Console.

**Solução:**
1. Acesse o Google Search Console
2. Vá para **Settings** → **Users and permissions**
3. Adicione o email da Service Account (formato: `nome@projeto.iam.gserviceaccount.com`)
4. Conceda permissão de **Owner** ou **Full**

---

### Erro: "API not enabled"

**Causa:** A Google Indexing API não está habilitada no projeto.

**Solução:**
1. Acesse o Google Cloud Console
2. Vá para **APIs & Services** → **Library**
3. Busque por **"Indexing API"**
4. Clique em **Enable**

---

### Erro: "Rate limit exceeded" (429)

**Causa:** Muitas requisições em pouco tempo.

**Solução:**
- O script já implementa rate limiting automático
- Se persistir, aumente os delays em `src/indexer.py`:
  ```python
  DELAY_BETWEEN_REQUESTS = 0.2  # Aumentar para 200ms
  DELAY_BETWEEN_BATCHES = 2.0   # Aumentar para 2 segundos
  ```

---

### URLs não aparecem no Google Search Console

**Causa:** A indexação pode levar alguns minutos ou horas.

**Solução:**
1. Aguarde algumas horas após a execução
2. Verifique no Google Search Console → **URL Inspection**
3. Use a ferramenta "Request Indexing" manualmente para testar
4. Verifique os logs em `indexer.log` para confirmar que as requisições foram enviadas

---

## Limites e Cotas da API

- **Máximo de requisições por dia**: Depende do seu plano do Google Cloud
- **Rate limiting**: O script implementa delays automáticos
- **Tipos de notificação**: `URL_UPDATED` (para novas/atualizadas) ou `URL_DELETED` (para removidas)

---

## Segurança

✅ **O arquivo `credentials/` está no `.gitignore`** - nunca será commitado
✅ **GitHub Secrets são criptografados** - seguros para uso em workflows
✅ **Service Account tem permissões mínimas** - apenas Indexing API
✅ **Script verifica credenciais antes de usar** - não quebra o pipeline se faltar

---

## Referências

- [Google Indexing API Documentation](https://developers.google.com/search/apis/indexing-api/v3/using-api)
- [Service Account Setup Guide](https://cloud.google.com/iam/docs/service-accounts)
- [Google Search Console](https://search.google.com/search-console)

---

## Suporte

Se encontrar problemas, verifique:
1. Logs em `indexer.log`
2. Logs do GitHub Actions (se executando no CI/CD)
3. Status da API no Google Cloud Console
4. Permissões no Google Search Console

---

**Última atualização:** 2026-01-22
