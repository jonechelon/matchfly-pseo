#!/bin/bash
# MatchFly Complete Pipeline
# Scraping → Generation → Deploy

set -e  # Exit on error

echo "============================================================"
echo "  🚀 MatchFly Complete Pipeline"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Activate virtual environment
echo -e "${YELLOW}📦 Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Step 1: Run scraper
echo ""
echo -e "${YELLOW}🛫 Passo 1: Executando scraper GRU...${NC}"
python3 run_gru_scraper.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Scraping concluído!${NC}"
else
    echo -e "${RED}❌ Erro no scraping!${NC}"
    exit 1
fi

# Step 2: Generate pages
echo ""
echo -e "${YELLOW}🎨 Passo 2: Gerando páginas HTML...${NC}"
python3 src/generator.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Páginas geradas!${NC}"
else
    echo -e "${RED}❌ Erro na geração!${NC}"
    exit 1
fi

# Step 3: Show statistics
echo ""
echo -e "${YELLOW}📊 Passo 3: Estatísticas${NC}"
echo ""
echo "Voos coletados:"
cat data/flights-db.json | grep -o '"flight_number"' | wc -l

echo ""
echo "Páginas geradas:"
ls public/*.html 2>/dev/null | wc -l

echo ""
echo "Diretório: $(pwd)/public/"

# Optional: Open in browser
echo ""
read -p "Abrir no navegador? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open public/index.html
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open public/index.html
    fi
fi

echo ""
echo "============================================================"
echo -e "${GREEN}✅ Pipeline completo executado com sucesso!${NC}"
echo "============================================================"
echo ""
echo "Próximos passos:"
echo "  1. Testar páginas em public/"
echo "  2. Fazer deploy (Netlify, Vercel, etc)"
echo "  3. Configurar cronjob para execução automática"
echo ""

