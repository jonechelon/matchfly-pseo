# 🚀 Quick Start - GRU Airport Scraper

## Quick Setup (5 minutes)

### 1️⃣ Clone and Configure

```bash
cd ~/matchfly

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2️⃣ Run the Scraper

```bash
python3 voos_proximos_finalbuild.py
```

### 3️⃣ Check Results

```bash
# View extracted data
cat data/flights-db.json

# View logs
cat gru_scraper.log
```

## 📊 What Does the Scraper Do?

1. 🔍 **Discovers** API endpoints from gru.com.br
2. 📡 **Extracts** flight data (number, airline, times, status)
3. 🔎 **Filters** only Cancelled or Delayed > 2h flights
4. 💾 **Saves** to `data/flights-db.json`
5. 📝 **Logs** everything to `gru_scraper.log`

## 📁 Output Structure

```json
{
  "metadata": {
    "source": "GRU Airport (gru.com.br)",
    "scraped_at": "2026-01-11T18:34:35",
    "total_flights": 5,
    "filters": "Cancelados ou Atrasados > 2h"
  },
  "flights": [
    {
      "flight_number": "LA3090",
      "airline": "LATAM",
      "scheduled_time": "2026-01-11 15:34:34",
      "actual_time": "2026-01-11 18:04:34",
      "status": "Atrasado",
      "delay_hours": 2.5
    }
  ]
}
```

## 🎯 Use Cases

### Basic Usage
```bash
python3 voos_proximos_finalbuild.py
```

### Interactive Examples
```bash
python3 examples/example_usage.py
```

### Programmatic Mode
```python
from src.scrapers import GRUFlightScraper

scraper = GRUFlightScraper()
scraper.run()
```

## 🛠️ Quick Customization

### Change output file
```python
scraper = GRUFlightScraper(output_file="custom/path.json")
```

### Custom filter
```python
flights = scraper.fetch_flights()
custom = [f for f in flights if f['delay_hours'] > 3]
scraper.save_to_json(custom)
```

### Enable DEBUG mode
```python
import logging
logging.getLogger('scrapers.gru_flights_scraper').setLevel(logging.DEBUG)
```

## 📚 Next Steps

- 📖 Read the [complete documentation](_internal_docs/GRU_SCRAPER_USAGE.md)
- 🔍 Explore the [examples](examples/example_usage.py)
- ⚙️ See the [source code](src/scrapers/gru_flights_scraper.py)

## ❓ Problems?

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check logs
tail -f gru_scraper.log

# Debug mode
python3 -c "
from src.scrapers import GRUFlightScraper
import logging
logging.basicConfig(level=logging.DEBUG)
scraper = GRUFlightScraper()
scraper.run()
"
```

## ✨ Features

- ✅ **No Selenium** - Fast and lightweight
- ✅ **API Discovery** - Finds endpoints automatically
- ✅ **Robust** - Complete error handling
- ✅ **Logging** - Console + file
- ✅ **Filters** - Cancelled and delayed flights
- ✅ **JSON** - Structured format
- ✅ **Modular** - Easy to extend

---

**Total time**: ~5 minutes  
**Difficulty**: ⭐ Easy  
**Requirements**: Python 3.9+
