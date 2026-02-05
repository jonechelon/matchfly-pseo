# 🏗️ MatchFly Architecture: Current vs. Target State

## Configuration Comparison Table

| Component | Current State | Target State (Release 2.0) | Status |
|-----------|--------------|---------------------------|---------|
| **Generator Output** | `public/` | `docs/` | ❌ MISMATCH |
| **Workflow Deploy Source** | `./public` | `./docs` | ❌ MISMATCH |
| **Deploy Method** | `gh-pages` branch (legacy) | Direct commit to `main` | ❌ INCOMPATIBLE |
| **GitHub Pages Source** | Branch: `gh-pages` / Folder: `/` | Branch: `main` / Folder: `/docs` | ❌ NOT CONFIGURED |
| **CNAME Location** | Generated in `gh-pages` by workflow | Must exist in `/workspace/docs/CNAME` | ❌ MISSING |
| **.nojekyll** | Not generated | Must exist in output directory | ⚠️ MISSING |
| **404.html** | Not generated | Should exist in output directory | ⚠️ MISSING |
| **Workflow Permissions** | `contents: write` ✅ | `contents: write` ✅ | ✅ CORRECT |
| **Domain in Workflow** | `cname: matchfly.org` ✅ | `cname: matchfly.org` ✅ | ✅ CORRECT |
| **Push Trigger** | Only `schedule` + `workflow_dispatch` | Should include `push: [main]` | ⚠️ MISSING |

---

## Visual Flow Diagrams

### Current Architecture (Using gh-pages branch)

```
┌─────────────────────────────────────────────────────────────┐
│ GitHub Actions Workflow                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Scraper runs → data/flights-db.json                     │
│  2. Generator runs → public/*.html                          │
│  3. peaceiris/actions-gh-pages@v3                           │
│     ├─ publish_dir: ./public                                │
│     ├─ cname: matchfly.org                                  │
│     └─ Deploy to orphan branch: gh-pages                    │
│                                                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  gh-pages branch │  ◄─── GitHub Pages serves from here
         ├─────────────────┤
         │ index.html       │
         │ CNAME (auto)     │
         │ voo/*.html       │
         │ sitemap.xml      │
         └─────────────────┘
```

**Issues:**
- ❌ Separate branch complicates version control
- ❌ Can't easily inspect deployed files in main branch
- ❌ Incompatible with `/docs` folder strategy

---

### Target Architecture (Using /docs folder)

```
┌─────────────────────────────────────────────────────────────┐
│ GitHub Actions Workflow                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Scraper runs → data/flights-db.json                     │
│  2. Generator runs → docs/*.html                            │
│  3. Git commit & push                                       │
│     ├─ git add docs/                                        │
│     ├─ git commit -m "chore: update site [skip ci]"        │
│     └─ git push origin main                                 │
│                                                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │   main branch    │
         ├─────────────────┤
         │ src/             │
         │ data/            │
         │ docs/            │  ◄─── GitHub Pages serves from here
         │  ├─ index.html   │
         │  ├─ CNAME        │
         │  ├─ .nojekyll    │
         │  ├─ 404.html     │
         │  ├─ voo/*.html   │
         │  └─ sitemap.xml  │
         └─────────────────┘
```

**Benefits:**
- ✅ Single branch (simpler mental model)
- ✅ Deployed files visible in repository
- ✅ Easier rollback (git revert)
- ✅ Native GitHub Pages support

---

## File Structure Comparison

### Current State
```
/workspace/
├── .github/workflows/update-flights.yml  (deploys from public/)
├── src/generator.py                      (outputs to public/)
├── public/                               (generated, git-ignored)
│   ├── index.html
│   ├── voo/*.html
│   └── sitemap.xml
└── docs/                                 (documentation only)
    ├── GENERATOR_GUIDE.md
    ├── GITHUB_ACTIONS_GUIDE.md
    └── ...markdown files...
```

**After workflow runs:**
- `public/` folder has HTML (but is git-ignored)
- Workflow pushes to `gh-pages` branch (separate from main)
- GitHub Pages serves from `gh-pages` branch

---

### Target State
```
/workspace/
├── .github/workflows/update-flights.yml  (deploys from docs/)
├── src/generator.py                      (outputs to docs/)
├── public/                               (deprecated, can be removed)
└── docs/                                 (generated site + docs)
    ├── index.html                        ◄─── Generated by generator.py
    ├── CNAME                             ◄─── matchfly.org
    ├── .nojekyll                         ◄─── Prevents Jekyll processing
    ├── 404.html                          ◄─── Custom error page
    ├── voo/*.html                        ◄─── Flight pages
    ├── sitemap.xml                       ◄─── SEO
    ├── robots.txt                        ◄─── SEO
    └── [documentation .md files]         ◄─── Keep existing docs
```

