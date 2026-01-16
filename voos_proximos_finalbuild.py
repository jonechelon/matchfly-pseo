#!/usr/bin/env python3
"""
Script de Scraping GRU via HTML - Versão Inteligente com pSEO
===============================================================

Funcionalidades:
1. Criação imediata do CSV com cabeçalhos corretos
2. Memória ativa (carrega CSV existente para evitar duplicatas)
3. Lógica precisa de destino (não confunde com companhia)
4. Extração de companhia de imagens (alt/src)
5. Monitoramento de ciclo de vida dos voos
6. Cálculo de alertas de atraso (1H e 2H)
7. Logs de debug detalhados

REQUISITOS:
- Playwright instalado: pip install playwright && playwright install chromium
"""

import csv
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    import pandas as pd
except ImportError:
    print("❌ Erro: pandas não está instalado.")
    print("   Execute: pip install pandas")
    sys.exit(1)

# PERMISSÕES macOS: Define TMPDIR para evitar erros de permissão
os.environ["TMPDIR"] = os.path.expanduser("~/Downloads")

# MODIFICAÇÃO 1: Cria diretório para logs imediatamente
LOG_DIR = 'logs_voos_atrasados'
os.makedirs(LOG_DIR, exist_ok=True)

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Route
except ImportError:
    print("❌ Erro: Playwright não está instalado.")
    print("   Execute: pip install playwright && playwright install chromium")
    sys.exit(1)


# Configurações
CSV_COLUMNS = [
    "databusca",  # Primeira coluna: timestamp da busca
    "Data",
    "Horario_Previsto",
    "Horario_Estimado",
    "Voo",
    "Companhia",
    "Destino",
    "Status",
    "Alerta_1H",
    "Alerta_2H",
    "Status_Monitoramento",
]

# Caminho do CSV persistente (na raiz) - arquivo principal de histórico
PERSISTENT_CSV_PATH = os.path.join(os.path.dirname(__file__), "voos_atrasados_gru.csv")

# Caminho do CSV antigo (na raiz) para migração (mantido para compatibilidade)
OLD_CSV_PATH = PERSISTENT_CSV_PATH

# Lista de companhias conhecidas (para filtro de destino incorreto)
COMPANHIAS_CONHECIDAS = {
    "LATAM", "TAM", "GOL", "AZUL", "EMIRATES", "TURKISH", "TURKISH AIRLINES",
    "BRITISH", "BRITISH AIRWAYS", "AIR FRANCE", "AIRFRANCE", "KLM", "LUFTHANSA",
    "AMERICAN", "AMERICAN AIRLINES", "DELTA", "UNITED"
}


def load_all_historical_data() -> List[Dict[str, str]]:
    """
    Carrega TODOS os dados históricos de CSVs anteriores e do CSV antigo.
    
    Returns:
        Lista completa de todos os voos históricos
    """
    all_historical = []
    
    # 1. Migra dados do CSV antigo (formato antigo na raiz)
    migrated_flights = migrate_old_csv_data()
    all_historical.extend(migrated_flights)
    
    # 2. Carrega dados de CSVs anteriores (com timestamp no nome)
    try:
        if os.path.exists(LOG_DIR):
            csv_files = [f for f in os.listdir(LOG_DIR) if f.startswith('voos_atrasados_') and f.endswith('.csv')]
            # Ordena por nome (timestamp) - mais recente primeiro
            csv_files.sort(reverse=True)
            
            for csv_file in csv_files:
                csv_path = os.path.join(LOG_DIR, csv_file)
                try:
                    with open(csv_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Valida dados
                            voo = str(row.get('Voo', '')).strip()
                            horario = str(row.get('Horario_Previsto', '')).strip()
                            if voo and horario and voo != 'N/A' and horario != 'N/A':
                                all_historical.append(row)
                except Exception as e:
                    print(f"   ⚠️  Erro ao carregar {csv_file}: {e}")
    except Exception as e:
        print(f"   ⚠️  Erro ao carregar CSVs históricos: {e}")
    
    return all_historical


def create_csv_with_timestamp() -> str:
    """
    Cria novo CSV com timestamp no nome do arquivo.
    
    Returns:
        Caminho completo do arquivo CSV criado
    """
    # Gera nome com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f"voos_atrasados_{timestamp}.csv"
    csv_file_path = os.path.join(LOG_DIR, csv_filename)
    
    try:
        # Cria arquivo novo com cabeçalhos
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)
            f.flush()
            os.fsync(f.fileno())
        
        abs_path = os.path.abspath(csv_file_path)
        print(f"🚀 ARQUIVO CRIADO EM: {abs_path}")
        
        return csv_file_path
        
    except Exception as e:
        print(f"❌ ERRO ao criar CSV: {e}")
        print(f"   Caminho tentado: {os.path.abspath(csv_file_path)}")
        import traceback
        traceback.print_exc()
        raise


