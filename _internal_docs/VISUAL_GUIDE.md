# 🎨 Visual Guide - Historical Importer

## 📺 What You'll See on Screen

### 1️⃣ Running the Import

```bash
$ python run_historical_import.py
```

**Expected Output**:

```
╔════════════════════════════════════════════════════════════════════╗
║               🔄 MATCHFLY - HISTORICAL IMPORT                     ║
╚════════════════════════════════════════════════════════════════════╝

This script will:
  1. Import historical ANAC data (last 30 days)
  2. Generate HTML pages with imported data
  3. Validate the result

Continue? [Y/n]: y

======================================================================
🚀 STEP 1: Importing historical ANAC data
======================================================================


╔════════════════════════════════════════════════════════════════════╗
║            🚀 MATCHFLY HISTORICAL IMPORTER - ANAC VRA             ║
╚════════════════════════════════════════════════════════════════════╝

🎯 Configuration:
   • Airport:         SBGR (Guarulhos)
   • Minimum delay:   15 minutes
   • Period:          Last 30 days
   • Output:          data/flights-db.json

======================================================================
STEP 1: LOADING EXISTING DATABASE
======================================================================
📚 Existing flights loaded: 2

======================================================================
STEP 2: IDENTIFYING ANAC FILES
======================================================================
🔍 Identifying available ANAC files...
📅 Periods to search: 202601, 202512
   • https://sistemas.anac.gov.br/.../VRA_202601.csv
   • https://sistemas.anac.gov.br/.../VRA_202512.csv

======================================================================
STEP 3: DOWNLOAD AND PROCESSING
======================================================================
📥 Downloading: https://sistemas.anac.gov.br/.../VRA_202601.csv
✅ Download completed: VRA_202601.csv (45.32 MB)
📊 Processing: VRA_202601.csv
   ✅ Encoding detected: latin-1
   📈 Total rows: 123,456
   🔑 Columns identified: ['airline_code', 'flight_number', ...]
   🛫 SBGR flights: 8,234
   ⏱️  Calculating delays...
   ✅ Delayed flights (>15min): 1,456

📥 Downloading: https://sistemas.anac.gov.br/.../VRA_202512.csv
✅ Download completed: VRA_202512.csv (48.91 MB)
📊 Processing: VRA_202512.csv
   ✅ Encoding detected: latin-1
   📈 Total rows: 134,567
   🔑 Columns identified: ['airline_code', 'flight_number', ...]
   🛫 SBGR flights: 9,123
   ⏱️  Calculating delays...
   ✅ Delayed flights (>15min): 1,234

======================================================================
STEP 4: MERGING WITH DATABASE
======================================================================
🔄 Merging 2,690 new flights with existing database...
✅ Database updated: 2,690 new flights added
   Total in database: 2,692 flights

======================================================================
STEP 5: CLEANUP
======================================================================
🧹 Temporary files removed

╔════════════════════════════════════════════════════════════════════╗
║                     ✅ IMPORT COMPLETED!                           ║
╚════════════════════════════════════════════════════════════════════╝

📊 IMPORT SUMMARY:
   • Files downloaded:        2
   • Total rows read:         258,023
   • SBGR flights:             17,357
   • Flights with delay >15min: 2,690
   • Flights imported (new):   2,690
   • Duplicates ignored:       0
   • Errors:                   12

📁 Database: data/flights-db.json

🎉 SUCCESS! Historical data imported successfully!
🚀 Run python src/generator.py to generate pages.
🔔 Success sound played!


======================================================================
🚀 STEP 2: Generating HTML pages
======================================================================


╔════════════════════════════════════════════════════════════════════╗
║               🚀 MATCHFLY PAGE GENERATOR v2.0                     ║
╚════════════════════════════════════════════════════════════════════╝


======================================================================
STEP 1: SETUP & VALIDATION
======================================================================
✅ Affiliate link configured: https://www.airhelp.com/...
✅ docs/voo folder ready

======================================================================
STEP 2: INITIAL CLEANUP (Audit)
======================================================================
🗑️  Removed: docs/index.html (will be regenerated)
📊 Detected 2 old files in docs/voo/
   Will be automatically removed when not regenerated.

======================================================================
STEP 3: GENERATION WORKFLOW
======================================================================
📊 Total flights loaded: 2692

🔄 Starting resilient rendering...
----------------------------------------------------------------------
[1/2692] Processing 1234...
✅ Success: voo-gol-1234-gru-atrasado.html
[2/2692] Processing 5678...
✅ Success: voo-azul-5678-gru-cancelado.html
[3/2692] Processing 9012...
✅ Success: voo-latam-9012-gru-atrasado.html
...
[2690/2692] Processing 4567...
✅ Success: voo-gol-4567-gru-atrasado.html
[2691/2692] Processing 8901...
✅ Success: voo-azul-8901-gru-atrasado.html
[2692/2692] Processing 2345...
✅ Success: voo-latam-2345-gru-cancelado.html

======================================================================
STEP 3.2: ORPHAN MANAGEMENT
======================================================================
🗑️  Found 2 orphan files for removal:
   • Removed: voo-air-france-0459-gru-atrasado.html
   • Removed: voo-klm-0792-gru-atrasado.html

======================================================================
STEP 3.3: SITEMAP GENERATION
======================================================================
✅ Sitemap generated: docs/sitemap.xml
   • URLs included: 2691 (1 home + 2690 flights)

======================================================================
STEP 3.4: HOME PAGE GENERATION
======================================================================
✅ Home page generated: docs/index.html
   • Flights displayed: 20 (of 2690 total)
   • Growth Variables:
     - Heroes (social proof): 4868
     - Gate context: Gate B12
     - UTM suffix: ?utm_source=hero_gru

╔════════════════════════════════════════════════════════════════════╗
║                       ✅ BUILD COMPLETED!                          ║
╚════════════════════════════════════════════════════════════════════╝

📊 BUILD SUMMARY:
   • Flights processed:     2692
   • Successes:             2690 pages
   • Failures:              2 pages
   • Filtered (< 15min):    0 flights
   • Orphans removed:       2 files
   • Sitemap:               Updated with 2690 URLs

📁 Output:
   • Flight pages:         docs/voo/
   • Home page:             docs/index.html
   • Sitemap:               docs/sitemap.xml

🎉 Build completed successfully!
🌐 Open docs/index.html in browser

✅ MatchFly: IATA dictionary expanded successfully!


======================================================================
🔍 STEP 3: Validating result
======================================================================

✅ Validation completed!

📊 Result:
   • Flight pages generated: 2690
   • Index.html: ✓
   • Sitemap.xml: ✓

🎉 SUCCESS! Import and generation completed!

🌐 To view:
   open docs/index.html

📦 To deploy:
   git add .
   git commit -m "feat: import ANAC historical data"
   git push

```

