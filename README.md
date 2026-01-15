# MatchFly

## Visão Geral

MatchFly é uma plataforma automatizada de agregação e análise de status de voos, desenvolvida com foco em escalabilidade, manutenibilidade e resolução de problemas via órgãos confiáveis como a ANAC. O sistema realiza web scraping de múltiplas fontes, processa status e gera páginas estáticas otimizadas para SEO.

## Arquitetura

### Estrutura do Projeto

```
matchfly/
├── .github/
│   └── workflows/          # Pipelines CI/CD (GitHub Actions)
├── src/
│   ├── scrapers/           # Módulos de web scraping
│   └── templates/          # Templates Jinja2 para geração de HTML
├── data/                   # Armazenamento de dados processados (JSON)
├── public/                 # Arquivos estáticos gerados
├── requirements.txt        # Dependências Python
└── README.md              # Documentação técnica
```

### Stack Tecnológico

- **Python 3.9+**: Linguagem principal
- **BeautifulSoup4**: Parsing de HTML/XML para web scraping
- **Requests**: Cliente HTTP para requisições web
- **Jinja2**: Engine de templates para geração de HTML
- **Python-Slugify**: Geração de URLs amigáveis (SEO)

## Funcionalidades Principais

### 1. Web Scraping Modular
- Arquitetura baseada em scrapers independentes
- Suporte para múltiplas fontes de dados
- Rate limiting e retry logic integrados
- Tratamento robusto de erros

### 2. Processamento de Dados
- Normalização e validação de dados esportivos
- Armazenamento em JSON estruturado
- Cache inteligente para otimização de performance

### 3. Geração de Páginas Estáticas
- Templates Jinja2 responsivos
- SEO-friendly URLs (usando slugify)
- Otimização para performance web
- Estrutura preparada para CDN

### 4. CI/CD
- Workflows automatizados via GitHub Actions
- Testes automatizados
- Deploy contínuo

## Instalação

### Pré-requisitos

- Python 3.9 ou superior
- pip (gerenciador de pacotes Python)
- Git

### Setup Local

```bash
# Clone o repositório
git clone <repository-url>
cd matchfly

# Crie e ative o ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt
```

## Uso

### Scrapers Disponíveis

#### 🛫 GRU Airport Flight Scraper

Scraper profissional para voos do Aeroporto de Guarulhos com descoberta automática de API.

```bash
# Executar scraper GRU
python3 run_gru_scraper.py

# Ou com exemplos interativos
python3 examples/example_usage.py
```

**Características:**
- ✅ Descoberta inteligente de API endpoints
- ✅ Filtros: Cancelados ou Atrasados > 2h
- ✅ Logging robusto (console + arquivo)
- ✅ Tratamento completo de erros
- ✅ Output: `data/flights-db.json`

**Uso Programático:**

```python
from src.scrapers import GRUFlightScraper

# Criar scraper
scraper = GRUFlightScraper(output_file="data/flights-db.json")

# Executar
scraper.run()

# Ou usar métodos individuais
flights = scraper.fetch_flights()
filtered = scraper.filter_flights(flights)
scraper.save_to_json(filtered)
```

📖 [Documentação Completa do GRU Scraper](docs/GRU_SCRAPER_USAGE.md)

### Executando Scrapers (Exemplo Genérico)

```python
# Exemplo básico de uso
from src.scrapers import match_scraper

# Executar scraping
matches = match_scraper.fetch_matches()
```

### Gerando Páginas

```python
# Exemplo de geração de páginas
from src.templates import renderer

# Renderizar template
renderer.generate_match_page(match_data)
```

## Estrutura de Dados

### Formato JSON (data/)

```json
{
  "match_id": "unique-id",
  "home_team": "Team A",
  "away_team": "Team B",
  "date": "2026-01-11T20:00:00Z",
  "competition": "League Name",
  "status": "scheduled|live|finished"
}
```

## Desenvolvimento

### Boas Práticas

1. **Código Limpo**: Seguir PEP 8 (Python)
2. **Type Hints**: Usar anotações de tipo
3. **Docstrings**: Documentar funções e classes
4. **Testes**: Cobertura mínima de 80%
5. **Git Flow**: Feature branches + Pull Requests

### Estrutura de Commit

```
<tipo>(<escopo>): <descrição curta>

<descrição detalhada opcional>
```

Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Criando um Novo Scraper

```python
# src/scrapers/new_source_scraper.py
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

class NewSourceScraper:
    """Scraper para [Nome da Fonte]."""
    
    BASE_URL = "https://example.com"
    
    def fetch_matches(self) -> List[Dict]:
        """
        Busca partidas da fonte.
        
        Returns:
            Lista de dicionários com dados das partidas
        """
        response = requests.get(self.BASE_URL)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Implementar lógica de scraping
        return matches
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/main.yml
name: CI/CD Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest
```

## Performance

### Otimizações Implementadas

- **Caching**: Redução de requisições redundantes
- **Async I/O**: Para operações de rede (futuro)
- **Lazy Loading**: Carregamento sob demanda
- **Compression**: Gzip para arquivos estáticos

## Segurança

- Validação de input em todos os scrapers
- Sanitização de dados antes do processamento
- Rate limiting para evitar bloqueios
- Sem armazenamento de credenciais em código

## Funcionalidades Implementadas ✅

### 🛫 GRU Airport Flight Scraper
- ✅ Descoberta automática de API endpoints
- ✅ Filtros: Cancelados ou Atrasados > 2h
- ✅ Logging robusto (console + arquivo)
- ✅ Tratamento completo de erros
- ✅ Output estruturado em JSON

### 🎨 Gerador de Páginas Estáticas
- ✅ Template CRO-optimized (tier2-anac400)
- ✅ Validação de affiliate link obrigatória
- ✅ Cálculo automático de "hours_ago"
- ✅ Slugs SEO-friendly
- ✅ Schemas JSON-LD (BroadcastEvent + FAQ)
- ✅ Checkboxes interativos com JavaScript
- ✅ Tabela de direitos ANAC
- ✅ Design mobile-first (Tailwind CSS)

### 📊 Pipeline Completo
- ✅ Script `run_pipeline.sh` (scraping → geração)
- ✅ Exemplos práticos interativos
- ✅ Documentação completa

## Roadmap Futuro

- [ ] Scrapers para outros aeroportos (CGH, BSB, SDU, GIG)
- [ ] Sistema de notificações em tempo real
- [ ] API REST para consumo de dados
- [ ] Dashboard administrativo
- [ ] Templates adicionais (Tier 1, Tier 3)
- [ ] Suporte multi-idioma
- [ ] Mobile app

## Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## Licença

[Definir Licença - MIT, Apache 2.0, etc.]

## Contato

- **Projeto**: MatchFly
- **Maintainer**: [Seu Nome/Equipe]
- **Email**: [contato@matchfly.com]

## Troubleshooting

### Problemas Comuns

**1. Erro de dependências**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**2. Scraper retorna vazio**
- Verificar se o site alvo mudou estrutura HTML
- Confirmar conectividade de rede
- Checar rate limiting

**3. Erro de encoding**
```python
# Use UTF-8 explicitamente
with open('file.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
```

## Status do Projeto

**Versão Atual**: 0.1.0 (Desenvolvimento Inicial)

**Status**: 🚧 Em Desenvolvimento Ativo

