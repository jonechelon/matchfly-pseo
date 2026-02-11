# GRU Airport Flight Scraper - Usage Guide

## 📖 Overview

The **GRU Flight Scraper** is a professional scraper developed to extract flight data from Guarulhos International Airport (GRU). The scraper implements multiple strategies to discover and use hidden API endpoints, without needing Selenium.

## ✨ Features

### 🔍 Intelligent API Discovery
- Tries multiple common API endpoints
- Parses JSON data embedded in HTML when needed
- If collection fails: returns empty list and logs critical error (no fake data)

### 🛡️ Robust Error Handling
- Try-catch at all critical points
- Detailed logging of all errors
- Graceful degradation (continues even with partial failures)

### 📊 Smart Filtering
- Filters **Cancelled** flights
- Filters **Delayed** flights (delay > 2 hours)
- Automatically calculates delay in hours

### 📝 Complete Logging
- Logs to console (stdout)
- Logs to file (`gru_scraper.log`)
- Different levels: INFO, WARNING, ERROR, DEBUG

## 🚀 How to Use

### 1. Install Dependencies

```bash
cd ~/matchfly

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Scraper

**Method 1: Script Runner (Recommended)**
```bash
python3 voos_proximos_finalbuild.py
```

**Method 2: Directly**
```bash
python3 src/scrapers/gru_flights_scraper.py
```

**Method 3: As Module**
```bash
python3 -m src.scrapers.gru_flights_scraper
```

### 3. Use Programmatically

```python
from src.scrapers.gru_flights_scraper import GRUFlightScraper

# Create scraper instance
scraper = GRUFlightScraper(output_file="data/flights-db.json")

# Run complete scraping
scraper.run()

