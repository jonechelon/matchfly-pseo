# 📚 MatchFly Historical Importer - Usage Guide

## 🎯 Overview

The **Historical Importer** is a data engineering script that downloads and imports official historical data from ANAC (Agência Nacional de Aviação Civil) to populate the MatchFly database with delayed flights from the last 30 days.

### Data Source

- **Origin**: ANAC Brazilian Open Data Portal
- **Dataset**: VRA (Voo Regular Ativo - Regular Active Flight)
- **Base URL**: https://www.gov.br/anac/pt-br/assuntos/dados-abertos/arquivos/vra/
- **Format**: Monthly CSV with all flights operated in Brazil

## 🚀 How to Use

### 1. Install Dependencies

```bash
# Make sure pandas is installed
pip install -r requirements.txt
```

### 2. Basic Execution

```bash
# Imports data from last 30 days of delayed flights in Guarulhos
python src/historical_importer.py
```

### 3. Generate Pages After Import

```bash
# After importing, generate HTML pages
python src/generator.py
```

## ⚙️ Configuration

### Main Parameters (editable in `main()`)

```python
importer = ANACHistoricalImporter(
    output_file="data/flights-db.json",  # Output file
    airport_code="SBGR",                 # Airport ICAO code
    min_delay_minutes=15,                # Minimum delay to consider
    days_lookback=30                     # How many days in the past to search
)
```

### Customizations

#### Change Airport

To import data from another airport, change `airport_code`:

```python
airport_code="SBSP"  # Congonhas (São Paulo)
airport_code="SBBR"  # Brasília
airport_code="SBGL"  # Galeão (Rio de Janeiro)
```

#### Adjust Period

To import more or fewer days:

```python
days_lookback=60  # Last 60 days
days_lookback=7   # Last week
```

#### Adjust Delay Filter

To change minimum delay criteria:

```python
min_delay_minutes=30  # Only delays > 30 minutes
min_delay_minutes=60  # Only delays > 1 hour
```

## 📊 How It Works

### Importer Workflow

```
┌─────────────────────────────────────────────────┐
│ STEP 1: Load existing database                 │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ STEP 2: Identify available ANAC files         │
│  • Calculates months to search (current + previous)│
│  • Generates download URLs                     │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ STEP 3: Download and Processing               │
│  ├─ Download monthly CSVs from ANAC          │
│  ├─ Parse with pandas (automatic encoding)     │
│  ├─ Intelligent column identification          │
│  ├─ Filter 1: Origin airport = SBGR          │
│  ├─ Delay calculation                         │
│  ├─ Filter 2: Delay > 15 minutes             │
│  ├─ Filter 3: Last 30 days                    │
│  └─ Mapping to MatchFly format                │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ STEP 4: Merge with existing database          │
│  • Avoids duplicates by unique ID              │
│  • Adds only new flights                       │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ STEP 5: Cleanup temporary files                │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ STEP 6: Summary + Success Sound 🔔            │
└─────────────────────────────────────────────────┘
```

### Data Mapping

The script automatically converts ANAC fields to MatchFly format:

| ANAC Field                    | MatchFly Field      | Transformation                          |
|-------------------------------|---------------------|----------------------------------------|
| `Sigla Empresa ICAO`          | `airline`           | Maps via dictionary (G3→GOL, etc.)   |
| `Numero Voo`                  | `flight_number`     | Removes prefixes, leading zeros        |
| `Aeroporto Origem (ICAO)`     | `origin`            | SBGR → GRU                             |
| `Cidade Destino`              | `destination`       | Uses CITY_TO_IATA dictionary           |
| `Data/Hora Prevista`          | `scheduled_time`    | Parse to HH:MM                         |
| `Data/Hora Real`              | `actual_time`       | Parse to HH:MM                         |
| Calculated difference         | `delay_min`         | (Actual - Scheduled) in minutes        |
| Calculated difference         | `delay_hours`       | (Actual - Scheduled) in hours (decimal)│
| Based on delay                | `status`            | "Atrasado" or "Cancelado"              |

## 🗺️ Airline Mapping

The script includes complete airline dictionary:

### Brazilian
- **G3** → GOL
- **AD** → AZUL  
- **LA/JJ** → LATAM
- **2Z** → Voepass

### International (Europe)
- **AF** → Air France
- **KL** → KLM
- **LH** → Lufthansa
- **BA** → British Airways
- **TP** → TAP Portugal
- And more...

### International (Americas)
- **AR** → Aerolíneas Argentinas
- **AA** → American Airlines
- **DL** → Delta
- **UA** → United Airlines
- **CM** → Copa Airlines
- And more...

## 📋 Logs and Tracking

### Log File

All operations are logged in:

```
historical_importer.log
```

### Example Success Log

