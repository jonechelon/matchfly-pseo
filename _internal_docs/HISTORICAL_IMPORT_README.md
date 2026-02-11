# 🚀 ANAC Historical Import - Quick Start

## 📥 What Is It?

Automated script that **downloads official ANAC data** and populates MatchFly with **delayed flights from the last 30 days** in Guarulhos (GRU).

### ✨ Features

- ✅ Automatic download of ANAC CSVs (Open Data)
- ✅ Smart filtering (only SBGR + delay > 15min)
- ✅ Automatic airline mapping (G3→GOL, etc.)
- ✅ Integration with CITY_TO_IATA dictionary
- ✅ Duplicate prevention
- ✅ Success sound (Glass.aiff) 🔔

---

## ⚡ Quick Usage

### Option 1: Automated Script (Recommended)

```bash
# Import + Generate pages + Validate (all automatic)
python run_historical_import.py
```

### Option 2: Manual Step by Step

```bash
# 1. Import historical data
python src/historical_importer.py

# 2. Generate HTML pages
python src/generator.py

# 3. View result
open docs/index.html
```

---

## 📊 Example Result

```
📊 IMPORT SUMMARY:
   • Files downloaded:        2
   • Total rows read:         234,567
   • SBGR flights:            15,432
   • Flights with delay >15min: 2,345
   • Flights imported (new):  2,345
   • Duplicates ignored:      0

🎉 SUCCESS! Historical data imported!
```

After import, you'll have:
- **2,345 HTML pages** generated in `docs/voo/`
- **sitemap.xml** updated
- **index.html** with the 20 most recent flights

---

## 🔧 Configuration

### Change Airport

Edit `src/historical_importer.py` (line ~655):

```python
importer = ANACHistoricalImporter(
    airport_code="SBSP",  # Congonhas
    # or "SBBR" (Brasília), "SBGL" (Galeão), etc.
)
```

### Adjust Period

```python
importer = ANACHistoricalImporter(
    days_lookback=60,  # Last 60 days (default: 30)
)
```

### Adjust Delay Filter

```python
importer = ANACHistoricalImporter(
    min_delay_minutes=30,  # Only delays > 30min (default: 15)
)
```

---

## 📚 Complete Documentation

For complete technical details, see:

👉 **[_internal_docs/HISTORICAL_IMPORTER_GUIDE.md](HISTORICAL_IMPORTER_GUIDE.md)**

---

## 🧪 Tests

```bash
# Run all tests
pytest tests/test_historical_importer.py -v

# Run specific tests
pytest tests/test_historical_importer.py::TestAirlineMapping -v
```

---

## 📦 Dependencies

Automatically installed by script:

- `pandas` - CSV processing
- `requests` - File download
- `beautifulsoup4` - HTML parsing (optional)

```bash
# Or install manually
pip install -r requirements.txt
```

---

## ⚠️ Troubleshooting

### Error: "File not found (HTTP 404)"

**Normal for first days of the month.** ANAC publishes data with some delay.

**Solution**: Script automatically uses previous month.

### Error: "pandas not found"

**Solution**: Script installs automatically. If it fails:

```bash
pip install pandas
```

### No flights imported (0 new)

**Possible causes**:
1. All flights already exist in database (duplicates) ✅
2. No delayed flights in period 
3. Filter too restrictive

**Solution**: Check `historical_importer.log` for details.

---

## 📁 Files Created

```
data/
  └── flights-db.json           # Database (updated)

docs/
  ├── index.html                # Home page (regenerated)
  ├── sitemap.xml               # Sitemap (updated)
  └── voo/
      ├── voo-gol-1234-gru-atrasado.html
      ├── voo-azul-5678-gru-cancelado.html
      └── ...                   # Thousands of pages

historical_importer.log         # Detailed logs
```

---

## 🎯 Next Steps

After successful import:

1. **View locally**:
   ```bash
   open docs/index.html
   ```

2. **Deploy**:
   ```bash
   git add .
   git commit -m "feat: import ANAC historical data (30 days)"
   git push
   ```

3. **Configure GitHub Actions** to import automatically:
   - Add cronjob in `.github/workflows/update-flights.yml`
   - Run daily import at 06:00 UTC

---

## 🔗 Useful Links

- **ANAC Open Data**: https://www.gov.br/anac/pt-br/assuntos/dados-abertos/arquivos/vra/
- **Technical Documentation**: [_internal_docs/HISTORICAL_IMPORTER_GUIDE.md](HISTORICAL_IMPORTER_GUIDE.md)
- **Tests**: [tests/test_historical_importer.py](tests/test_historical_importer.py)

---

**Developed with ❤️ by the MatchFly team**

*Date: January 12, 2026*