# Or use individual methods
flights = scraper.fetch_flights()
filtered = scraper.filter_flights(flights)
scraper.save_to_json(filtered)
```

## 📁 Generated Files

### `data/flights-db.json`
Main file with flight data:

```json
{
  "metadata": {
    "source": "GRU Airport (gru.com.br)",
    "scraped_at": "2026-01-11T18:34:35.005828",
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

### `gru_scraper.log`
Log file with execution history:

```
2026-01-11 18:34:34,243 - scrapers.gru_flights_scraper - INFO - 🚀 GRU Airport Flight Scraper - Starting
2026-01-11 18:34:34,246 - scrapers.gru_flights_scraper - INFO - 🔍 Starting API endpoint discovery...
2026-01-11 18:34:35,008 - scrapers.gru_flights_scraper - INFO - ✅ Scraping completed successfully!
```

## 🔧 Advanced Configuration

### Customize Output

```python
# Change output file path
scraper = GRUFlightScraper(output_file="custom/path/flights.json")

# Modify filters
def custom_filter(flight):
    return flight['delay_hours'] > 3  # Only delays > 3h

all_flights = scraper.fetch_flights()
custom_filtered = [f for f in all_flights if custom_filter(f)]
scraper.save_to_json(custom_filtered)
```

### Add New Endpoints

Edit the `API_ENDPOINTS` list in the class:

```python
API_ENDPOINTS = [
    "/pt-br/api/voos/partidas",
    "/your/new/endpoint",
]
```

### Adjust Logging

```python
import logging

# Change log level to DEBUG
logging.getLogger('scrapers.gru_flights_scraper').setLevel(logging.DEBUG)

# Disable console logs
logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.StreamHandler)]
```

## 🏗️ Code Architecture

### Main Classes

#### `GRUFlightScraper`
Main class that manages the entire scraping process.

**Public Methods:**
- `run()` - Runs the complete scraper
- `fetch_flights()` - Fetches flight data
- `filter_flights(flights)` - Filters flights by criteria
- `save_to_json(flights)` - Saves data to JSON

**Internal Methods:**
- `_extract_next_build_id(html)` - Captures Next.js `buildId` from HTML
- `fetch_next_data_endpoint(build_id)` - Uses `/_next/data/{buildId}/...` to fetch JSON
- `_filter_only_today(flights)` - Keeps only flights with today's date
- `discover_api_endpoint()` - Discovers valid endpoints
- `scrape_html_fallback()` - Fallback when API is not available
- `_parse_flight(flight_data)` - Parses individual flight data
- `_parse_datetime(dt_string)` - Parses date/time strings
- `_parse_embedded_data(data)` - Extracts JSON data from HTML

### Execution Flow

```
1. Initialization
   └─ Configures headers and HTTP session

2. API Discovery
   ├─ Tests known endpoints
   ├─ Validates JSON responses
   └─ Returns first valid endpoint

3. Data Collection
   ├─ Session with Cloudscraper (cookies/JS challenges automatically)
   ├─ Loads `/pt-br/voos` to get `buildId` and tries `/_next/data/{buildId}/pt-br/voos.json`
   ├─ If API found: uses endpoint
   ├─ If API not found: parses HTML
   └─ If total failure: returns empty list and logs critical error (no fake data)

4. Processing
   ├─ Normalizes flight data
   ├─ Calculates delays
   └─ Parses times

4b. Date Filter
   └─ Keeps only flights with today's date to avoid persistence of old flights

5. Filtering
   ├─ Identifies cancelled flights
   ├─ Identifies delayed flights > 2h
   └─ Returns filtered list

6. Persistence
   ├─ Adds metadata
   ├─ Formats JSON with indentation
   └─ Saves to file
```

## 🐛 Troubleshooting

### Error: ModuleNotFoundError

**Cause:** Dependencies not installed

**Solution:**
```bash
pip install -r requirements.txt
```

### Error: Permission Denied when saving JSON

**Cause:** `data/` folder doesn't exist or no permission

**Solution:**
```bash
mkdir -p data
chmod 755 data
```

### Warning: urllib3 OpenSSL

**Cause:** Old OpenSSL/LibreSSL version

**Solution:** Doesn't affect functionality, but can update:
```bash
pip install --upgrade urllib3
```

### No data extracted

**Cause:** Site changed structure or API unavailable

**Solution:**
1. Check logs for details
2. Update endpoints in `API_ENDPOINTS` list
3. Use DEBUG mode for analysis:
   ```python
   logger.setLevel(logging.DEBUG)
   ```

### Rate Limiting / Blocking

**Cause:** Too many requests in short period

**Solution:** Add delays between requests:
```python
import time
time.sleep(2)  # 2 seconds between requests
```

## 📈 Performance

### Typical Metrics
- **Execution time:** ~1-5 seconds
- **HTTP requests:** 3-10 (depending on endpoints tested)
- **Memory:** < 50MB
- **JSON file size:** ~1-10KB (varies with number of flights)

### Implemented Optimizations
- ✅ Reusable HTTP session
- ✅ Timeout on all requests
- ✅ Lazy evaluation of data
- ✅ Early return in API discovery

## 🔐 Security

### Implemented Practices
- ✅ Input data validation
- ✅ String sanitization
- ✅ Realistic User-Agent headers
- ✅ Timeouts to prevent hanging
- ✅ No hardcoded credentials

### Recommendations
- 🔸 Respect site robots.txt
- 🔸 Implement rate limiting in production
- 🔸 Use proxy if needed
- 🔸 Monitor error logs

## 🚀 Next Steps

### Suggested Improvements
- [ ] Implement request caching
- [ ] Add proxy support
- [ ] Create scheduler for automatic execution
- [ ] Add unit tests
- [ ] Implement retry with exponential backoff
- [ ] Add support for multiple airports
- [ ] Create REST API to consume data
- [ ] Web dashboard for visualization

### Possible Integrations
- 📧 Email notifications (cancelled flights)
- 💬 Telegram/WhatsApp bot
- 📊 Grafana dashboard
- 🔔 Real-time alerts
- 🗄️ Database (PostgreSQL/MongoDB)

## 📚 Additional Resources

### Documentation
- [BeautifulSoup4 Docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Cloudscraper](https://github.com/VeNoMouS/cloudscraper)
- [Python Logging](https://docs.python.org/3/library/logging.html)

### Useful Tools
- **Insomnia/Postman:** Test APIs manually
- **Chrome DevTools:** Inspect network calls
- **jq:** Process JSON on command line

## 👥 Support

For questions or issues:
1. Check logs in `gru_scraper.log`
2. Consult this documentation
3. Open an issue in the repository

---

**Version:** 1.0.0  
**Last Updated:** 2026-01-11  
**License:** MIT