```
2026-01-12 10:30:15 - INFO - 🔍 Identifying available ANAC files...
2026-01-12 10:30:15 - INFO - 📅 Periods to search: 202601, 202512
2026-01-12 10:30:16 - INFO - 📥 Downloading: https://...VRA_202601.csv
2026-01-12 10:30:45 - INFO - ✅ Download completed: VRA_202601.csv (45.32 MB)
2026-01-12 10:31:00 - INFO - 📊 Processing: VRA_202601.csv
2026-01-12 10:31:02 - INFO -    📈 Total rows: 123,456
2026-01-12 10:31:03 - INFO -    🛫 SBGR flights: 8,234
2026-01-12 10:31:15 - INFO -    ✅ Delayed flights (>15min): 1,456
2026-01-12 10:31:20 - INFO - ✅ Database updated: 1,456 new flights added
2026-01-12 10:31:20 - INFO -    Total in database: 1,458 flights
2026-01-12 10:31:20 - INFO - 🔔 Success sound played!
```

## 🎨 Advanced Features

### 1. Intelligent Column Identification

The script uses **flexible patterns** to identify columns, even if ANAC changes names:

```python
# Search for multiple patterns
'airline_code': ['sigla', 'empresa', 'companhia', 'icao_empresa']
'flight_number': ['numero_voo', 'voo', 'flight']
# ... etc
```

### 2. Automatic Encoding Detection

Tries multiple encodings automatically:

```python
for encoding in ['latin-1', 'utf-8', 'iso-8859-1']:
    try:
        df = pd.read_csv(csv_path, encoding=encoding)
        break
    except UnicodeDecodeError:
        continue
```

### 3. Duplicate Prevention

Each flight receives a unique ID based on:

```
ID = airline + flight_number + scheduled_date
```

Example: `gol-1234-2025-12-15`

### 4. Integration with CITY_TO_IATA Dictionary

Reuses dictionary from `generator.py` to map cities:

```python
from generator import get_iata_code, CITY_TO_IATA

destination_iata = get_iata_code("Paris")  # → "CDG"
```

## 📊 Generated Statistics

At the end, the script displays:

```
📊 IMPORT SUMMARY:
   • Files downloaded:        2
   • Total rows read:         234,567
   • SBGR flights:            15,432
   • Flights with delay >15min: 2,345
   • Flights imported (new):  2,345
   • Duplicates ignored:      0
   • Errors:                  12
```

## ⚠️ Troubleshooting

### Error: "pandas not found"

**Solution**: Script installs automatically. If it fails:

```bash
pip install pandas
```

### Error: "File not found (HTTP 404)"

**Cause**: ANAC hasn't published current month data yet.

**Solution**: Normal for first days of the month. Script will continue with previous month.

### Error: "Could not identify required columns"

**Cause**: ANAC drastically changed CSV structure.

**Solution**: Open CSV manually and update patterns in `_identify_columns()`.

### No flights imported (0 new)

**Possible causes**:
1. All flights already exist in database (duplicates)
2. No delayed flights in period
3. Filter too restrictive (e.g.: `min_delay_minutes` too high)

**Solution**: Check logs for details.

## 🔧 Advanced Customization

### Add New Airline

Edit the `AIRLINE_MAPPING` dictionary:

```python
AIRLINE_MAPPING = {
    # ...
    "XY": "New Airline",  # Add here
}
```

### Change Date Format

Edit `parse_datetime()` to accept new formats:

```python
for date_format in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
    # Add new format here
```

### Add Custom Fields

In `_process_row()` method, add new fields:

```python
flight = {
    # ... existing fields ...
    'custom_field': row.get('anac_column', ''),
}
```

## 📈 Performance

### Average Times

| Operation                  | Average Time    |
|---------------------------|----------------|
| Download 1 CSV (50MB)    | ~30-60s        |
| Process 1 CSV             | ~15-30s        |
| Merge with database       | <5s            |
| **Total (1 month)**      | **~1-2 minutes**|
| **Total (2 months)**      | **~3-4 minutes**|

### Optimizations

- Uses `pandas` for efficient processing
- Download with streaming (doesn't overload RAM)
- Cache existing flights in memory
- Logs with levels (INFO/DEBUG)

## 🎯 Next Steps

After importing historical data:

1. **Generate HTML pages**:
   ```bash
   python src/generator.py
   ```

2. **Check result**:
   ```bash
   open docs/index.html
   ```

3. **Deploy to production**:
   ```bash
   # If using GitHub Actions
   git add .
   git commit -m "feat: import ANAC historical data"
   git push
   ```

## 📞 Support

For questions or issues:

1. Check `historical_importer.log`
2. Run with `python -v src/historical_importer.py` for more details
3. Consult ANAC documentation: https://www.gov.br/anac/pt-br/assuntos/dados-abertos

---

**Developed with ❤️ by the MatchFly team**

*Last updated: January 12, 2026*
