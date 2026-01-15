#!/usr/bin/env python3
"""
Script de execução rápida para importação histórica da ANAC
Automatiza o workflow completo: Importar → Gerar → Validar
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Executa comando e exibe resultado."""
    print(f"\n{'='*70}")
    print(f"🚀 {description}")
    print(f"{'='*70}\n")
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode != 0:
        print(f"\n❌ Erro ao executar: {description}")
        return False
    
    return True

def main():
    """Executa workflow completo de importação."""
    
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "🔄 MATCHFLY - IMPORTAÇÃO HISTÓRICA" + " " * 18 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print("Este script vai:")
    print("  1. Importar dados históricos da ANAC (últimos 30 dias)")
    print("  2. Gerar páginas HTML com os dados importados")
    print("  3. Validar o resultado")
    print()
    
    # Confirma execução
    response = input("Deseja continuar? [S/n]: ").strip().lower()
    if response and response not in ['s', 'sim', 'y', 'yes']:
        print("❌ Importação cancelada pelo usuário")
        return False
    
    # STEP 1: Importar dados históricos
    if not run_command(
        "python src/historical_importer.py",
        "STEP 1: Importando dados históricos da ANAC"
    ):
        return False
    
    # STEP 2: Gerar páginas HTML
    if not run_command(
        "python src/generator.py",
        "STEP 2: Gerando páginas HTML"
    ):
        return False
    
    # STEP 3: Validar resultado
    print(f"\n{'='*70}")
    print("🔍 STEP 3: Validando resultado")
    print(f"{'='*70}\n")
    
    # Verifica arquivos gerados
    public_dir = Path("public")
    voo_dir = public_dir / "voo"
    
    if not public_dir.exists():
        print("❌ Diretório public/ não encontrado")
        return False
    
    index_file = public_dir / "index.html"
    sitemap_file = public_dir / "sitemap.xml"
    
    if not index_file.exists():
        print("❌ Arquivo index.html não foi gerado")
        return False
    
    if not sitemap_file.exists():
        print("❌ Arquivo sitemap.xml não foi gerado")
        return False
    
    # Conta páginas geradas
    if voo_dir.exists():
        html_files = list(voo_dir.glob("*.html"))
        num_pages = len(html_files)
    else:
        num_pages = 0
    
    print("✅ Validação concluída!")
    print()
    print(f"📊 Resultado:")
    print(f"   • Páginas de voos geradas: {num_pages}")
    print(f"   • Index.html: ✓")
    print(f"   • Sitemap.xml: ✓")
    print()
    
    if num_pages > 0:
        print("🎉 SUCESSO! Importação e geração concluídas!")
        print()
        print("🌐 Para visualizar:")
        print(f"   open {index_file}")
        print()
        print("📦 Para fazer deploy:")
        print("   git add .")
        print('   git commit -m "feat: importar dados históricos ANAC"')
        print("   git push")
        print()
        
        # Toca som de sucesso
        try:
            subprocess.run(
                ['afplay', '/System/Library/Sounds/Glass.aiff'],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass
        
        return True
    else:
        print("⚠️  Nenhuma página foi gerada. Verifique os logs.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
