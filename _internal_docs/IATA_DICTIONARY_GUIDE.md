# 📖 IATA Dictionary Guide - MatchFly

## 🎯 Objective

The `CITY_TO_IATA` dictionary maps city names to IATA airport codes, allowing the AirHelp funnel link to be automatically pre-filled, increasing conversion rate.

## 📍 Location

**File:** `src/generator.py`  
**Lines:** 45-74 (dictionary) and 118-143 (search function)

## 🔧 How It Works

### 1. Case-Insensitive Search

The `get_iata_code()` function normalizes input before searching:

```python
# All these inputs return "CDG":
get_iata_code("Paris")      # → "CDG"
get_iata_code("PARIS")      # → "CDG"
get_iata_code("paris")      # → "CDG"
get_iata_code("  Paris  ")  # → "CDG"
```

### 2. Dictionary Format

```python
CITY_TO_IATA = {
    # All keys must be in LOWERCASE
    "paris": "CDG",           # ✅ Correct
    "rio de janeiro": "GIG",  # ✅ Correct
    "foz do iguaçu": "IGU",   # ✅ Accepts accents
    
    # ❌ DON'T use uppercase in keys:
    # "PARIS": "CDG",         # Wrong
    # "Paris": "CDG",         # Wrong
}
```

### 3. Automatic Fallback

If city is not in dictionary:
- IATA code stays empty in link
- `departureAirportIata=GRU` always present
- User can fill manually in funnel

## ➕ How to Add New Destinations

### Step 1: Identify City and IATA Code

Check generator logs to see unmapped cities:

```bash
grep "Cidade não mapeada" generator.log
```

Search IATA code at:
- [IATA Airport Codes](https://www.iata.org/en/publications/directories/code-search/)
- [Wikipedia - List of IATA codes](https://en.wikipedia.org/wiki/List_of_IATA_airport_codes)

### Step 2: Add to Dictionary

Edit `src/generator.py` and add new entry:

```python
CITY_TO_IATA = {
    # ... existing entries ...
    
    # New entry (always lowercase!)
    "nova cidade": "ABC",
    "new city": "ABC",  # Add variations if needed
}
```

### Step 3: Update Brazilian Airports List (if applicable)

If it's a Brazilian airport, also add to `BRAZILIAN_AIRPORTS`:

```python
BRAZILIAN_AIRPORTS = {
    "GRU", "GIG", "BSB", "SSA", # ... existing ...
    "ABC",  # New Brazilian airport
}
```

### Step 4: Test

```bash
# Manual test
python test_iata_mapping.py

# Unit test
python -m unittest tests.test_generator -v

# Complete test
python src/generator.py
```

## 📋 Maintenance Checklist

When adding new destinations:

- [ ] Dictionary key in **lowercase**
- [ ] IATA code in **UPPERCASE** (IATA standard)
- [ ] Add common variations (with/without accent, Portuguese/English)
- [ ] If Brazilian, add to `BRAZILIAN_AIRPORTS`
- [ ] Run `test_iata_mapping.py` to validate
- [ ] Check generator logs after deploy

## 🌍 Currently Covered Destinations

### International (20+)
- **Europe:** Paris, Lisbon, Madrid, London, Frankfurt, Rome, Barcelona, Amsterdam, Zurich, Milan
- **South America:** Buenos Aires, Santiago, Lima, Bogotá, Montevideo
- **North America:** Miami, New York, Orlando, Los Angeles, Toronto, Mexico City, Panama

### National (20+)
- **Southeast:** Rio de Janeiro, Belo Horizonte, Vitória
- **South:** Porto Alegre, Curitiba, Florianópolis, Foz do Iguaçu
- **Northeast:** Salvador, Fortaleza, Recife, Natal, Maceió, Aracaju, Porto Seguro
- **North:** Manaus, Belém
- **Central-West:** Brasília, Goiânia, Cuiabá, Campo Grande

## 🔍 Monitoring

### See unmapped cities in logs:

```bash
grep "Cidade não mapeada" generator.log | sort | uniq -c | sort -rn
```

### See mapping statistics:

```bash
python test_iata_mapping.py
```

### Check generated links:

```bash
# See all generated affiliate links
grep -r "arrivalAirportIata=" docs/voo/*.html | grep -o "arrivalAirportIata=[A-Z]*" | sort | uniq -c
```

## 🐛 Troubleshooting

### Problem: City is not being mapped

**Solution:**
1. Verify key is lowercase in dictionary
2. Check for accents or special characters
3. Test with `get_iata_code("city name")` directly

### Problem: Link without destination IATA code

**Cause:** Unmapped city (expected behavior - fallback)

**Solution:** Add city to dictionary following guide above

### Problem: Wrong IATA code

**Solution:**
1. Verify IATA code is correct at [IATA.org](https://www.iata.org/)
2. Fix in dictionary
3. Run `python src/generator.py` again

## 📊 Success Metrics

Monitor these metrics to evaluate impact:

1. **Mapping rate:** What % of flights have mapped IATA code
2. **AirHelp link CTR:** Click-through rate on CTA button
3. **Funnel conversion:** % of users who complete form
4. **AirHelp commissions:** Increase in received commissions

## 📚 References

- [IATA Airport Codes](https://www.iata.org/en/publications/directories/code-search/)
- [AirHelp API Documentation](https://funnel.airhelp.com/claims/new/trip-details)
- [MatchFly Generator Architecture](GENERATOR_GUIDE.md)

## 🆘 Support

If you encounter issues or have questions:
1. Check logs: `generator.log`
2. Run tests: `python test_iata_mapping.py`
3. Consult this guide
4. Review code in `src/generator.py` (well documented)

---

**Last updated:** 2026-01-12  
**Generator Version:** 2.0.0
