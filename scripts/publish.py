import os
import subprocess
import sys

def run_command(command, description):
    print(f"\n🚀 {description}...")
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"✅ {description} concluído com sucesso.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar {description}.")
        print(f"Detalhes: {e}")
        sys.exit(1)

def main():
    print("╔════════════════════════════════════════╗")
    print("║      MATCHFLY - DEPLOY AUTOMÁTICO      ║")
    print("╚════════════════════════════════════════╝")

    # 1. Gerar o Site
    # Roda o generator para garantir que o HTML está fresco e atualizado
    run_command("python src/generator.py", "Gerando arquivos HTML (Build)")

    # 2. Verificar se o build funcionou
    if not os.path.exists("public/index.html"):
        print("❌ Erro: Arquivo public/index.html não encontrado. O build falhou.")
        sys.exit(1)

    # 3. Publicar no GitHub Pages
    # Usa ghp-import para enviar a pasta 'public' para a branch 'gh-pages'
    # -n: Inclui .nojekyll
    # -p: Faz o push
    # -f: Força a atualização
    deploy_cmd = "ghp-import -n -p -f public -c matchfly.org -m 'Deploy automático via publish.py'"
    run_command(deploy_cmd, "Publicando no GitHub Pages (Branch gh-pages)")

    print("\n✨ Site publicado com sucesso! Acesse: [https://matchfly.org](https://matchfly.org)")

if __name__ == "__main__":
    main()
