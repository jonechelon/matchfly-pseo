import os
from playwright.sync_api import sync_playwright

# Isso resolve o erro de permissão (EACCES)
os.environ["TMPDIR"] = os.path.expanduser("~/Downloads")

with sync_playwright() as p:
    print("Iniciando o navegador...")
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("Acessando o site...")
    page.goto("https://example.com")
    
    title = page.title()
    print(f"Sucesso! O título da página é: {title}")
    
    browser.close()