---

## 🗂️ Generated File Structure

### Before Import:

```
data/
  └── flights-db.json (2 flights)

docs/
  ├── index.html
  ├── sitemap.xml
  └── voo/
      ├── voo-air-france-0459-gru-atrasado.html
      └── voo-klm-0792-gru-atrasado.html
```

### After Import:

```
data/
  └── flights-db.json (2,692 flights) ← ✨ Updated!

docs/
  ├── index.html ← ✨ Regenerated!
  ├── sitemap.xml ← ✨ Updated with 2,690 URLs!
  └── voo/
      ├── voo-gol-1234-gru-atrasado.html ← 🆕 New!
      ├── voo-gol-1235-gru-atrasado.html ← 🆕 New!
      ├── voo-azul-5678-gru-cancelado.html ← 🆕 New!
      ├── voo-azul-5679-gru-atrasado.html ← 🆕 New!
      ├── voo-latam-9012-gru-atrasado.html ← 🆕 New!
      ├── voo-latam-9013-gru-atrasado.html ← 🆕 New!
      └── ... (2,690 HTML pages!) ← 🆕 New!

historical_importer.log ← 🆕 Detailed log
```

---

## 📄 Example Updated `flights-db.json` File

### Before (2 flights):

```json
{
  "flights": [
    {
      "flight_number": "0459",
      "airline": "Air France",
      "status": "Atrasado",
      "scheduled_time": "20:40",
      "actual_time": "22:40",
      "delay_hours": 2.0,
      "delay_min": 120,
      "origin": "GRU",
      "destination": "Paris",
      "numero": "0459",
      "companhia": "Air France",
      "horario": "20:40"
    },
    {
      "flight_number": "0792",
      "airline": "KLM",
      "status": "Atrasado",
      "scheduled_time": "21:00",
      "actual_time": "21:25",
      "delay_hours": 0.42,
      "delay_min": 25,
      "origin": "GRU",
      "destination": "Amsterdã",
      "numero": "0792",
      "companhia": "KLM",
      "horario": "21:00"
    }
  ],
  "metadata": {
    "scraped_at": "2026-01-12T17:45:15.777435+00:00",
    "source": "playwright_intercept:GetVoos"
  }
}
```

### After (2,692 flights):

```json
{
  "flights": [
    {
      "flight_number": "1234",
      "airline": "GOL",
      "status": "Atrasado",
      "scheduled_time": "08:30",
      "actual_time": "09:15",
      "delay_hours": 0.75,
      "delay_min": 45,
      "origin": "GRU",
      "destination": "Rio de Janeiro",
      "numero": "1234",
      "companhia": "GOL",
      "horario": "08:30",
      "scheduled_date": "2025-12-15",
      "actual_date": "2025-12-15"
    },
    {
      "flight_number": "5678",
      "airline": "AZUL",
      "status": "Cancelado",
      "scheduled_time": "10:00",
      "actual_time": "10:00",
      "delay_hours": 0,
      "delay_min": 0,
      "origin": "GRU",
      "destination": "Brasília",
      "numero": "5678",
      "companhia": "AZUL",
      "horario": "10:00",
      "scheduled_date": "2025-12-16",
      "actual_date": "2025-12-16"
    },
    // ... +2,688 flights
  ],
  "metadata": {
    "last_import": "2026-01-12T10:30:15",
    "source": "anac_vra_historical",
    "total_flights": 2692,
    "import_stats": {
      "downloaded_files": 2,
      "total_rows": 258023,
      "filtered_sbgr": 17357,
      "delayed_flights": 2690,
      "imported": 2690,
      "duplicates": 0,
      "errors": 12
    }
  }
}
```

