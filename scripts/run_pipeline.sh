#!/bin/bash
# MatchFly Complete Pipeline (Updated)
# Scraping → Generation → Ready to Push

set -e  # Exit on error

echo "============================================================"
echo "  🚀 MatchFly Pipeline Local (Sincronizado)"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Run from repo root (so paths resolve correctly)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# Activate virtual environment
echo -e "${YELLOW}Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Step 1: Run scraper
echo ""
echo -e "${YELLOW}Passo 1: Executando scraper (voos_proximos_finalbuild.py)...${NC}"
python3 voos_proximos_finalbuild.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Scraping concluído com sucesso!${NC}"
else
    echo -e "${RED}Erro no scraping. Verifique voos_proximos_finalbuild.py${NC}"
    exit 1
fi

# Step 2: Generate pages
echo ""
echo -e "${YELLOW}🎨 Passo 2: Gerando páginas HTML...${NC}"
python3 src/generator.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Páginas geradas na pasta docs/${NC}"
else
    echo -e "${RED}❌ Erro na geração!${NC}"
    exit 1
fi

# Step 2.5: Index URLs to Google (indexer.py movido para backup; opcional)
# echo ""
# echo -e "${YELLOW}🔍 Passo 2.5: Indexando URLs na Google Indexing API (opcional)...${NC}"
# if [ -f "credentials/service_account.json" ]; then
#     python3 src/indexer.py
#     ...
# fi

# Step 3: Show statistics
echo ""
echo -e "${YELLOW}📊 Passo 3: Estatísticas${NC}"
echo ""
echo "Voos coletados:"
cat data/flights-db.json | grep -o '"flight_number"' | wc -l

echo ""
echo "Páginas geradas:"
ls docs/*.html 2>/dev/null | wc -l

echo ""
echo "Diretório: $(pwd)/docs/"

# Optional: Open in browser
echo ""
read -p "Abrir no navegador para testar? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open docs/index.html
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open docs/index.html
    fi
fi

echo ""
echo "============================================================"
echo -e "${GREEN}✅ Tudo pronto! Seu ambiente local está igual ao servidor.${NC}"
echo "============================================================"
echo ""
echo "Para publicar as mudanças, rode:"
echo -e "${YELLOW}  git add .${NC}"
echo -e "${YELLOW}  git commit -m \"update: dados atualizados localmente\"${NC}"
echo -e "${YELLOW}  git push origin main${NC}"
echo ""