**After workflow runs:**
- `docs/` folder has HTML (committed to main branch)
- No separate `gh-pages` branch needed
- GitHub Pages serves from `main` branch `/docs` folder

---

## Migration Checklist

### Step 1: Update Generator
- [ ] Edit `src/generator.py` line 672
  ```python
  # Before
  output_dir: str = "public",
  
  # After
  output_dir: str = "docs",
  ```

- [ ] Add .nojekyll generation in generator
  ```python
  (self.output_dir / ".nojekyll").touch()
  ```

### Step 2: Create CNAME
- [ ] Create file `/workspace/docs/CNAME`
  ```
  matchfly.org
  ```

### Step 3: Update Workflow
- [ ] Edit `.github/workflows/update-flights.yml`
  ```yaml
  # Remove lines 49-59 (peaceiris/actions-gh-pages step)
  
  # Add this instead:
  - name: Commit Generated Site
    run: |
      git config user.name "github-actions[bot]"
      git config user.email "github-actions[bot]@users.noreply.github.com"
      git add docs/
      git diff --staged --quiet || git commit -m "chore: update site [skip ci]"
      git push origin main
  ```

- [ ] Add push trigger
  ```yaml
  on:
    push:
      branches: [main]
    schedule:
      - cron: '*/20 * * * *'
    workflow_dispatch:
  ```

### Step 4: Update .gitignore
- [ ] Remove `docs/` from `.gitignore` if present (currently not present ✅)
- [ ] Verify `public/` is still ignored (currently ignored ✅)

### Step 5: GitHub Settings
- [ ] Go to Settings > Pages
- [ ] Change source to: Branch `main` → Folder `/docs`
- [ ] Verify custom domain is set to `matchfly.org`
- [ ] Enable "Enforce HTTPS"

### Step 6: Test
- [ ] Run locally: `python src/generator.py`
- [ ] Verify files created in `docs/`
- [ ] Check CNAME exists: `cat docs/CNAME`
- [ ] Check .nojekyll exists: `ls -la docs/.nojekyll`
- [ ] Commit and push: `git add . && git commit -m "feat: migrate to /docs" && git push`
- [ ] Monitor workflow: `gh run list`
- [ ] Verify site: `https://matchfly.org`

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| DNS propagation delay | Medium | Low | CNAME is already configured in workflow |
| Existing gh-pages branch conflicts | Low | Medium | Delete gh-pages branch after migration |
| Broken links during transition | Low | Low | Both URLs redirect properly |
| Workflow permissions issue | Low | High | Verify "Read and write" permissions |
| Generator fails with new path | Low | Medium | Test locally before pushing |

---

## Rollback Plan

If migration fails:

1. **Revert generator.py:**
   ```bash
   git checkout HEAD~1 src/generator.py
   ```

2. **Revert workflow:**
   ```bash
   git checkout HEAD~1 .github/workflows/update-flights.yml
   ```

3. **Change GitHub Pages settings back:**
   - Settings > Pages
   - Source: Deploy from branch `gh-pages` / `/`

4. **Manual trigger workflow:**
   ```bash
   gh workflow run "Update Flight Data & Site"
   ```

---

## Success Criteria

After migration, verify:

- ✅ Site loads at `https://matchfly.org`
- ✅ HTTPS certificate is valid
- ✅ All pages load correctly (index, voo pages, cidades, etc.)
- ✅ Sitemap.xml is accessible
- ✅ robots.txt is accessible
- ✅ No Jekyll processing errors (check for _ folders/files)
- ✅ Workflow runs successfully every 20 minutes
- ✅ Manual workflow trigger works
- ✅ Push to main triggers deployment

---

## Timeline Estimate

| Task | Time | Complexity |
|------|------|------------|
| Update generator.py | 15 min | Low |
| Update workflow | 30 min | Medium |
| Create CNAME | 5 min | Low |
| Test locally | 20 min | Low |
| Push and monitor | 30 min | Medium |
| Verify in production | 20 min | Low |
| Documentation update | 30 min | Low |
| **Total** | **~2.5 hours** | **Medium** |

---

**Conclusion:** The migration is straightforward but critical. Current setup is incompatible with declared `/docs` strategy. Migration must be completed before Release 2.0.

---

**Related Documents:**
- Full audit: `REPOSITORY_HEALTH_CHECK.md`
- Quick summary: `HEALTH_CHECK_SUMMARY.md`
