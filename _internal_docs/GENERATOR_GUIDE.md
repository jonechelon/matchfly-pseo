# 🎨 ANAC 400 Page Generator Guide

## 📖 Overview

The **MatchFly Page Generator** is a CRO (Conversion Rate Optimization) oriented static page generation system that transforms problematic flight data into conversion and SEO optimized landing pages.

## ✨ Template Features

### 🎯 Template: tier2-anac400.html

**Style:** Public Utility (Clean, Official)
**Color Palette:**
- Dark Blue (#1e3a8a) - Main brand
- Light Blue (#3b82f6) - Highlights
- Light Gray (#f3f4f6) - Background
- White - Base

### 📊 CRO Elements Implemented

#### 1. **Data Freshness Badge**
```html
<span class="text-xs text-gray-600 font-medium">
    Updated {{ hours_ago }}h ago
</span>
```
- Creates urgency and trust
- Automatic update based on scraping timestamp

#### 2. **High-Impact H1**
```html
Was Flight {{ flight_number }} from {{ airline }} Cancelled or Delayed?
```
- Specific to the flight
- Personalized by airline
- Focus on user pain point

#### 3. **Self-Assessment with Interactive Checkboxes**
```javascript
function checkAllBoxes() {
    // When all 3 boxes are checked:
    // ✅ Adds pulse animation to CTA
    // ✅ Shows success message
    // ✅ Auto-scrolls to CTA
}
```

**Checkboxes:**
- [ ] Airline didn't offer assistance?
- [ ] Flight cancelled or delayed > 4h?
- [ ] Occurred in the last 2 years?

**Behavior:**
- ✅ Gradual commitment (foot-in-the-door)
- ✅ Pulse animation when complete
- ✅ Auto-check if delay >= 4h

#### 4. **ANAC Rights Table**
Clear educational information:
- ⏱️ 1h: Communication
- 🍔 2h: Food
- 🏨 4h: Accommodation + **Compensation**

#### 5. **Optimized CTA**
```html
CHECK MY COMPENSATION →
```
- Vibrant color with contrast
- Full width on mobile
- Trust badges (100% Secure, No Costs, 97% Success)
- Clear disclaimer

#### 6. **SEO & Schema.org**

**BroadcastEvent Schema:**
```json
{
    "@type": "BroadcastEvent",
    "eventStatus": "EventCancelled",
    "startDate": "{{ departure_time }}",
    "location": "{{ origin }}"
}
```

**FAQPage Schema:**
3 questions optimized for featured snippets:
1. How to receive ANAC 400 compensation?
2. How long does it take?
3. Do I need to pay anything?

## 🔧 How to Use the Generator

### 1️⃣ Initial Setup

#### Edit Affiliate Link

**File:** `src/generator.py`

```python
# Line ~350
AFFILIATE_LINK = "https://www.compensair.com/compensation?ref=matchfly&flight={flight_number}"
```

⚠️ **IMPORTANT:** The generator will NOT run without a valid affiliate link!

### 2️⃣ Run Generation

```bash
# Method 1: Directly
cd ~/matchfly
source venv/bin/activate
python3 src/generator.py

# Method 2: Via import
from src.generator import FlightPageGenerator

generator = FlightPageGenerator(
    data_file="data/flights-db.json",
    template_file="src/templates/tier2-anac400.html",
    output_dir="public",
    affiliate_link="https://..."
)

stats = generator.run()
```

### 3️⃣ Verify Output

```bash
# List generated pages
ls -la docs/

# Open in browser
open docs/index.html  # macOS
xdg-open docs/index.html  # Linux
start docs/index.html  # Windows
```

## 📁 Generated File Structure

```
docs/
├── index.html                          # Index page with all flights
├── voo-latam-la3090-gru-atrasado.html  # Individual page
├── voo-gol-g31447-gru-cancelado.html
├── voo-azul-ad4123-gru-atrasado.html
└── ...
```

### Slug Format

**Pattern:** `voo-{airline}-{flight_number}-{origin}-{status}.html`

**Examples:**
- `voo-latam-la3090-gru-atrasado.html`
- `voo-gol-g31447-gru-cancelado.html`
- `voo-azul-ad4123-gru-atrasado.html`

**SEO Optimizations:**
- ✅ Automatic slugify (removes accents, special characters)
- ✅ Lowercase for consistency
- ✅ Relevant keywords (voo, airline, number, origin, status)

## 🎨 Template Variables

### Required Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `flight_number` | string | Flight number | "LA3090" |
| `airline` | string | Airline | "LATAM" |
| `status` | string | Flight status | "Atrasado" |
| `delay_hours` | float | Delay hours | 2.5 |
| `hours_ago` | int | Hours since scraping | 0 |
| `affiliate_link` | string | Conversion link | "https://..." |

### Optional Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `origin` | string | "GRU" | Origin airport |
| `destination` | string | "N/A" | Destination airport |
| `scheduled_time` | string | "N/A" | Scheduled time |
| `actual_time` | string | "N/A" | Actual time |
| `departure_time` | string | now() | For schema.org |
| `scraped_at` | string | now() | Scraping timestamp |
| `generated_at` | string | now() | Generation timestamp |

## 🛡️ Implemented Validations

### 1. Affiliate Link Validation

```python
if not self.affiliate_link or self.affiliate_link.strip() == "":
    logger.error("❌ CRITICAL ERROR: affiliate_link is empty!")
    return self.stats
```

**Reason:** Avoid pages without monetization.

### 2. Flight Validation

```python
def validate_flight(self, flight: Dict) -> bool:
    required_fields = ['flight_number', 'airline', 'status']
    for field in required_fields:
        if not flight.get(field):
            return False
    return True
```

**Required Fields:**
- `flight_number`
- `airline`
- `status`

### 3. Hours Ago Calculation

```python
def calculate_hours_ago(self, scraped_at: str) -> int:
    scraped_dt = datetime.fromisoformat(scraped_at)
    now = datetime.now()
    delta = now - scraped_dt
    hours = int(delta.total_seconds() / 3600)
    return max(0, hours)
```

**Treatment:**
- Flexible timestamp parsing
- Doesn't return negative values
- Fallback to 0 on error

## 📊 Generation Statistics

The generator provides detailed statistics:

```python
{
    'total_flights': 5,
    'pages_generated': 5,
    'skipped_no_affiliate': 0,
    'skipped_invalid': 0,
    'errors': 0
}
```

**Generated Logs:**
- `generator.log` - Complete execution history
- Console output - Real-time status

## 🎯 CRO Optimizations

### Applied Psychology

#### 1. **Gradual Commitment (Foot-in-the-Door)**
Checkboxes create micro-commitments before the main CTA.

#### 2. **Urgency & Scarcity**
- Badge "Updated Xh ago"
- Red status (Cancelled/Delayed)

#### 3. **Social Proof**
- "97% Success Rate"
- Trust badges

#### 4. **Risk Reduction**
- "100% Free"
- "No upfront costs"
- "You only pay if you win"

### Mobile-First Design

- ✅ Large checkboxes (easy to tap)
- ✅ Full-width CTA on mobile
- ✅ Generous spacing
- ✅ Readable font (>16px)
- ✅ Sticky header

### Performance

- ✅ Tailwind CSS via CDN (browser cache)
- ✅ No heavy JavaScript
- ✅ Static HTML (fast)
- ✅ Lazy loading images (if added)

## 🚀 Complete Workflow

### Step by Step

```bash
# 1. Run scraper
python3 voos_proximos_finalbuild.py

# Output: data/flights-db.json

# 2. Configure affiliate link
# Edit src/generator.py line ~350

# 3. Generate pages
python3 src/generator.py

# Output: docs/*.html

# 4. Test locally
open docs/index.html

# 5. Deploy (choose one):
# - Netlify: drag docs/ folder
# - Vercel: vercel --prod
# - GitHub Pages: git push
# - S3 + CloudFront: aws s3 sync docs/ s3://bucket
```

## 📈 Recommended Metrics

### Conversion Tracking

**Add to template:**

```javascript
// Google Analytics 4
gtag('event', 'click', {
    'event_category': 'CTA',
    'event_label': 'Check Compensation',
    'flight_number': '{{ flight_number }}',
    'airline': '{{ airline }}'
});

// Facebook Pixel
fbq('track', 'Lead', {
    flight: '{{ flight_number }}',
    value: 10000,
    currency: 'BRL'
});
```

### A/B Testing Ideas

1. **Headline:**
   - A: "Was flight X cancelled?"
   - B: "Did you miss flight X?"

2. **CTA:**
   - A: "Check Compensation"
   - B: "Calculate My Compensation"

3. **Colors:**
   - A: Professional blue
   - B: "Money" green

## 🐛 Troubleshooting

### Error: "affiliate_link is empty"

**Cause:** AFFILIATE_LINK not configured

**Solution:**
```python
# src/generator.py, line ~350
AFFILIATE_LINK = "https://your-link-here.com"
```

### Error: "Template not found"

**Cause:** Incorrect path

**Solution:**
```bash
# Check structure
ls -la src/templates/tier2-anac400.html
```

### Pages not generating

**Cause:** Invalid data

**Solution:**
```bash
# Check JSON
python3 -m json.tool data/flights-db.json

# Check required fields
cat data/flights-db.json | jq '.flights[] | {flight_number, airline, status}'
```

### Hours_ago always 0

**Cause:** Timestamp format

**Solution:**
```python
# Check format in flights-db.json
# Should be: "2026-01-11T18:34:35.005828"
```

## 📚 Additional Resources

### References

- [ANAC Resolution 400](https://www.gov.br/anac/pt-br)
- [Schema.org Event](https://schema.org/Event)
- [Schema.org FAQPage](https://schema.org/FAQPage)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Jinja2 Template Designer](https://jinja.palletsprojects.com/)

### Affiliate Program Examples

- **CompensAir:** Up to 25% commission
- **AirHelp:** €25-30 per approved case
- **ClaimCompass:** 20-30% commission
- **FlightRight:** CPA model

## 🎓 Best Practices

### DO ✅

- ✅ Always configure affiliate_link
- ✅ Test pages locally before deploy
- ✅ Keep data updated (run scraper regularly)
- ✅ Monitor conversion metrics
- ✅ A/B test headlines and CTAs
- ✅ Optimize for mobile-first

### DON'T ❌

- ❌ Generate pages without affiliate link
- ❌ Use outdated data (> 24h)
- ❌ Ignore SEO validations
- ❌ Forget to test on mobile
- ❌ Deploy without testing locally
- ❌ Ignore error logs

## 🚀 Next Steps

### Future Improvements

1. **Template Variations:**
   - Tier 1: Simple listing
   - Tier 2: ANAC 400 (current)
   - Tier 3: Emotional story + testimonials

2. **Personalization:**
   - Detect user city (geo-targeting)
   - Dynamic prices based on route
   - Airline problem history

3. **Automation:**
   - Cronjob for automatic scraping + generation
   - Webhook for new flight notifications
   - Auto-deploy to production

4. **Analytics:**
   - Conversion dashboard per flight
   - Click heatmaps
   - Detailed conversion funnel

---

**Version:** 1.0.0  
**Last Updated:** 2026-01-11  
**Author:** MatchFly Team
