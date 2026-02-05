# 🚀 Quick Start - GRU Airport Scraper

## Setup Rápido (5 minutos)

### 1️⃣ Clone e Configure

```bash
cd ~/matchfly

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 2️⃣ Execute o Scraper

```bash
python3 voos_proximos_finalbuild.py
```

### 3️⃣ Verifique os Resultados

```bash
# Ver dados extraídos
cat data/flights-db.json

# Ver logs
cat gru_scraper.log
```

## 📊 O que o Scraper Faz?

1. 🔍 **Descobre** endpoints de API do site gru.com.br
2. 📡 **Extrai** dados de voos (número, companhia, horários, status)
3. 🔎 **Filtra** apenas voos Cancelados ou Atrasados > 2h
4. 💾 **Salva** em `data/flights-db.json`
5. 📝 **Registra** tudo em `gru_scraper.log`

## 📁 Estrutura de Output

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

## 🎯 Casos de Uso

### Uso Básico
```bash
python3 voos_proximos_finalbuild.py
```

### Exemplos Interativos
```bash
python3 examples/example_usage.py
```

### Modo Programático
```python
from src.scrapers import GRUFlightScraper

scraper = GRUFlightScraper()
scraper.run()
```

## 🛠️ Customização Rápida

### Mudar arquivo de saída
```python
scraper = GRUFlightScraper(output_file="custom/path.json")
```

### Filtro customizado
```python
flights = scraper.fetch_flights()
custom = [f for f in flights if f['delay_hours'] > 3]
scraper.save_to_json(custom)
```

### Ativar modo DEBUG
```python
import logging
logging.getLogger('scrapers.gru_flights_scraper').setLevel(logging.DEBUG)
```

## 📚 Próximos Passos

- 📖 Leia a [documentação completa](docs/GRU_SCRAPER_USAGE.md)
- 🔍 Explore os [exemplos](examples/example_usage.py)
- ⚙️ Veja o [código fonte](src/scrapers/gru_flights_scraper.py)

## ❓ Problemas?

```bash
# Reinstalar dependências
pip install -r requirements.txt --force-reinstall

# Verificar logs
tail -f gru_scraper.log

# Modo debug
python3 -c "
from src.scrapers import GRUFlightScraper
import logging
logging.basicConfig(level=logging.DEBUG)
scraper = GRUFlightScraper()
scraper.run()
"
```

## ✨ Características

- ✅ **Sem Selenium** - Rápido e leve
- ✅ **API Discovery** - Encontra endpoints automaticamente
- ✅ **Robusto** - Tratamento completo de erros
- ✅ **Logging** - Console + arquivo
- ✅ **Filtros** - Cancelados e atrasados
- ✅ **JSON** - Formato estruturado
- ✅ **Modular** - Fácil de estender

---

**Tempo total**: ~5 minutos  
**Dificuldade**: ⭐ Fácil  
**Requisitos**: Python 3.9+

