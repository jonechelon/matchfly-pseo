# 🚀 Importação Histórica ANAC - Quick Start

## 📥 O Que É?

Script automatizado que **baixa dados oficiais da ANAC** e popula o MatchFly com **voos atrasados dos últimos 30 dias** em Guarulhos (GRU).

### ✨ Recursos

- ✅ Download automático de CSVs da ANAC (Dados Abertos)
- ✅ Filtragem inteligente (apenas SBGR + atraso > 15min)
- ✅ Mapeamento automático de companhias aéreas (G3→GOL, etc.)
- ✅ Integração com dicionário CITY_TO_IATA
- ✅ Prevenção de duplicatas
- ✅ Som de sucesso (Glass.aiff) 🔔

---

## ⚡ Uso Rápido

### Opção 1: Script Automatizado (Recomendado)

```bash
# Importa + Gera páginas + Valida (tudo automático)
python run_historical_import.py
```

### Opção 2: Passo a Passo Manual

```bash
# 1. Importar dados históricos
python src/historical_importer.py

# 2. Gerar páginas HTML
python src/generator.py

# 3. Visualizar resultado
open public/index.html
```

---

## 📊 Exemplo de Resultado

```
📊 SUMÁRIO DA IMPORTAÇÃO:
   • Arquivos baixados:        2
   • Total de linhas lidas:    234,567
   • Voos de SBGR:             15,432
   • Voos com atraso >15min:   2,345
   • Voos importados (novos):  2,345
   • Duplicatas ignoradas:     0

🎉 SUCESSO! Dados históricos importados!
```

Depois da importação, você terá:
- **2.345 páginas HTML** geradas em `public/voo/`
- **sitemap.xml** atualizado
- **index.html** com os 20 voos mais recentes

---

## 🔧 Configuração

### Mudar Aeroporto

Edite `src/historical_importer.py` (linha ~655):

```python
importer = ANACHistoricalImporter(
    airport_code="SBSP",  # Congonhas
    # ou "SBBR" (Brasília), "SBGL" (Galeão), etc.
)
```

### Ajustar Período

```python
importer = ANACHistoricalImporter(
    days_lookback=60,  # Últimos 60 dias (padrão: 30)
)
```

### Ajustar Filtro de Atraso

```python
importer = ANACHistoricalImporter(
    min_delay_minutes=30,  # Apenas atrasos > 30min (padrão: 15)
)
```

---

## 📚 Documentação Completa

Para detalhes técnicos completos, consulte:

👉 **[docs/HISTORICAL_IMPORTER_GUIDE.md](docs/HISTORICAL_IMPORTER_GUIDE.md)**

---

## 🧪 Testes

```bash
# Rodar todos os testes
pytest tests/test_historical_importer.py -v

# Rodar testes específicos
pytest tests/test_historical_importer.py::TestAirlineMapping -v
```

---

## 📦 Dependências

Automaticamente instaladas pelo script:

- `pandas` - Processamento de CSVs
- `requests` - Download de arquivos
- `beautifulsoup4` - Parse de HTML (opcional)

```bash
# Ou instale manualmente
pip install -r requirements.txt
```

---

## ⚠️ Troubleshooting

### Erro: "Arquivo não encontrado (HTTP 404)"

**Normal para os primeiros dias do mês.** A ANAC publica os dados com alguns dias de atraso.

**Solução**: O script automaticamente usa o mês anterior.

### Erro: "pandas não encontrado"

**Solução**: O script instala automaticamente. Se falhar:

```bash
pip install pandas
```

### Nenhum voo importado (0 novos)

**Causas possíveis**:
1. Todos os voos já existem no banco (duplicatas) ✅
2. Não houve voos atrasados no período 
3. Filtro muito restritivo

**Solução**: Verifique `historical_importer.log` para detalhes.

---

## 📁 Arquivos Criados

```
data/
  └── flights-db.json           # Banco de dados (atualizado)

public/
  ├── index.html                # Home page (regenerada)
  ├── sitemap.xml               # Sitemap (atualizado)
  └── voo/
      ├── voo-gol-1234-gru-atrasado.html
      ├── voo-azul-5678-gru-cancelado.html
      └── ...                   # Milhares de páginas

historical_importer.log         # Logs detalhados
```

---

## 🎯 Próximos Passos

Após importar com sucesso:

1. **Visualize localmente**:
   ```bash
   open public/index.html
   ```

2. **Faça deploy**:
   ```bash
   git add .
   git commit -m "feat: importar dados históricos ANAC (30 dias)"
   git push
   ```

3. **Configure GitHub Actions** para importar automaticamente:
   - Adicione cronjob em `.github/workflows/update-flights.yml`
   - Execute importação diária às 06:00 UTC

---

## 🔗 Links Úteis

- **Dados Abertos ANAC**: https://www.gov.br/anac/pt-br/assuntos/dados-abertos/arquivos/vra/
- **Documentação Técnica**: [docs/HISTORICAL_IMPORTER_GUIDE.md](docs/HISTORICAL_IMPORTER_GUIDE.md)
- **Testes**: [tests/test_historical_importer.py](tests/test_historical_importer.py)

---

**Desenvolvido com ❤️ pela equipe MatchFly**

*Data: 12 de Janeiro de 2026*