def migrate_old_csv_data() -> List[Dict[str, str]]:
    """
    Migra dados do CSV antigo (formato antigo) para o novo formato.
    
    CSV antigo: Data_Captura, Horario, Companhia, Numero_Voo, Destino_Origem, Status
    Novo formato: databusca, Data, Horario_Previsto, Horario_Estimado, Voo, Companhia, Destino, Status, Alerta_1H, Alerta_2H, Status_Monitoramento
    
    NOTA: Esta função é para migração do formato antigo (com Destino_Origem) para o novo formato interno.
    O CSV persistente agora usa Operado_Por, Data_Partida, Hora_Partida.
    """
    migrated_flights = []
    
    if not os.path.exists(OLD_CSV_PATH):
        return migrated_flights
    
    try:
        print(f"   📂 Migrando dados do CSV antigo: {OLD_CSV_PATH}")
        with open(OLD_CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Mapeia dados antigos para novo formato
                data_captura = str(row.get('Data_Captura', '')).strip()
                horario = str(row.get('Horario', '')).strip()
                companhia = str(row.get('Companhia', '')).strip()
                numero_voo = str(row.get('Numero_Voo', '')).strip()
                # Suporta tanto Destino_Origem (antigo) quanto Operado_Por (novo)
                destino_origem = str(row.get('Destino_Origem', row.get('Operado_Por', ''))).strip()
                status = str(row.get('Status', '')).strip()
                
                # Usa Data_Captura como databusca (se não tiver horário, adiciona 00:00:00)
                if data_captura:
                    databusca = f"{data_captura} 00:00:00"
                else:
                    databusca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Calcula alertas
                alerta_1h, alerta_2h, _ = calculate_delay_alerts(horario, "N/A")
                
                # Filtra destino incorreto (companhias aéreas não devem estar em Destino)
                destino = destino_origem
                if destino_origem in COMPANHIAS_CONHECIDAS:
                    destino = "N/A"  # Remove companhia aérea do destino
                
                # Prepara dados no novo formato
                flight_data = {
                    "databusca": databusca,
                    "Data": data_captura,
                    "Horario_Previsto": horario,
                    "Horario_Estimado": "N/A",
                    "Voo": numero_voo,
                    "Companhia": companhia if companhia != 'N/A' else "N/A",
                    "Destino": destino,
                    "Status": status,
                    "Alerta_1H": alerta_1h,
                    "Alerta_2H": alerta_2h,
                    "Status_Monitoramento": "Ativo",
                }
                
                migrated_flights.append(flight_data)
        
        print(f"   ✅ {len(migrated_flights)} voo(s) migrado(s) do CSV antigo")
    except Exception as e:
        print(f"   ⚠️  Erro ao migrar CSV antigo: {e}")
        import traceback
        traceback.print_exc()
    
    return migrated_flights


def load_existing_flights(csv_path: str) -> List[Dict[str, str]]:
    """
    Carrega voos existentes do CSV (retorna lista completa).
    
    Returns:
        Lista de todos os voos existentes no CSV
    """
    existing = []
    
    if not csv_path or not os.path.exists(csv_path):
        return existing
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Valida se tem dados mínimos
                voo = str(row.get('Voo', '')).strip()
                horario = str(row.get('Horario_Previsto', '')).strip()
                if voo and horario and voo != 'N/A' and horario != 'N/A':
                    existing.append(row)
    except Exception as e:
        print(f"⚠️  Erro ao carregar CSV existente: {e}")
        import traceback
        traceback.print_exc()
    
    return existing


def remove_duplicates(flights: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Remove duplicados: mesmo Voo + Data, mantendo o mais recente (por databusca).
    
    Args:
        flights: Lista de voos
        
    Returns:
        Lista sem duplicados (mantém o mais recente)
    """
    # Agrupa por chave: Voo + Data (sem horário)
    grouped = {}
    
    for flight in flights:
        voo = str(flight.get('Voo', '')).strip()
        data = str(flight.get('Data', '')).strip()
        databusca = str(flight.get('databusca', '')).strip()
        
        if not voo or not data or voo == 'N/A' or data == 'N/A':
            continue
        
        key = f"{voo}|{data}"
        
        # Se não existe ou se este é mais recente (databusca maior), substitui
        if key not in grouped:
            grouped[key] = flight
        else:
            existing_databusca = str(grouped[key].get('databusca', '')).strip()
            if databusca > existing_databusca:
                grouped[key] = flight
    
    return list(grouped.values())


def calculate_delay_alerts(horario_previsto: str, horario_estimado: str = "N/A") -> tuple:
    """
    REQUISITO 3: Calcula alertas de atraso (1H e 2H).
    
    Compara Horario_Previsto com hora atual ou Horario_Estimado.
    
    Returns:
        (alerta_1h, alerta_2h, atraso_minutos)
    """
    try:
        if horario_previsto == "N/A" or not horario_previsto:
            return "NÃO", "NÃO", 0
        
        # Parse do horário previsto
        hora, minuto = map(int, horario_previsto.split(':'))
        previsto = datetime.now().replace(hour=hora, minute=minuto, second=0, microsecond=0)
        
        # Se tem horário estimado, usa ele para calcular atraso
        if horario_estimado != "N/A" and horario_estimado:
            try:
                hora_est, min_est = map(int, horario_estimado.split(':'))
                estimado = datetime.now().replace(hour=hora_est, minute=min_est, second=0, microsecond=0)
                
                # Se o horário estimado é do dia anterior, ajusta
                if estimado < previsto:
                    estimado = estimado + timedelta(days=1)
                
                atraso_minutos = (estimado - previsto).total_seconds() / 60
            except Exception:
                # Fallback: usa hora atual
                agora = datetime.now()
                if previsto > agora + timedelta(hours=12):
                    previsto = previsto - timedelta(days=1)
                elif previsto < agora - timedelta(hours=12):
                    previsto = previsto + timedelta(days=1)
                atraso_minutos = (agora - previsto).total_seconds() / 60
        else:
            # Usa hora atual
            agora = datetime.now()
            if previsto > agora + timedelta(hours=12):
                previsto = previsto - timedelta(days=1)
            elif previsto < agora - timedelta(hours=12):
                previsto = previsto + timedelta(days=1)
            atraso_minutos = (agora - previsto).total_seconds() / 60
        
        alerta_1h = "SIM" if atraso_minutos > 60 else "NÃO"
        alerta_2h = "SIM" if atraso_minutos > 120 else "NÃO"
        
        return alerta_1h, alerta_2h, int(atraso_minutos) if atraso_minutos > 0 else 0
    except Exception:
        return "NÃO", "NÃO", 0


def extract_company_from_img(block) -> str:
    """
    REQUISITO 2: Extrai companhia APENAS de atributo 'alt' ou 'src' das imagens.
    """
    try:
        images = block.query_selector_all("img")
        for img in images:
            src = (img.get_attribute("src") or "").lower()
            alt = (img.get_attribute("alt") or "").lower()
            
            # Remove palavras comuns
            src_clean = re.sub(r'\b(logo|imagem|image|icon|ícone)\b', '', src, flags=re.IGNORECASE)
            alt_clean = re.sub(r'\b(logo|imagem|image|icon|ícone)\b', '', alt, flags=re.IGNORECASE)
            
            # Mapeamento
            text_to_check = f"{src_clean} {alt_clean}"
            
            if "latam" in text_to_check or "tam" in text_to_check:
                return "LATAM"
            elif "gol" in text_to_check:
                return "GOL"
            elif "azul" in text_to_check:
                return "AZUL"
            elif "emirates" in text_to_check:
                return "EMIRATES"
            elif "turkish" in text_to_check:
                return "TURKISH AIRLINES"
            elif "british" in text_to_check:
                return "BRITISH AIRWAYS"
            elif "air france" in text_to_check or "airfrance" in text_to_check:
                return "AIR FRANCE"
            elif "klm" in text_to_check:
                return "KLM"
            elif "lufthansa" in text_to_check:
                return "LUFTHANSA"
            elif "american" in text_to_check:
                return "AMERICAN AIRLINES"
            elif "delta" in text_to_check:
                return "DELTA"
            elif "united" in text_to_check:
                return "UNITED"
    except Exception:
        pass
    
    return ""


def extract_company_from_text(block_text: str, voo: str) -> str:
    """
    Fallback: Extrai companhia do texto se imagem falhou.
    """
    try:
        text_upper = block_text.upper()
        
        if "LATAM" in text_upper or "TAM" in text_upper:
            return "LATAM"
        elif "GOL" in text_upper:
            return "GOL"
        elif "AZUL" in text_upper:
            return "AZUL"
        elif "EMIRATES" in text_upper:
            return "EMIRATES"
        elif "TURKISH" in text_upper:
            return "TURKISH AIRLINES"
        elif "BRITISH" in text_upper:
            return "BRITISH AIRWAYS"
        elif "AIR FRANCE" in text_upper or "AIRFRANCE" in text_upper:
            return "AIR FRANCE"
        elif "KLM" in text_upper:
            return "KLM"
        elif "LUFTHANSA" in text_upper:
            return "LUFTHANSA"
        elif "AMERICAN" in text_upper:
            return "AMERICAN AIRLINES"
        elif "DELTA" in text_upper:
            return "DELTA"
        elif "UNITED" in text_upper:
            return "UNITED"
        
        # Inferir do código do voo
        if voo and len(voo) >= 2:
            airline_codes = {
                "LA": "LATAM", "JJ": "LATAM", "4M": "LATAM",
                "G3": "GOL", "GOL": "GOL",
                "AD": "AZUL", "AZUL": "AZUL",
                "KL": "KLM", "AF": "AIR FRANCE",
                "LH": "LUFTHANSA", "BA": "BRITISH AIRWAYS",
                "EK": "EMIRATES", "TK": "TURKISH AIRLINES",
                "AA": "AMERICAN AIRLINES", "DL": "DELTA", "UA": "UNITED",
                "RJ": "AZUL"  # RJ geralmente é Azul
            }
            code = voo[:2].upper()
            return airline_codes.get(code, "N/A")
    except Exception:
        pass
    
    return "N/A"


def extract_destination(block_text: str) -> str:
    """
    REQUISITO 2: Extrai destino (código IATA ou cidade).
    
    Filtra nomes de companhias conhecidas.
    """
    try:
        # Busca por códigos de aeroporto (3 letras maiúsculas)
        airport_codes = re.findall(r'\b([A-Z]{3})\b', block_text)
        
        for code in airport_codes:
            # Ignora códigos comuns que não são aeroportos
            if code in ["GRU", "N/A", "API", "CSS", "HTML", "JPG", "PNG", "SVG"]:
                continue
            
            # REQUISITO 2: Filtro de precisão - não aceita nomes de companhias
            code_upper = code.upper()
            if code_upper in COMPANHIAS_CONHECIDAS or any(comp.upper() in code_upper for comp in COMPANHIAS_CONHECIDAS):
                continue
            
            # Códigos válidos de aeroportos brasileiros comuns
            valid_airports = {
                "SDU", "CGH", "GIG", "REC", "BSB", "FOR", "POA", "SSA",
                "BEL", "CNF", "FLN", "MAO", "PVH", "RBR", "AJU", "IOS",
                "CWB", "VIX", "THE", "IMP", "SLZ", "BVB", "JPA", "NAT",
                "CGB", "UDI", "GYN", "PMW", "BPS", "CPV", "FEN", "JDO"
            }
            
            # Se está na lista de válidos ou é um código que não é companhia
            if code in valid_airports:
                return code
            
            # Aceita qualquer código de 3 letras que não seja companhia conhecida
            # (pode ser aeroporto internacional)
            if len(code) == 3 and code.isalpha():
                return code
        
        # Fallback: busca por nomes de cidades comuns
        cities = re.findall(r'\b([A-Z][a-z]+)\b', block_text)
        city_keywords = {
            "Rio", "São", "Brasília", "Recife", "Salvador", "Belo", "Curitiba",
            "Porto", "Fortaleza", "Manaus", "Florianópolis", "Belém"
        }
        
        for city in cities:
            if any(keyword in city for keyword in city_keywords):
                return city
        
    except Exception:
        pass
    
    return "N/A"


def extract_flight_data(block) -> Optional[Dict[str, str]]:
    """
    Extrai dados de um container de voo.
    
    REQUISITO 4: Logs de DEBUG para cada linha processada.
    """
    try:
        block_text = block.inner_text().strip()
        
        if not block_text or len(block_text) < 10:
            return None
        
        # Extrai horários
        horarios = re.findall(r'\b(\d{1,2}:\d{2})\b', block_text)
        horario_previsto = horarios[0] if len(horarios) > 0 else "N/A"
        horario_estimado = horarios[1] if len(horarios) > 1 else "N/A"
        
        # Extrai número do voo
        voo_match = re.search(r'\b([A-Z]{2,3})\s*(\d{3,4})\b', block_text, re.IGNORECASE)
        if voo_match:
            voo = f"{voo_match.group(1).upper()}{voo_match.group(2)}"
        else:
            voo_match = re.search(r'\b(\d{4})\b', block_text)
            voo = voo_match.group(1) if voo_match else "N/A"
        
        # Extrai status
        status = "N/A"
        text_lower = block_text.lower()
        if "atrasado" in text_lower or "atraso" in text_lower:
            status_match = re.search(r'[Aa]trasado[^\s]*', block_text, re.IGNORECASE)
            status = status_match.group(0) if status_match else "Atrasado"
        elif "cancelado" in text_lower or "cancel" in text_lower:
            status_match = re.search(r'[Cc]ancelado[^\s]*', block_text, re.IGNORECASE)
            status = status_match.group(0) if status_match else "Cancelado"
        elif "embarcando" in text_lower or "embarque" in text_lower:
            status = "Embarque"
        elif "programado" in text_lower:
            status = "Programado"
        else:
            status = "Outro"
        
        # REQUISITO 2: Extrai companhia (prioriza imagens)
        companhia = extract_company_from_img(block)
        if not companhia or companhia == "":
            companhia = extract_company_from_text(block_text, voo)
        
        companhia = re.sub(r'\s+', ' ', companhia).strip()
        
        # REQUISITO 2: Extrai destino (com filtro de precisão)
        destino = extract_destination(block_text)
        
        # REQUISITO 4: Log de DEBUG para cada linha processada
        print(f"   DEBUG: Visto: Voo {voo} | Horário {horario_previsto} | Companhia {companhia} | Destino {destino} | Status {status}")
        
        return {
            "Horario_Previsto": horario_previsto,
            "Horario_Estimado": horario_estimado,
            "Voo": voo,
            "Companhia": companhia,
            "Destino": destino,
            "Status": status,
        }
    
    except Exception as e:
        print(f"   ❌ Erro ao extrair dados: {e}")
        return None


def find_flight_containers(page) -> List:
    """
    Identifica containers de voos (busca por "Detalhes" ou formato de hora).
    """
    flight_blocks = []
    
    print("   🔍 Buscando containers de voos...")
    
    try:
        # ESTRATÉGIA 1: Busca por texto "Detalhes"
        detalhes_elements = page.query_selector_all(":has-text('Detalhes')")
        
        if detalhes_elements and len(detalhes_elements) > 0:
            print(f"   ✅ Encontrados {len(detalhes_elements)} elemento(s) com 'Detalhes'")
            flight_blocks = list(detalhes_elements)
        else:
            # ESTRATÉGIA 2: Busca por formato de hora
            print("   📋 Buscando por formato de hora (XX:XX)...")
            all_divs = page.query_selector_all("div")
            
            for div in all_divs:
                try:
                    text = div.inner_text().strip()
                    if re.search(r'\b\d{1,2}:\d{2}\b', text) and 15 < len(text) < 500:
                        flight_blocks.append(div)
                except Exception:
                    continue
            
            if flight_blocks:
                print(f"   ✅ Encontrados {len(flight_blocks)} elemento(s) com formato de hora")
            else:
                print("   ❌ ERRO CRÍTICO: Não foi possível mapear a lista de voos.")
    
    except Exception as e:
        print(f"   ❌ Erro na busca de containers: {e}")
    
    return flight_blocks


def extract_flights_from_page(page) -> List[Dict[str, str]]:
    """
    Extrai todos os voos da página.
    """
    flights = []
    
    flight_blocks = find_flight_containers(page)
    
    if not flight_blocks:
        return flights
    
    print(f"   📋 Processando {len(flight_blocks)} container(s)...")
    
    for idx, block in enumerate(flight_blocks):
        flight_data = extract_flight_data(block)
        if flight_data:
            flights.append(flight_data)
    
    return flights


def scrape_gru_flights_html(
    max_load_more_clicks: int = 10,
    wait_between_clicks_ms: int = 2000,
    headless: bool = True
) -> List[Dict[str, str]]:
    """
    REQUISITO 4: Modo de execução com headless=True (sem interface gráfica).
    """
    VOOS_URL = "https://www.gru.com.br/pt/passageiro/voos"
    
    print("=" * 70)
    print("🌐 SCRAPING GRU - VERSÃO INTELIGENTE pSEO")
    print("=" * 70)
    print(f"   • URL: {VOOS_URL}")
    print(f"   • Modo visual: {'DESATIVADO' if headless else 'ATIVADO'}")
    print(f"   • Máximo de cliques 'Carregar mais': {max_load_more_clicks}")
    print()
    
    flights = []
    
    # CONFIGURAÇÃO DE SEGURANÇA CI/CD
    # Define pasta de downloads dentro do projeto, não na raiz do sistema
    download_path = os.path.join(os.getcwd(), "downloads_playwright")
    os.makedirs(download_path, exist_ok=True)
    print(f"📂 Diretório de downloads forçado: {download_path}")
    
    # --- CORREÇÃO CRÍTICA PARA GITHUB ACTIONS ---
    # O Playwright exige que ~/Downloads exista para artefatos temporários,
    # independentemente de onde salvamos os arquivos finais.
    system_downloads = os.path.expanduser("~/Downloads")
    os.makedirs(system_downloads, exist_ok=True)
    print(f"🔧 Pasta de Sistema Criada: {system_downloads}")
    # ---------------------------------------------
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ],
            downloads_path=download_path  # Força o uso da pasta criada
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.2 Mobile/15E148 Safari/604.1"
            ),
            accept_downloads=True
        )
        page = context.new_page()
        
        # Economia de dados (bloqueio de imagens)
        def handle_route(route: Route):
            url = route.request.url
            if route.request.resource_type == "image" and any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                route.abort()
            else:
                route.continue_()
        
        page.route("**/*", handle_route)
        print("   ✅ Economia de dados ativada")
        
        try:
            print("📡 Carregando página...")
            page.goto(VOOS_URL, wait_until="domcontentloaded", timeout=60_000)
            print("✅ Página carregada")
            
            page.wait_for_timeout(3000)
            
            # REQUISITO 4: Loop de cliques no botão "Carregar mais"
            print(f"\n🔄 Procurando botão 'Carregar mais'...")
            clicks_performed = 0
            
            for attempt in range(max_load_more_clicks):
                load_more_selectors = [
                    "button:has-text('Carregar mais')",
                    "button:has-text('carregar mais')",
                    "a:has-text('Carregar mais')",
                    "[class*='load-more']",
                    "[class*='carregar']",
                ]
                
                button_found = False
                for selector in load_more_selectors:
                    try:
                        button = page.query_selector(selector)
                        if button and button.is_visible():
                            print(f"   [{attempt + 1}/{max_load_more_clicks}] Clicando no botão 'Carregar mais'...")
                            button.click()
                            button_found = True
                            clicks_performed += 1
                            page.wait_for_timeout(wait_between_clicks_ms)
                            break
                    except Exception:
                        continue
                
                if not button_found:
                    if attempt == 0:
                        try:
                            page.mouse.wheel(0, 2000)
                            page.wait_for_timeout(1000)
                            continue
                        except Exception:
                            pass
                    break
            
            print(f"\n✅ Carregamento concluído ({clicks_performed} clique(s))")
            page.wait_for_timeout(2000)
            
            # Extrai voos
            print(f"\n📊 Extraindo voos...")
            flights = extract_flights_from_page(page)
            print(f"   ✅ {len(flights)} voo(s) extraído(s)")
            
        except Exception as e:
            print(f"❌ Erro durante scraping: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if not headless:
                print("\n⏸️  Navegador aberto para validação. Pressione Enter para fechar...")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    pass
            context.close()
            browser.close()
    
    return flights


def merge_flights_to_csv(scraped_flights: List[Dict[str, str]], csv_path: str) -> int:
    """
    Faz merge completo: dados históricos + dados novos.
    
    Lógica:
    1. Carrega TODOS os dados históricos (CSV antigo + CSVs anteriores)
    2. Adiciona novos voos da busca atual (com databusca = timestamp atual)
    3. Filtra destinos incorretos (companhias aéreas)
    4. Remove duplicados (mesmo Voo + Data), mantendo o mais recente
    5. Salva tudo no novo CSV com timestamp
    
    Returns:
        Número de novos voos adicionados
    """
    agora = datetime.now()
    data_captura = agora.strftime("%Y-%m-%d")
    databusca_timestamp = agora.strftime("%Y-%m-%d %H:%M:%S")  # Timestamp completo para databusca
    
    # Filtra apenas voos problemáticos
    problematic_flights = [
        f for f in scraped_flights 
        if f.get('Status', '').lower() in ['atrasado', 'atraso', 'cancelado', 'cancel']
    ]
    
    print(f"\n💾 MERGE COMPLETO: Processando dados históricos + novos voos...")
    
    # 1. Carrega TODOS os dados históricos (CSV antigo + CSVs anteriores)
    print(f"   📂 Carregando dados históricos...")
    all_historical = load_all_historical_data()
    print(f"   📊 Dados históricos carregados: {len(all_historical)} voo(s)")
    
    # 2. Prepara novos voos da busca atual
    new_flights_to_add = []
    
    if problematic_flights:
        print(f"   📋 Processando {len(problematic_flights)} voo(s) problemático(s) da busca atual...")
        
        for flight in problematic_flights:
            voo = flight.get('Voo', '')
            horario_previsto = flight.get('Horario_Previsto', '')
            
            if voo == "N/A" or horario_previsto == "N/A":
                continue
            
            # Calcula alertas
            alerta_1h, alerta_2h, atraso_minutos = calculate_delay_alerts(
                horario_previsto, 
                flight.get('Horario_Estimado', 'N/A')
            )
            
            # Filtra destino incorreto (companhias aéreas)
            destino = flight.get('Destino', 'N/A')
            if destino in COMPANHIAS_CONHECIDAS:
                destino = "N/A"
            
            # Prepara dados do voo
            flight_data = {
                "databusca": databusca_timestamp,  # Timestamp da captura atual
                "Data": data_captura,
                "Horario_Previsto": horario_previsto,
                "Horario_Estimado": flight.get('Horario_Estimado', 'N/A'),
                "Voo": voo,
                "Companhia": flight.get('Companhia', 'N/A'),
                "Destino": destino,
                "Status": flight.get('Status', 'N/A'),
                "Alerta_1H": alerta_1h,
                "Alerta_2H": alerta_2h,
                "Status_Monitoramento": "Ativo",
            }
            
            new_flights_to_add.append(flight_data)
    
    # 3. Combina dados históricos + novos voos
    all_flights = all_historical + new_flights_to_add
    print(f"   📊 Total antes de remover duplicados: {len(all_flights)} voo(s)")
    
    # 4. Remove duplicados (mesmo Voo + Data), mantendo o mais recente
    print(f"   🔍 Removendo duplicados (mesmo Voo + Data)...")
    unique_flights = remove_duplicates(all_flights)
    duplicates_removed = len(all_flights) - len(unique_flights)
    
    if duplicates_removed > 0:
        print(f"   ✅ {duplicates_removed} duplicata(s) removida(s) (mantido o mais recente)")
    
    # 5. Salva tudo no novo CSV com timestamp
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(unique_flights)
            f.flush()
            os.fsync(f.fileno())  # Força escrita no disco
        
        new_flights_count = len(new_flights_to_add)
        print(f"\n   ✅ {new_flights_count} novo(s) voo(s) adicionado(s) nesta execução")
        print(f"   📊 Total no CSV: {len(unique_flights)} voo(s) (históricos + novos, sem duplicados)")
        
        for flight_data in new_flights_to_add:
            voo = flight_data['Voo']
            companhia = flight_data['Companhia']
            destino = flight_data['Destino']
            print(f"      ✅ ADICIONADO: Voo {voo} da {companhia} → {destino}")
        
    except Exception as e:
        print(f"   ❌ ERRO CRÍTICO ao fazer merge: {e}")
        print(f"   Caminho: {os.path.abspath(csv_path)}")
        import traceback
        traceback.print_exc()
        return 0
    
    return new_flights_count


def mark_missing_flights_as_finished(found_flight_keys: Set[str], csv_path: str) -> int:
    """
    REQUISITO 3: Para arquivos com timestamp, esta função não é necessária.
    Cada execução cria um novo arquivo, então não há voos que "sumiram" entre execuções.
    """
    # Como cada execução cria um novo arquivo, não precisamos marcar voos como "sumiram"
    # Esta função é mantida apenas para compatibilidade, mas não faz nada
    return 0


def save_with_historical_persistence(scraped_flights: List[Dict[str, str]]) -> int:
    """
    Nova lógica de salvamento com histórico persistente usando pandas.
    
    Lógica:
    1. Verifica se voos_atrasados_gru.csv existe na raiz
    2. Se existir, carrega em DataFrame pandas
    3. Converte novos dados coletados para o formato do CSV (Data_Captura, Horario, Companhia, Numero_Voo, Destino_Origem, Status)
    4. Concatena novos dados com antigos
    5. Deduplicação: Remove duplicatas mantendo a versão mais recente
       - Critério de duplicidade: Numero_Voo + Data_Captura
    6. Salva o arquivo final acumulado no mesmo local
    
    Args:
        scraped_flights: Lista de voos coletados no scraping
        
    Returns:
        Número de novos voos adicionados
    """
    agora = datetime.now()
    data_captura = agora.strftime("%Y-%m-%d")
    
    print(f"\n💾 SALVAMENTO COM HISTÓRICO PERSISTENTE")
    print(f"   📂 Arquivo: {os.path.abspath(PERSISTENT_CSV_PATH)}")
    
    # 1. Verifica se o arquivo existe e carrega dados históricos
    df_historical = pd.DataFrame()
    if os.path.exists(PERSISTENT_CSV_PATH):
        try:
            print(f"   📖 Carregando dados históricos existentes...")
            df_historical = pd.read_csv(PERSISTENT_CSV_PATH, encoding='utf-8')
            
            # Migração: se existir coluna Destino_Origem, renomeia para Operado_Por
            if 'Destino_Origem' in df_historical.columns and 'Operado_Por' not in df_historical.columns:
                print(f"   🔄 Migrando coluna Destino_Origem → Operado_Por...")
                df_historical = df_historical.rename(columns={'Destino_Origem': 'Operado_Por'})
            
            # Adiciona colunas Data_Partida e Hora_Partida se não existirem
            if 'Data_Partida' not in df_historical.columns:
                df_historical['Data_Partida'] = ''
            if 'Hora_Partida' not in df_historical.columns:
                df_historical['Hora_Partida'] = ''
            
            # Preenche Data_Partida e Hora_Partida para registros antigos que não têm
            for idx, row in df_historical.iterrows():
                if pd.isna(row.get('Data_Partida')) or str(row.get('Data_Partida', '')).strip() == '':
                    try:
                        if pd.notna(row.get('Data_Captura')):
                            data_obj = datetime.strptime(str(row['Data_Captura']), "%Y-%m-%d")
                            df_historical.at[idx, 'Data_Partida'] = data_obj.strftime("%d/%m")
                    except:
                        pass
                
                if pd.isna(row.get('Hora_Partida')) or str(row.get('Hora_Partida', '')).strip() == '':
                    try:
                        if pd.notna(row.get('Horario')):
                            horario = str(row['Horario'])
                            if ":" in horario:
                                parts = horario.split(":")
                                if len(parts) >= 2:
                                    df_historical.at[idx, 'Hora_Partida'] = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
                    except:
                        pass
            
            print(f"   ✅ {len(df_historical)} registro(s) histórico(s) carregado(s)")
        except Exception as e:
            print(f"   ⚠️  Erro ao carregar CSV histórico: {e}")
            print(f"   📝 Criando novo arquivo...")
            df_historical = pd.DataFrame()
    else:
        print(f"   📝 Arquivo não existe. Será criado novo arquivo.")
    
    # 2. Filtra apenas voos problemáticos (atrasados/cancelados)
    problematic_flights = [
        f for f in scraped_flights 
        if f.get('Status', '').lower() in ['atrasado', 'atraso', 'cancelado', 'cancel']
    ]
    
    if not problematic_flights:
        print(f"   ℹ️  Nenhum voo problemático encontrado nesta execução.")
        if len(df_historical) > 0:
            # Salva o histórico mesmo sem novos dados (preserva histórico)
            df_historical.to_csv(PERSISTENT_CSV_PATH, index=False, encoding='utf-8')
            print(f"   ✅ Histórico preservado: {len(df_historical)} registro(s)")
        return 0
    
    print(f"   📋 Processando {len(problematic_flights)} voo(s) problemático(s)...")
    
    # 3. Converte novos dados para o formato do CSV persistente
    # Formato: Data_Captura, Horario, Companhia, Numero_Voo, Operado_Por, Status, Data_Partida, Hora_Partida
    new_flights_data = []
    
    for flight in problematic_flights:
        voo = str(flight.get('Voo', '')).strip()
        horario_previsto = str(flight.get('Horario_Previsto', '')).strip()
        
        if voo == "N/A" or horario_previsto == "N/A" or not voo or not horario_previsto:
            continue
        
        companhia = str(flight.get('Companhia', 'N/A')).strip()
        
        # Extrai Operado_Por (anteriormente Destino_Origem - na verdade é codeshare)
        # Se o destino for uma companhia conhecida, é codeshare
        destino = str(flight.get('Destino', 'N/A')).strip()
        operado_por = ""
        
        if destino in COMPANHIAS_CONHECIDAS:
            # É codeshare - usa como Operado_Por
            operado_por = destino
        else:
            # Não é codeshare, deixa vazio
            operado_por = ""
        
        # Se Operado_Por for vazio ou igual à companhia principal, define como "Própria Cia" ou vazio
        if not operado_por or operado_por == companhia or operado_por == "N/A":
            operado_por = ""  # Deixa em branco quando é própria companhia
        
        # Extrai Data_Partida (DD/MM) e Hora_Partida (HH:MM)
        data_partida = ""
        hora_partida = ""
        
        try:
            # Data_Partida: converte Data_Captura (YYYY-MM-DD) para DD/MM
            if data_captura:
                data_obj = datetime.strptime(data_captura, "%Y-%m-%d")
                data_partida = data_obj.strftime("%d/%m")
            
            # Hora_Partida: extrai HH:MM do Horario_Previsto
            if horario_previsto and ":" in horario_previsto:
                # Garante formato HH:MM
                parts = horario_previsto.split(":")
                if len(parts) >= 2:
                    hora_partida = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
        except Exception as e:
            print(f"   ⚠️  Erro ao processar data/hora para voo {voo}: {e}")
        
        # Prepara dados no formato do CSV persistente
        flight_row = {
            "Data_Captura": data_captura,
            "Horario": horario_previsto,
            "Companhia": companhia,
            "Numero_Voo": voo,
            "Operado_Por": operado_por,
            "Status": str(flight.get('Status', 'N/A')).strip(),
            "Data_Partida": data_partida,
            "Hora_Partida": hora_partida,
        }
        
        new_flights_data.append(flight_row)
    
    if not new_flights_data:
        print(f"   ℹ️  Nenhum voo válido para adicionar.")
        if len(df_historical) > 0:
            df_historical.to_csv(PERSISTENT_CSV_PATH, index=False, encoding='utf-8')
        return 0
    
    # 4. Cria DataFrame com novos dados
    df_new = pd.DataFrame(new_flights_data)
    print(f"   ✅ {len(df_new)} novo(s) voo(s) preparado(s) para adição")
    
    # 5. Concatena dados históricos com novos
    # IMPORTANTE: Novos dados vêm primeiro para que sejam mantidos em caso de duplicata
    if len(df_historical) > 0:
        # Garante que as colunas estão na mesma ordem
        if set(df_historical.columns) != set(df_new.columns):
            print(f"   ⚠️  Aviso: Colunas diferentes detectadas.")
            print(f"      Histórico: {list(df_historical.columns)}")
            print(f"      Novos: {list(df_new.columns)}")
            # Alinha colunas
            common_cols = list(set(df_historical.columns) & set(df_new.columns))
            df_historical = df_historical[common_cols]
            df_new = df_new[common_cols]
        
        # Concatena: novos dados primeiro (para manter versão mais recente em duplicatas)
        df_combined = pd.concat([df_new, df_historical], ignore_index=True)
        print(f"   📊 Total após concatenação: {len(df_combined)} registro(s)")
    else:
        df_combined = df_new
        print(f"   📊 Total (primeira execução): {len(df_combined)} registro(s)")
    
    # 6. Deduplicação inteligente: Remove duplicatas mantendo a versão mais recente
    # Critério: Numero_Voo + Data_Captura
    print(f"   🔍 Aplicando deduplicação (Numero_Voo + Data_Captura)...")
    
    # Adiciona índice original para preservar ordem (novos dados têm índices menores)
    df_combined['_original_index'] = df_combined.index
    
    # Converte Data_Captura para datetime para comparação e ordenação
    df_combined['Data_Captura_Parsed'] = pd.to_datetime(df_combined['Data_Captura'], errors='coerce')
    
    # Ordena por Data_Captura (mais recente primeiro) e depois por índice original (menor = mais recente)
    # Isso garante que se houver duplicatas na mesma data, mantemos os novos dados (índices menores)
    df_combined = df_combined.sort_values(
        by=['Data_Captura_Parsed', '_original_index', 'Numero_Voo'],
        ascending=[False, True, True],
        na_position='last'
    )
    
    # Remove duplicatas mantendo a primeira ocorrência (que é a mais recente após ordenação)
    # Como novos dados têm índices menores e vêm primeiro após ordenação,
    # keep='first' mantém a versão mais recente
    df_deduplicated = df_combined.drop_duplicates(
        subset=['Numero_Voo', 'Data_Captura'],
        keep='first'
    )
    
    # Remove colunas auxiliares
    df_deduplicated = df_deduplicated.drop(columns=['Data_Captura_Parsed', '_original_index'], errors='ignore')
    
    duplicates_removed = len(df_combined) - len(df_deduplicated)
    if duplicates_removed > 0:
        print(f"   ✅ {duplicates_removed} duplicata(s) removida(s) (mantida versão mais recente)")
    
    # 7. Salva o arquivo final acumulado
    try:
        # Ordena por Data_Captura (mais recente primeiro) e Numero_Voo para melhor visualização
        df_deduplicated = df_deduplicated.sort_values(
            by=['Data_Captura', 'Numero_Voo'],
            ascending=[False, True],
            na_position='last'
        )
        
        df_deduplicated.to_csv(PERSISTENT_CSV_PATH, index=False, encoding='utf-8')
        
        new_count = len(new_flights_data)
        total_count = len(df_deduplicated)
        
        print(f"\n   ✅ Salvamento concluído!")
        print(f"   📊 Novos voos adicionados: {new_count}")
        print(f"   📊 Total no arquivo: {total_count} registro(s)")
        
        # Lista novos voos adicionados
        for flight_row in new_flights_data:
            voo = flight_row['Numero_Voo']
            companhia = flight_row['Companhia']
            operado_por = flight_row.get('Operado_Por', '')
            if operado_por:
                print(f"      ✅ ADICIONADO: Voo {voo} da {companhia} (Operado por: {operado_por})")
            else:
                print(f"      ✅ ADICIONADO: Voo {voo} da {companhia}")
        
        return new_count
        
    except Exception as e:
        print(f"   ❌ ERRO CRÍTICO ao salvar CSV: {e}")
        print(f"   Caminho: {os.path.abspath(PERSISTENT_CSV_PATH)}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """
    Função principal com salvamento de histórico persistente.
    Usa voos_atrasados_gru.csv na raiz como arquivo persistente.
    """
    print("=" * 70)
    print("🚀 SCRAPER GRU - VERSÃO INTELIGENTE pSEO")
    print("=" * 70)
    print()
    print(f"   Diretório de trabalho atual: {os.getcwd()}")
    print()
    
    # Executa scraping
    scraped_flights = scrape_gru_flights_html(
        max_load_more_clicks=10,
        wait_between_clicks_ms=2000,
        headless=True
    )
    
    if not scraped_flights:
        print("\n⚠️  Nenhum voo encontrado no scraping")
        print(f"📄 Arquivo CSV: {os.path.abspath(PERSISTENT_CSV_PATH)}")
        return
    
    print(f"\n" + "=" * 70)
    print("💾 SALVAMENTO COM HISTÓRICO PERSISTENTE")
    print("=" * 70)
    
    # Salva com histórico persistente (carrega CSV existente, concatena, deduplica e salva)
    new_flights_count = save_with_historical_persistence(scraped_flights)
    
    print(f"\n" + "=" * 70)
    print("📊 RESUMO FINAL")
    print("=" * 70)
    print(f"   • Total de voos vistos no site: {len(scraped_flights)}")
    problematic = [f for f in scraped_flights if f.get('Status', '').lower() in ['atrasado', 'atraso', 'cancelado', 'cancel']]
    print(f"   • Voos problemáticos encontrados: {len(problematic)}")
    print(f"   • Novos voos adicionados ao histórico: {new_flights_count}")
    print(f"📄 Arquivo CSV persistente: {os.path.abspath(PERSISTENT_CSV_PATH)}")
    print("=" * 70)
    print("✅ Scraping concluído com histórico persistente!")
    print("=" * 70)
    
    # Automação: Gera o site automaticamente após o scraping
    print(f"\n" + "=" * 70)
    print("🌐 GERANDO SITE AUTOMATICAMENTE")
    print("=" * 70)
    try:
        import subprocess
        gerar_site_path = os.path.join(os.path.dirname(__file__), "gerar_site.py")
        if os.path.exists(gerar_site_path):
            print(f"   📄 Executando: {gerar_site_path}")
            result = subprocess.run(
                [sys.executable, gerar_site_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__)
            )
            if result.returncode == 0:
                print(f"   ✅ Site gerado com sucesso!")
                if result.stdout:
                    print(f"   📋 Saída: {result.stdout[:200]}...")
            else:
                print(f"   ⚠️  Aviso: Geração do site retornou código {result.returncode}")
                if result.stderr:
                    print(f"   📋 Erro: {result.stderr[:200]}...")
        else:
            print(f"   ⚠️  Arquivo gerar_site.py não encontrado em: {gerar_site_path}")
    except Exception as e:
        print(f"   ⚠️  Erro ao gerar site automaticamente: {e}")
        print(f"   💡 Execute manualmente: python gerar_site.py")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
