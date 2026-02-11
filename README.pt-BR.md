# MatchFly https://matchfly.org

**Monitor de Confiabilidade Aérea e Indenizações**

<div align="center">

**Language / Idioma / Idioma:**

[![English](https://img.shields.io/badge/English-🇬🇧-blue?style=flat-square)](./README.md)
[![Português](https://img.shields.io/badge/Português-🇧🇷-green?style=flat-square)](#português)
[![Español](https://img.shields.io/badge/Español-🇪🇸-red?style=flat-square)](./README.es.md)

</div>

---

## 🇧🇷 Português

MatchFly agrega dados de voos (atrasos e cancelamentos) a partir do Aeroporto de Guarulhos (GRU), gera páginas estáticas otimizadas para SEO e informa passageiros sobre direitos à indenização (ANAC 400 / EC 261), com integração a parceiros de verificação de indenização.

---

## Sobre

MatchFly é uma plataforma automatizada que:

- Consolida dados de voos (scrapers, CSV, dados ANAC)
- Gera um site estático com uma página por voo problemático e por destino
- Oferece interface clara para consulta de status e links para verificação de indenização

O site é publicado em **GitHub Pages** a partir da pasta `docs/` na branch `main`.

---

## UI: Split-Flap (Aeroporto Retrô)

A interface usa um conceito visual **Split-Flap** (painéis tipo aeroporto retrô): cards por cidade com voos atrasados/cancelados, navegação por abas (Cidades, Cancelados, Atrasados) e página customizada 404. O layout é responsivo (Tailwind CSS) e acessível.

---

## Tech Stack

| Camada        | Tecnologia                    |
|---------------|-------------------------------|
| Backend       | Python 3.12                   |
| Templates     | Jinja2                        |
| Estilos       | Tailwind CSS (CDN)            |
| Dados         | JSON (`data/flights-db.json`) |
| Publicação    | GitHub Pages (pasta `/docs`)  |

---

## Como rodar

**Pré-requisito:** ter dados em `data/flights-db.json` (gerado por `voos_proximos_finalbuild.py` ou pelo import histórico).

Gerar o site localmente (saída em `docs/`):

```bash
pip install -r requirements.txt
python src/generator.py
```

Abrir no navegador: `docs/index.html` ou servir a pasta `docs/` com um servidor local (ex.: `python -m http.server --directory docs 8000`).

Para atualizar os dados antes de gerar:

```bash
python voos_proximos_finalbuild.py
python src/generator.py
```

Pipeline completo (scraper + gerador): `./scripts/run_pipeline.sh` (executar na raiz do repositório).

---

## Estrutura do projeto

| Pasta / arquivo   | Descrição |
|-------------------|-----------|
| `src/`            | Código principal: gerador de páginas (`generator.py`), enriquecimento, scrapers e templates Jinja2. |
| `docs/`           | **Saída do gerador** e pasta publicada no GitHub Pages (HTML, sitemap, robots, CNAME, 404). |
| `data/`           | Banco de dados de voos em JSON e arquivos de apoio (ex.: rotas ANAC). |
| `_internal_docs/` | Documentação técnica interna (arquitetura, deploy, guias). |
| `scripts/`        | Scripts de automação e manutenção (ex.: `run_pipeline.sh`). |
| `voos_proximos_finalbuild.py` | Entry point de sincronização de dados (usado pelo CI e localmente). |

---

## Documentação interna

- **Arquitetura e fluxo:** `_internal_docs/ARCHITECTURE.md`
- **Deploy (GitHub Pages, CNAME, workflow):** `_internal_docs/DEPLOY.md`
- Outros guias e referências: pasta `_internal_docs/`

---

## Licença e uso

Consulte o repositório e a documentação interna para detalhes de uso, contribuição e licença.
