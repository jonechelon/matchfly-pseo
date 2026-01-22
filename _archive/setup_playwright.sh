#!/bin/bash
# Script de instalação do Playwright Chromium
# Usado para configurar o ambiente antes de executar scrapers

echo "🔧 Instalando Playwright Chromium..."
playwright install chromium

if [ $? -eq 0 ]; then
    echo "✅ Playwright Chromium instalado com sucesso!"
else
    echo "❌ Erro ao instalar Playwright Chromium"
    exit 1
fi