---

## 🌐 Example Generated `index.html`

When you open `docs/index.html`, you'll see:

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│              ✈️ MatchFly - Flights with Problems            │
│                                                              │
│        Check if you have the right to compensation          │
│                    of up to R$ 10,000                       │
│                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ GOL 1234           │  │ AZUL 5678            │          │
│  │ Delayed            │  │ Cancelled            │          │
│  │ ⏱️ Delay: 0.75h   │  │ ⏱️ Cancelled         │          │
│  │ 🔗 View details → │  │ 🔗 View details →   │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ LATAM 9012         │  │ GOL 3456             │          │
│  │ Delayed            │  │ Delayed              │          │
│  │ ⏱️ Delay: 1.2h    │  │ ⏱️ Delay: 0.5h      │          │
│  │ 🔗 View details → │  │ 🔗 View details →   │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                              │
│  ... (20 most recent flights displayed)                      │
│                                                              │
│  Generated on: 01/12/2026 10:45                             │
│  Total flights: 2690                                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Example Generated `sitemap.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://matchfly.org/</loc>
    <lastmod>2026-01-12</lastmod>
    <changefreq>hourly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://matchfly.org/voo/voo-gol-1234-gru-atrasado.html</loc>
    <lastmod>2026-01-12</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://matchfly.org/voo/voo-azul-5678-gru-cancelado.html</loc>
    <lastmod>2026-01-12</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <!-- ... +2,688 URLs -->
</urlset>
```

---

## 📝 Example Individual Flight Page

When you open `docs/voo/voo-gol-1234-gru-atrasado.html`:

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│        🛫 Flight GOL 1234 - Guarulhos → Rio de Janeiro      │
│                                                              │
│  ⚠️ Status: Delayed (45 minutes)                            │
│                                                              │
│  📅 Date: 12/15/2025                                         │
│  ⏰ Scheduled: 08:30                                         │
│  ⏰ Actual: 09:15                                            │
│  ⏱️ Delay: 45 minutes (0.75h)                               │
│                                                              │
│  ✈️ Origin: GRU (Guarulhos)                                │
│  🏙️ Destination: Rio de Janeiro                            │
│  🏢 Airline: GOL                                             │
│                                                              │
│  ┌────────────────────────────────────────────────┐        │
│  │                                                │        │
│  │  💰 You may have the right to compensation     │        │
│  │      of up to R$ 10,000!                       │        │
│  │                                                │        │
│  │  📋 Regulation: ANAC 400                       │        │
│  │  (domestic flight)                            │        │
│  │                                                │        │
│  │  [Check my right now →]                       │        │
│  │  ↑ Link to AirHelp with pre-filled data       │        │
│  │                                                │        │
│  └────────────────────────────────────────────────┘        │
│                                                              │
│  📊 Information reported 2 hours ago                        │
│  🔔 Last update: 01/12/2026 at 10:45                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎯 Success Metrics

### SEO Impact

**Before**:
- 2-3 indexable pages
- Little content
- Sitemap with 3 URLs

**After**:
- 2,690 indexable pages! 🎉
- Rich and unique content per flight
- Sitemap with 2,691 URLs
- Better long-tail keyword coverage

### User Experience

**Before**:
- Only active flights at the moment
- Limited information

**After**:
- Complete 30-day history
- More chances for user to find their flight
- More entry pages via Google

### Monetization

**Before**:
- 2-3 conversion opportunities

**After**:
- 2,690 conversion opportunities! 🎉
- Affiliate link on each page
- Pre-filled data in funnel (↑ conversion)

---

## 🚀 Quick Commands

```bash
# Complete import (recommended)
python run_historical_import.py

# Or manual
python src/historical_importer.py  # Import
python src/generator.py            # Generate

# View
open docs/index.html

# Test
pytest tests/test_historical_importer.py -v

# View logs
tail -f historical_importer.log
tail -f generator.log
```

---

## 🎉 Final Result

```
BEFORE: 3 HTML pages 😐
AFTER: 2,690 HTML pages! 🚀🎉

BEFORE: Sitemap with 3 URLs 😐
AFTER: Sitemap with 2,691 URLs! 🚀🎉

BEFORE: Limited content 😐
AFTER: Robust SEO content base! 🚀🎉
```

---

**🔔 Success sound played when finished!**

*Glass.aiff - the macOS victory sound* 🎵

---

**Developed with ❤️ by the MatchFly team**

*January 12, 2026*
