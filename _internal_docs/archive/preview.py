#!/usr/bin/env python3
"""
Script simples para iniciar um servidor HTTP local para visualizar
o preview dos dados de flights-db.json.

Uso:
    python preview.py

O servidor será iniciado em http://localhost:8000
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

# Porta padrão
PORT = 8000

# Diretório base (pasta public/)
BASE_DIR = Path(__file__).parent / "public"

def main():
    # Verificar se a pasta public existe
    if not BASE_DIR.exists():
        print(f"❌ Erro: Pasta 'public' não encontrada em {BASE_DIR.parent}")
        sys.exit(1)
    
    # Mudar para o diretório public
    os.chdir(BASE_DIR)
    
    # Criar handler
    handler = http.server.SimpleHTTPRequestHandler
    
    # Criar servidor
    try:
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            print("=" * 60)
            print("🚀 Servidor de Preview iniciado!")
            print("=" * 60)
            print(f"📁 Diretório: {BASE_DIR}")
            print(f"🌐 URL: http://localhost:{PORT}")
            print(f"📄 Abra: http://localhost:{PORT}/index.html")
            print("=" * 60)
            print("💡 Pressione Ctrl+C para parar o servidor")
            print("=" * 60)
            
            httpd.serve_forever()
            
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Erro: Porta {PORT} já está em uso.")
            print(f"💡 Tente usar outra porta ou feche o processo que está usando a porta {PORT}")
        else:
            print(f"❌ Erro ao iniciar servidor: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor interrompido pelo usuário")
        sys.exit(0)

if __name__ == "__main__":
    main()
