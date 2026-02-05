# Deploy MatchFly – GitHub Pages via pasta `/docs`

**Última atualização:** Fevereiro 2026

O site MatchFly é publicado usando **GitHub Pages** com a pasta **`/docs`** da branch **`main`** como raiz do site. Não há uso de Netlify nem da branch `gh-pages`.

---

## 1. Modelo de deploy

- **Fonte do site:** branch `main`, pasta `docs/`
- **Como o conteúdo chega em `docs/`:**
  - Local: você roda `python src/generator.py`, que escreve em `docs/`
  - CI: o workflow `.github/workflows/update-flights.yml` roda o generator e faz commit + push das alterações em `docs/` na `main`

O GitHub serve tudo que está em `docs/` em `https://<user>.github.io/<repo>/` ou, com domínio custom, em `https://matchfly.org`.

---

## 2. Configuração no GitHub

1. Repositório → **Settings** → **Pages**.
2. Em **Build and deployment**:
   - **Source:** Deploy from a branch
   - **Branch:** `main`
   - **Folder:** `/docs`
3. Salvar. O site passará a ser servido a partir da pasta `docs/`.

---

## 3. Domínio custom (matchfly.org)

Para que o site responda em `https://matchfly.org`:

1. **CNAME no repositório**  
   O generator escreve em `docs/CNAME` o conteúdo `matchfly.org` (uma linha, sem `https://` e sem barra no final). Esse arquivo deve estar em `docs/` e versionado.

2. **DNS no provedor do domínio**  
   Configure um registro **CNAME** (ou A/AAAA conforme a documentação do GitHub) apontando o domínio para o endereço do GitHub Pages (ex.: `<user>.github.io`). Detalhes: [GitHub – Configuring a custom domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site).

3. **HTTPS**  
   O GitHub Pages oferece HTTPS para domínios custom; pode levar alguns minutos até o certificado ser provisionado.

---

## 4. Arquivo `.nojekyll`

O GitHub Pages, por padrão, processa o site com Jekyll. O Jekyll ignora pastas e arquivos que começam com `_`.

- O generator cria um arquivo **vazio** `docs/.nojekyll`.
- Com isso, o Jekyll é desativado e a pasta `docs/` é servida como está (incluindo qualquer conteúdo com `_` no nome no futuro).

---

## 5. Workflow de CI (update-flights.yml)

Fluxo resumido:

| Step | Ação |
|------|------|
| 1 | Checkout do repositório |
| 2 | Setup Python 3.12 (cache pip) |
| 3 | `pip install -r requirements.txt` |
| 4 | `python voos_proximos_finalbuild.py` (sincroniza dados → `data/flights-db.json`) |
| 5 | `python src/generator.py` (gera todo o site em `docs/`) |
| 6 | `git add docs/` → commit (se houver mudanças) → `git push` |

O job usa `permissions: contents: write` para poder fazer push na `main`. O commit só ocorre se houver alterações em `docs/` (`git diff --staged --quiet || git commit ...`).

---

## 6. Como rodar localmente

1. **Gerar o site em `docs/`:**
   ```bash
   python src/generator.py
   ```
2. **Pré-requisito:** existir `data/flights-db.json` (gerado por `voos_proximos_finalbuild.py` ou por import histórico).
3. **Visualizar:** abrir `docs/index.html` no navegador ou servir a pasta `docs/` com um servidor local (ex.: `python -m http.server --directory docs 8000`).

Não é necessário Netlify, Vercel nem branch `gh-pages` para o deploy atual.

---

## 7. Checklist pós-deploy

- [ ] Settings → Pages: Source = branch `main`, folder `/docs`
- [ ] Arquivo `docs/CNAME` existe e contém apenas `matchfly.org`
- [ ] Arquivo `docs/.nojekyll` existe (vazio)
- [ ] Após o workflow rodar, `docs/` contém `index.html`, `sitemap.xml`, `robots.txt`, `404.html` e as subpastas `voo/` e `destino/`
- [ ] Domínio custom configurado no DNS e HTTPS ativo (se usar matchfly.org)
