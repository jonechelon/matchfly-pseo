#!/usr/bin/env python3
"""
MatchFly - Gerador de Site Estático
====================================
Script para gerar páginas HTML estáticas usando templates separados:
- TEMPLATE_HOME: home_template.html (para public/index.html)
- TEMPLATE_VOO: public/voo/voo-klm-0792-gru-atrasado.html (para páginas de voos)

Autor: MatchFly Team
Data: 2026-01-12
"""

import csv
import json
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Carregar variáveis de ambiente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv é opcional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gerar_site.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Templates
TEMPLATE_HOME = Path("home_template.html")
TEMPLATE_VOO = Path("public/voo/voo-klm-0792-gru-atrasado.html")

# Link de afiliado (lido de variável de ambiente)
AFFILIATE_LINK = os.getenv("AFFILIATE_LINK", "").strip()


def validate_json_integrity(json_file: Path) -> Tuple[bool, str, Optional[Dict]]:
    """
    Valida a integridade do arquivo JSON antes de carregar.
    
    Args:
        json_file: Caminho para o arquivo JSON
        
    Returns:
        Tuple (is_valid, message, data):
        - is_valid: True se JSON está válido
        - message: Mensagem descritiva
        - data: Dados carregados ou None se inválido
    """
    if not json_file.exists():
        return False, "Arquivo não existe", None
    
    if json_file.stat().st_size == 0:
        return False, "Arquivo está vazio (0 bytes)", None
    
    try:
        # Tenta carregar o JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Verifica se termina corretamente
        if not content.endswith('}'):
            return False, "JSON não termina com '}' - arquivo pode estar truncado", None
        
        # Tenta parsear
        data = json.loads(content)
        
        # Valida estrutura básica
        if not isinstance(data, dict):
            return False, "JSON raiz não é um objeto (dict)", None
        
        if 'flights' not in data:
            return False, "Campo 'flights' ausente no JSON", None
        
        if not isinstance(data.get('flights'), list):
            return False, "Campo 'flights' não é uma lista", None
        
        # Valida que cada voo tem campos obrigatórios
        flights = data.get('flights', [])
        for i, flight in enumerate(flights):
            if not isinstance(flight, dict):
                return False, f"Voo {i} não é um objeto válido", None
            if 'flight_number' not in flight:
                return False, f"Voo {i} sem campo 'flight_number'", None
        
        return True, f"JSON válido com {len(flights)} voos", data
        
    except json.JSONDecodeError as e:
        return False, f"Erro de sintaxe JSON: {e.msg} (linha {e.lineno}, coluna {e.colno})", None
    except Exception as e:
        return False, f"Erro ao validar JSON: {str(e)}", None


def fix_json_file(json_file: Path) -> Tuple[bool, str, Optional[Dict]]:
    """
    Tenta corrigir um arquivo JSON corrompido.
    
    Estratégias de correção:
    1. Adiciona fechamentos faltantes (], })
    2. Remove conflitos do Git
    3. Tenta recuperar dados válidos
    
    Args:
        json_file: Caminho para o arquivo JSON
        
    Returns:
        Tuple (success, message, data):
        - success: True se conseguiu corrigir
        - message: Mensagem descritiva
        - data: Dados recuperados ou None
    """
    if not json_file.exists():
        return False, "Arquivo não existe", None
    
    try:
        # Lê conteúdo bruto
        with open(json_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove conflitos do Git
        content = re.sub(r'<<<<<<<.*?======.*?>>>>>>>', '', content, flags=re.DOTALL)
        content = re.sub(r'<<<<<<<.*?', '', content, flags=re.DOTALL)
        content = re.sub(r'======.*?', '', content, flags=re.DOTALL)
        content = re.sub(r'>>>>>>>.*?', '', content, flags=re.DOTALL)
        
        # Remove linhas vazias extras
        lines = [line for line in content.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
        # Tenta encontrar onde o JSON foi truncado
        # Conta chaves e colchetes abertos vs fechados
        open_braces = content.count('{')
        close_braces = content.count('}')
        open_brackets = content.count('[')
        close_brackets = content.count(']')
        
        # Adiciona fechamentos faltantes
        if not content.rstrip().endswith('}'):
            # Adiciona fechamentos necessários
            missing_brackets = open_brackets - close_brackets
            missing_braces = open_braces - close_braces
            
            # Se está dentro de uma lista, fecha a lista primeiro
            if missing_brackets > 0:
                content = content.rstrip() + '\n' + '  ]' * missing_brackets
            
            # Depois fecha o objeto principal
            if missing_braces > 0:
                content = content.rstrip() + '\n' + '}' * missing_braces
        
        # Tenta parsear novamente
        try:
            data = json.loads(content)
            
            # Valida estrutura
            if isinstance(data, dict) and 'flights' in data:
                return True, f"JSON corrigido com sucesso. {len(data.get('flights', []))} voos recuperados.", data
            else:
                return False, "JSON corrigido mas estrutura inválida", None
                
        except json.JSONDecodeError:
            # Se ainda não funcionou, tenta extrair apenas os voos válidos
            return extract_valid_flights(content)
            
    except Exception as e:
        return False, f"Erro ao tentar corrigir JSON: {str(e)}", None


def extract_valid_flights(content: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Tenta extrair voos válidos de um JSON parcialmente corrompido.
    
    Args:
        content: Conteúdo do arquivo JSON
        
    Returns:
        Tuple (success, message, data)
    """
    try:
        # Tenta encontrar todos os objetos de voo válidos
        flights = []
        
        # Procura por padrões de objetos de voo
        flight_pattern = r'\{[^{}]*"flight_number"[^{}]*\}'
        matches = re.finditer(flight_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                flight_obj = json.loads(match.group(0))
                if 'flight_number' in flight_obj:
                    flights.append(flight_obj)
            except:
                continue
        
        if flights:
            data = {
                "flights": flights,
                "metadata": {
                    "scraped_at": datetime.now().isoformat() + "+00:00",
                    "source": "playwright_intercept:GetVoos",
                    "total_flights": len(flights),
                    "recovered": True,
                    "recovery_note": "Voos recuperados de JSON corrompido"
                }
            }
            return True, f"Recuperados {len(flights)} voos do JSON corrompido", data
        else:
            return False, "Não foi possível extrair voos válidos", None
            
    except Exception as e:
        return False, f"Erro ao extrair voos: {str(e)}", None


def convert_csv_to_json_flights(csv_path: Path) -> List[Dict]:
    """
    Converte dados do CSV (voos_atrasados_gru.csv) para o formato JSON esperado.
    
    Mapeia campos do CSV para o formato do JSON:
    - Data_Captura -> capture_date
    - Horario -> scheduled_time
    - Companhia -> airline
    - Numero_Voo -> flight_number
    - Operado_Por (ou Destino_Origem) -> Operado_Por
    - Status -> status
    - Data_Partida -> Data_Partida
    - Hora_Partida -> Hora_Partida
    
    Args:
        csv_path: Caminho para o arquivo CSV
        
    Returns:
        Lista de voos no formato JSON
    """
    flights = []
    
    if not csv_path.exists():
        return flights
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Extrai campos do CSV
                data_captura = str(row.get('Data_Captura', '')).strip()
                horario = str(row.get('Horario', '')).strip()
                companhia = str(row.get('Companhia', 'N/A')).strip()
                numero_voo = str(row.get('Numero_Voo', '')).strip()
                status = str(row.get('Status', 'N/A')).strip()
                data_partida = str(row.get('Data_Partida', '')).strip()
                hora_partida = str(row.get('Hora_Partida', '')).strip()
                
                # FILTRO ANTI-N/A: Remove linhas sem companhia válida
                # Se companhia estiver vazia, nula ou "N/A", pula esta linha
                if not companhia or companhia.upper() == 'N/A' or companhia == '':
                    continue
                
                # Suporta tanto Operado_Por (novo) quanto Destino_Origem (antigo)
                # Se Destino_Origem for uma companhia conhecida, é codeshare (Operado_Por)
                destino_origem = str(row.get('Destino_Origem', '')).strip()
                operado_por_raw = str(row.get('Operado_Por', '')).strip()
                
                # Lista de companhias conhecidas (para identificar codeshare)
                companhias_conhecidas = {
                    "LATAM", "TAM", "GOL", "AZUL", "EMIRATES", "TURKISH", "TURKISH AIRLINES",
                    "BRITISH", "BRITISH AIRWAYS", "AIR FRANCE", "AIRFRANCE", "KLM", "LUFTHANSA",
                    "AMERICAN", "AMERICAN AIRLINES", "DELTA", "UNITED"
                }
                
                # Determina Operado_Por
                operado_por = ""
                if operado_por_raw and operado_por_raw != 'N/A':
                    operado_por = operado_por_raw
                elif destino_origem in companhias_conhecidas:
                    # É codeshare - usa como Operado_Por
                    operado_por = destino_origem
                
                # Se Operado_Por for igual à companhia principal ou vazio, deixa em branco
                if not operado_por or operado_por == companhia or operado_por == "N/A":
                    operado_por = ""
                
                # Se não tiver Data_Partida, tenta extrair de Data_Captura
                if not data_partida and data_captura:
                    try:
                        data_obj = datetime.strptime(data_captura, "%Y-%m-%d")
                        data_partida = data_obj.strftime("%d/%m")
                    except:
                        pass
                
                # Se não tiver Hora_Partida, usa Horario
                if not hora_partida and horario:
                    hora_partida = horario
                
                # Calcula delay_hours (aproximado, baseado no status)
                delay_hours = 0.0
                if 'atrasado' in status.lower():
                    # Aproximação: assume 1 hora de atraso se não tiver informação
                    delay_hours = 1.0
                
                # Cria objeto de voo no formato JSON
                flight = {
                    'flight_number': numero_voo,
                    'airline': companhia if companhia != 'N/A' else 'N/A',
                    'status': status,
                    'scheduled_time': hora_partida if hora_partida else horario,
                    'delay_hours': delay_hours,
                    'origin': 'GRU',
                    'capture_date': data_captura,
                    # Novos campos
                    'Operado_Por': operado_por if operado_por and operado_por != 'N/A' else '',
                    'Data_Partida': data_partida,
                    'Hora_Partida': hora_partida if hora_partida else horario,
                }
                
                flights.append(flight)
        
        logger.info(f"✅ {len(flights)} voo(s) convertido(s) do CSV")
        
    except Exception as e:
        logger.error(f"❌ Erro ao converter CSV para JSON: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return flights


def load_flights_safely(json_file: Path) -> Tuple[bool, str, List[Dict]]:
    """
    Carrega voos do arquivo JSON com validação e correção automática.
    
    Esta função:
    1. Valida integridade do JSON
    2. Tenta corrigir se estiver corrompido
    3. Cria backup antes de qualquer modificação
    4. Retorna lista de voos ou lista vazia se falhar
    
    Args:
        json_file: Caminho para o arquivo JSON
        
    Returns:
        Tuple (success, message, flights):
        - success: True se conseguiu carregar
        - message: Mensagem descritiva
        - flights: Lista de voos (pode estar vazia)
    """
    # Valida integridade primeiro
    is_valid, message, data = validate_json_integrity(json_file)
    
    if is_valid and data:
        flights = data.get('flights', [])
        return True, message, flights
    
    # Se inválido, tenta corrigir
    logger.warning(f"⚠️  JSON inválido detectado: {message}")
    logger.info("🔄 Tentando corrigir arquivo JSON...")
    
    # Cria backup antes de tentar corrigir
    backup_file = json_file.with_suffix('.json.backup')
    try:
        if json_file.exists():
            shutil.copy2(json_file, backup_file)
            logger.info(f"💾 Backup criado: {backup_file.name}")
    except Exception as e:
        logger.warning(f"⚠️  Não foi possível criar backup: {e}")
    
    # Tenta corrigir
    success, fix_message, fixed_data = fix_json_file(json_file)
    
    if success and fixed_data:
        # Salva versão corrigida
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(fixed_data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ {fix_message}")
            flights = fixed_data.get('flights', [])
            return True, f"JSON corrigido: {fix_message}", flights
        except Exception as e:
            logger.error(f"❌ Erro ao salvar JSON corrigido: {e}")
            # Tenta restaurar backup
            if backup_file.exists():
                try:
                    shutil.copy2(backup_file, json_file)
                    logger.info("💾 Backup restaurado")
                except:
                    pass
            return False, f"Erro ao salvar correção: {e}", []
    else:
        logger.error(f"❌ Não foi possível corrigir JSON: {fix_message}")
        # Tenta restaurar backup
        if backup_file.exists():
            try:
                shutil.copy2(backup_file, json_file)
                logger.info("💾 Backup restaurado")
            except:
                pass
        return False, fix_message, []


def slugify(text: str) -> str:
    """Converte texto para slug (simples, sem dependências externas)."""
    if not text:
        return ""
    # Converter para minúsculas e substituir espaços por hífens
    text = text.lower().strip()
    # Remover caracteres especiais, manter apenas letras, números e hífens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def format_delay_hours(delay_hours: float) -> str:
    """
    Formata delay_hours no formato usado no template (ex: "0.42 horas", "2.0 horas").
    """
    if delay_hours == int(delay_hours):
        return f"{int(delay_hours)}.0 horas"
    else:
        return f"{delay_hours:.2f} horas"


def get_destination_from_flight(flight: Dict) -> str:
    """
    Obtém o destino do voo. Prioriza OrigemDestino, senão usa fallback.
    """
    # Tentar campo OrigemDestino primeiro
    origem_destino = flight.get('OrigemDestino', '').strip()
    if origem_destino:
        return origem_destino
    
    # Fallback: usar função existente baseada na companhia
    airline = flight.get('airline', '').strip()
    if not airline:
        return 'Destino não informado'
    
    airline_lower = airline.lower()
    if 'klm' in airline_lower:
        return 'Amsterdã'
    elif 'air france' in airline_lower or 'france' in airline_lower:
        return 'Paris'
    elif 'lufthansa' in airline_lower:
        return 'Frankfurt'
    elif 'british' in airline_lower or 'british airways' in airline_lower:
        return 'Londres'
    elif 'latam' in airline_lower:
        return 'Santiago'
    elif 'gol' in airline_lower:
        return 'Rio de Janeiro'
    elif 'azul' in airline_lower:
        return 'Campinas'
    else:
        return 'Destino não informado'


def generate_flight_card_html(flight: Dict, filename: str) -> str:
    """
    Gera o HTML de um card de voo seguindo o design exato do template.
    """
    flight_number = flight.get('flight_number', '').strip()
    airline = flight.get('airline', '').strip()
    status = flight.get('status', '').strip()
    delay_hours = flight.get('delay_hours', 0)
    scheduled_time = flight.get('scheduled_time', '').strip() or 'N/A'
    
    # Novos campos: Operado_Por, Data_Partida, Hora_Partida
    operado_por = flight.get('Operado_Por', flight.get('operado_por', '')).strip()
    data_partida = flight.get('Data_Partida', flight.get('data_partida', '')).strip()
    hora_partida = flight.get('Hora_Partida', flight.get('hora_partida', '')).strip()
    
    # Se não tiver Data_Partida/Hora_Partida, tenta extrair de scheduled_time
    if not data_partida or not hora_partida:
        # Tenta extrair de scheduled_time se disponível
        if scheduled_time and scheduled_time != 'N/A':
            hora_partida = scheduled_time
    
    # Status em português
    status_lower = status.lower()
    if 'cancelado' in status_lower:
        status_badge = 'Cancelado'
        status_bg = 'bg-red-100 text-red-800'
    elif 'atrasado' in status_lower:
        status_badge = 'Atrasado'
        status_bg = 'bg-orange-500 text-white'
    else:
        status_badge = status
        status_bg = 'bg-orange-500 text-white'
    
    delay_formatted = format_delay_hours(delay_hours)
    
    # URL do voo
    voo_url = f"/voo/{filename}"
    
    # Sub-header "Operado por" (apenas se tiver valor)
    operado_por_html = ""
    if operado_por and operado_por != "N/A" and operado_por != "":
        operado_por_html = f'<p class="text-xs text-gray-500 mt-1">Operado por: {operado_por}</p>'
    
    # HTML do card (cópia exata do template com melhorias)
    card_html = f'''            <a class='block bg-white rounded-3xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden border border-gray-100 group hover:-translate-y-2' href='{voo_url}'>
                
                <!-- Header Card -->
                <div class="bg-gradient-to-br from-orange-50 to-orange-100 border-b-2 border-orange-200 p-5">
                    <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center space-x-2">
                            <div class="w-8 h-8 rounded-lg bg-white shadow-sm flex items-center justify-center">
                                <svg class="w-5 h-5 text-blue-900" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"/>
                                </svg>
                            </div>
                            <div>
                                <span class="text-xs font-bold text-gray-500 uppercase tracking-wider">{airline}</span>
                                {operado_por_html}
                            </div>
                        </div>
                        <span class="px-3 py-1 {status_bg} text-[10px] font-black rounded-full uppercase tracking-wider shadow-md">
                            {status_badge}
                        </span>
                    </div>
                    
                    <h4 class="text-3xl font-black text-orange-900 tracking-tight">
                        {flight_number}
                    </h4>
                </div>

                <!-- Body Card -->
                <div class="p-5 bg-white">
                    <div class="space-y-3 mb-4">
                        <div class="flex items-center space-x-3 text-sm">
                            <div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                                <svg class="w-5 h-5 text-blue-900" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
                                </svg>
                            </div>
                            <div>
                                <p class="text-xs text-gray-500 font-medium">Atraso</p>
                                <p class="text-base font-bold text-gray-900">{delay_formatted}</p>
                            </div>
                        </div>
                        
                        <!-- Layout de duas colunas para Data e Hora -->
                        <div class="grid grid-cols-2 gap-3">
                            <!-- Data Partida -->
                            <div class="flex items-center space-x-2 text-sm">
                                <div class="w-6 h-6 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                                    <svg class="w-4 h-4 text-blue-900" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd"/>
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-[10px] text-gray-500 font-medium">Data</p>
                                    <p class="text-xs font-semibold text-gray-700">{data_partida if data_partida else 'N/A'}</p>
                                </div>
                            </div>
                            
                            <!-- Hora Partida -->
                            <div class="flex items-center space-x-2 text-sm">
                                <div class="w-6 h-6 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                                    <svg class="w-4 h-4 text-blue-900" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-[10px] text-gray-500 font-medium">Hora</p>
                                    <p class="text-xs font-semibold text-gray-700">{hora_partida if hora_partida else scheduled_time}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- CTA -->
                    <div class="pt-4 border-t border-gray-100">
                        <div class="flex items-center justify-between text-blue-900 font-bold text-sm group-hover:text-blue-700 transition-colors">
                            <span>Ver detalhes</span>
                            <svg class="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/>
                            </svg>
                        </div>
                        <p class="text-xs text-gray-400 mt-1">Indenização até R$ 10.000</p>
                    </div>
                </div>
            </a>'''
    
    return card_html


def generate_filename(flight: Dict) -> str:
    """
    Gera nome de arquivo no formato: voo-[empresa]-[numero]-[origem]-[status].html
    """
    airline_slug = slugify(flight.get('airline', ''))
    flight_number = flight.get('flight_number', '').strip().lower()
    origin = flight.get('origin', 'GRU').lower()
    status_lower = flight.get('status', '').lower()
    
    if 'atrasado' in status_lower:
        status_slug = 'atrasado'
    elif 'cancelado' in status_lower:
        status_slug = 'cancelado'
    else:
        status_slug = 'problema'
    
    return f"voo-{airline_slug}-{flight_number}-{origin}-{status_slug}.html"


def generate_home_page(flights: List[Dict], output_path: Path) -> bool:
    """
    Gera a página index.html usando substituição cirúrgica no template home.
    Apenas substitui os cards de voo e contadores, mantendo todo o resto intacto.
    """
    try:
        if not TEMPLATE_HOME.exists():
            logger.error(f"❌ Template HOME não encontrado: {TEMPLATE_HOME}")
            return False
        
        # Ler template
        with open(TEMPLATE_HOME, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Data/hora atual
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%H:%M")
        datetime_str = f"{date_str} {time_str}"
        bullet_char = "•"
        
        # Contar voos
        num_flights = len(flights)
        
        # Atualizar data/hora no badge
        template_content = re.sub(
            r'Atualizado em tempo real • \d{2}/\d{2}/\d{4} \d{2}:\d{2}',
            f'Atualizado em tempo real {bullet_char} {datetime_str}',
            template_content
        )
        
        # Atualizar contador de voos no hero
        template_content = re.sub(
            r'<strong class="text-blue-900">\d+ voos</strong>',
            f'<strong class="text-blue-900">{num_flights} voos</strong>',
            template_content
        )
        
        # Atualizar contador no banner
        template_content = re.sub(
            r'<span class="px-2 py-0.5 bg-yellow-400 text-blue-950 font-black rounded">\d+ voos</span>',
            f'<span class="px-2 py-0.5 bg-yellow-400 text-blue-950 font-black rounded">{num_flights} voos</span>',
            template_content
        )
        
        # Atualizar contador nas stats
        template_content = re.sub(
            r'<p class="text-5xl font-black text-blue-950 mb-2">\d+</p>\s*<p class="text-gray-600 font-semibold">Voos com Problemas</p>',
            f'<p class="text-5xl font-black text-blue-950 mb-2">{num_flights}</p>\n                    <p class="text-gray-600 font-semibold">Voos com Problemas</p>',
            template_content
        )
        
        # Atualizar data no footer
        template_content = re.sub(
            r'Última atualização: \d{2}/\d{2}/\d{4} às \d{2}:\d{2}',
            f'Última atualização: {datetime_str}',
            template_content
        )
        
        # Substituir links de afiliado se AFFILIATE_LINK estiver configurado
        if AFFILIATE_LINK:
            template_content = replace_affiliate_links(template_content, AFFILIATE_LINK)
        
        # Identificar e substituir o conteúdo do grid de voos
        # Procurar pela div do grid
        grid_pattern = r'(<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">)(.*?)(</div>\s*</section>)'
        
        # Gerar cards de voos
        cards_html = ""
        
        if num_flights == 0:
            # Manter os 2 cards originais do template
            logger.info("📋 Nenhum voo encontrado. Mantendo cards de exemplo do template.")
            # Não fazer nada, deixar os cards originais
        else:
            # Ordenar voos: mais recentes primeiro (ordenação cronológica rigorosa)
            # Critério 1: Data_Captura (ou Data_Partida) -> Descendente (mais recente no topo)
            # Critério 2: Horario -> Descendente
            def sort_key(flight):
                # Converte Data_Captura para datetime para ordenação correta
                capture_date_str = flight.get('capture_date', '')
                data_partida_str = flight.get('Data_Partida', '')
                horario = flight.get('scheduled_time', '') or flight.get('Hora_Partida', '') or ''
                
                # Tenta parsear Data_Captura (formato: YYYY-MM-DD)
                try:
                    if capture_date_str:
                        date_obj = datetime.strptime(capture_date_str, "%Y-%m-%d")
                    elif data_partida_str:
                        # Data_Partida está no formato DD/MM, precisa inferir o ano
                        # Usa ano atual como fallback
                        day, month = data_partida_str.split('/')
                        date_obj = datetime(datetime.now().year, int(month), int(day))
                    else:
                        # Se não tiver data, usa data muito antiga para ir para o final
                        date_obj = datetime(1900, 1, 1)
                except (ValueError, AttributeError):
                    date_obj = datetime(1900, 1, 1)
                
                # Converte Horario para datetime (formato: HH:MM)
                try:
                    if horario and ':' in horario:
                        hour, minute = map(int, horario.split(':'))
                        time_obj = datetime(1900, 1, 1, hour, minute)
                    else:
                        time_obj = datetime(1900, 1, 1, 0, 0)
                except (ValueError, AttributeError):
                    time_obj = datetime(1900, 1, 1, 0, 0)
                
                # Retorna tupla para ordenação: (data, hora) em ordem reversa
                # Mais recente primeiro = data mais recente + hora mais recente
                return (date_obj, time_obj)
            
            flights_sorted = sorted(
                flights,
                key=sort_key,
                reverse=True  # Mais recentes primeiro (descendente)
            )
            
            # Gerar cards reais
            for flight in flights_sorted:
                filename = generate_filename(flight)
                cards_html += generate_flight_card_html(flight, filename) + "\n            "
            
            # Substituir todo o conteúdo dentro do grid
            replacement = f'\\1\n            {cards_html}\n        \\3'
            template_content = re.sub(grid_pattern, replacement, template_content, flags=re.DOTALL)
        
        # Salvar arquivo
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        logger.info(f"✅ Home gerada: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar home: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def replace_affiliate_links(content: str, affiliate_link: str) -> str:
    """
    Substitui links de afiliado hardcoded no template pelo link da variável de ambiente.
    Se AFFILIATE_LINK não estiver configurado, mantém os links originais.
    """
    if not affiliate_link:
        return content
    
    # Padrões de links de afiliado encontrados nos templates
    patterns = [
        # Padrão do home_template.html
        r'https://www\.airhelp\.com/pt-br/verificar-indenizacao/[^"\s]*',
        # Padrão do template de voo (funnel.airhelp.com)
        r'https://funnel\.airhelp\.com/claims/new/trip-details[^"\s]*',
        # Padrão genérico para JavaScript
        r'const affiliateLink = "[^"]*"',
    ]
    
    # Substituir em href
    content = re.sub(
        r'href="https://(www\.airhelp\.com|funnel\.airhelp\.com)[^"]*"',
        f'href="{affiliate_link}"',
        content
    )
    
    # Substituir em JavaScript (const affiliateLink)
    content = re.sub(
        r'const affiliateLink = "[^"]*"',
        f'const affiliateLink = "{affiliate_link}";',
        content
    )
    
    return content


def replace_template_content(template_content: str, flight: Dict) -> str:
    """
    Substitui valores do template de voo pelos dados do voo.
    Mantém toda a estrutura HTML/CSS/JS intacta.
    """
    # Valores do voo KLM original (template)
    old_values = {
        'flight_number': '0792',
        'airline': 'KLM',
        'destination': 'Amsterdã',
        'origin': 'GRU',
        'status': 'Atrasado',
        'delay_hours': '0.42h',
        'scheduled_time': '21:00',
        'actual_time': '21:25',
    }
    
    # Novos valores do voo atual
    new_flight_number = flight.get('flight_number', '').strip()
    new_airline = flight.get('airline', '').strip()
    new_destination = get_destination_from_flight(flight)
    new_origin = flight.get('origin', 'GRU').strip().upper()
    new_status = flight.get('status', '').strip()
    new_delay_hours = format_delay_hours(flight.get('delay_hours', 0))
    new_scheduled_time = flight.get('scheduled_time', '').strip()
    new_actual_time = flight.get('actual_time', '').strip()
    
    # Status em português
    status_pt = 'Atrasado' if 'atrasado' in new_status.lower() else ('Cancelado' if 'cancelado' in new_status.lower() else new_status)
    
    # Realizar substituições no conteúdo
    content = template_content
    
    # Substituições diretas
    content = content.replace(old_values['flight_number'], new_flight_number)
    content = content.replace(old_values['airline'], new_airline)
    content = content.replace(old_values['destination'], new_destination)
    content = content.replace(old_values['origin'], new_origin)
    content = content.replace(old_values['status'], status_pt)
    content = content.replace(old_values['delay_hours'], new_delay_hours)
    
    # Substituições mais específicas para evitar substituições indevidas
    # Meta description
    content = content.replace(
        f'Voo {old_values["flight_number"]} da {old_values["airline"]}',
        f'Voo {new_flight_number} da {new_airline}'
    )
    
    # Title
    content = content.replace(
        f'Voo {old_values["flight_number"]} {old_values["airline"]} para {old_values["destination"]}',
        f'Voo {new_flight_number} {new_airline} para {new_destination}'
    )
    
    # Hero section - número do voo
    content = content.replace(
        f'<span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-900 to-blue-600">{old_values["flight_number"]}</span>',
        f'<span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-900 to-blue-600">{new_flight_number}</span>'
    )
    
    # Hero section - rota
    content = content.replace(
        f'{old_values["airline"]} • {old_values["origin"]} → {old_values["destination"]}',
        f'{new_airline} • {new_origin} → {new_destination}'
    )
    
    # Card de informações - número do voo
    old_pattern = f'<p class="text-2xl font-black text-blue-950">{old_values["flight_number"]}</p>'
    new_pattern = f'<p class="text-2xl font-black text-blue-950">{new_flight_number}</p>'
    content = content.replace(old_pattern, new_pattern)
    
    # Card de informações - companhia
    content = content.replace(
        f'<p class="text-lg font-black text-gray-900">{old_values["airline"]}</p>',
        f'<p class="text-lg font-black text-gray-900">{new_airline}</p>'
    )
    
    # Card de informações - atraso
    content = content.replace(
        f'<p class="text-2xl font-black text-orange-600">{old_values["delay_hours"]}</p>',
        f'<p class="text-2xl font-black text-orange-600">{new_delay_hours}</p>'
    )
    
    # JavaScript - flightNumber
    content = content.replace(
        f'const flightNumber = "{old_values["flight_number"]}";',
        f'const flightNumber = "{new_flight_number}";'
    )
    
    # JavaScript - airline
    content = content.replace(
        f'const airline = "{old_values["airline"]}";',
        f'const airline = "{new_airline}";'
    )
    
    # JavaScript - destination
    content = content.replace(
        f'const destination = "{old_values["destination"]}";',
        f'const destination = "{new_destination}";'
    )
    
    # Footer
    content = content.replace(
        f'MatchFly • Voo {old_values["flight_number"]} • {old_values["airline"]}',
        f'MatchFly • Voo {new_flight_number} • {new_airline}'
    )
    
    # WhatsApp share - número do voo
    content = content.replace(
        f'voo {old_values["flight_number"]}',
        f'voo {new_flight_number}'
    )
    
    # Schema.org JSON-LD - name
    content = content.replace(
        f'"name": "Voo {old_values["flight_number"]} - {old_values["airline"]}"',
        f'"name": "Voo {new_flight_number} - {new_airline}"'
    )
    
    # Schema.org JSON-LD - description
    content = content.replace(
        f'Voo {old_values["flight_number"]} da {old_values["airline"]} com status {old_values["status"]}',
        f'Voo {new_flight_number} da {new_airline} com status {status_pt}'
    )
    
    # Schema.org JSON-LD - organizer name
    content = content.replace(
        f'"name": "{old_values["airline"]}"',
        f'"name": "{new_airline}"',
        1  # Apenas a primeira ocorrência (no organizer)
    )
    
    # Substituir links de afiliado se AFFILIATE_LINK estiver configurado
    if AFFILIATE_LINK:
        content = replace_affiliate_links(content, AFFILIATE_LINK)
    
    return content


def clean_voo_directory(voo_dir: Path, preserve_template: Path) -> None:
    """
    Limpa a pasta public/voo/ preservando o arquivo template.
    
    NOTA: Esta função NÃO é mais usada na estratégia persistente.
    Mantida apenas para referência/compatibilidade.
    """
    if not voo_dir.exists():
        voo_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Criada pasta: {voo_dir}")
        return
    
    # Listar todos os arquivos HTML
    html_files = list(voo_dir.glob("*.html"))
    
    # Preservar template
    preserved = 0
    removed = 0
    
    for html_file in html_files:
        # Preservar o arquivo template
        if html_file.name == preserve_template.name:
            preserved += 1
            logger.debug(f"🔒 Preservado (template): {html_file.name}")
            continue
        
        # Remover outros arquivos
        try:
            html_file.unlink()
            removed += 1
            logger.debug(f"🗑️  Removido: {html_file.name}")
        except Exception as e:
            logger.warning(f"⚠️  Não foi possível remover {html_file.name}: {e}")
    
    logger.info(f"🧹 Limpeza concluída: {preserved} preservado(s), {removed} removido(s)")


def generate_flight_page(template_path: Path, flight: Dict, output_path: Path) -> bool:
    """
    Gera uma página HTML para um voo usando o template de voo como base.
    """
    try:
        # Carregar template
        if not template_path.exists():
            logger.error(f"❌ Template não encontrado: {template_path}")
            return False
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Substituir valores
        new_content = replace_template_content(template_content, flight)
        
        # Salvar arquivo
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"✅ Página gerada: {output_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar página para voo {flight.get('flight_number', 'N/A')}: {e}")
        return False


def main():
    """Função principal do script."""
    logger.info("🚀 Iniciando geração do site MatchFly (templates separados)...")
    
    # Verificar e criar pastas necessárias
    public_dir = Path("public")
    voo_dir = Path("public/voo")
    public_dir.mkdir(parents=True, exist_ok=True)
    voo_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Pastas verificadas/criadas: {public_dir}, {voo_dir}")
    
    # Verificar AFFILIATE_LINK
    if AFFILIATE_LINK:
        logger.info(f"✅ AFFILIATE_LINK configurado: {AFFILIATE_LINK[:50]}...")
    else:
        logger.warning("⚠️  AFFILIATE_LINK não configurado - links originais serão mantidos")
        logger.warning("   Configure a variável de ambiente AFFILIATE_LINK para usar links personalizados")
    
    # Caminhos
    data_file = Path("data/flights-db.json")
    index_file = Path("public/index.html")
    
    # Verificar se templates existem
    if not TEMPLATE_HOME.exists():
        logger.error(f"❌ Template HOME não encontrado: {TEMPLATE_HOME}")
        logger.error("   O arquivo home_template.html é obrigatório.")
        return
    
    if not TEMPLATE_VOO.exists():
        logger.error(f"❌ Template VOO não encontrado: {TEMPLATE_VOO}")
        logger.error("   O arquivo public/voo/voo-klm-0792-gru-atrasado.html é obrigatório.")
        return
    
    logger.info(f"📄 Template HOME: {TEMPLATE_HOME.name}")
    logger.info(f"📄 Template VOO: {TEMPLATE_VOO.name}")
    
    # 1. NÃO limpar pasta public/voo/ - estratégia persistente
    # Apenas verificar se a pasta existe
    logger.info("📁 Verificando pasta public/voo/ (estratégia persistente - não limpa arquivos)...")
    if not voo_dir.exists():
        voo_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Pasta criada: {voo_dir}")
    else:
        existing_files = list(voo_dir.glob("*.html"))
        logger.info(f"📊 Arquivos existentes em public/voo/: {len(existing_files)} (serão preservados)")
    
    # 2. Carregar dados com VALIDAÇÃO DE INTEGRIDADE e CORREÇÃO AUTOMÁTICA
    logger.info("=" * 70)
    logger.info("🔍 CARREGANDO DADOS DE VOOS")
    logger.info("=" * 70)
    
    flights = []
    
    # Tenta carregar do JSON primeiro
    if data_file.exists():
        logger.info(f"📄 Tentando carregar de: {data_file}")
        success, message, flights_json = load_flights_safely(data_file)
        
        if success and flights_json:
            flights = flights_json
            logger.info(f"✅ {message}")
            logger.info(f"📊 Total de voos carregados do JSON: {len(flights)}")
        else:
            logger.warning(f"⚠️  JSON vazio ou inválido: {message}")
    
    # Se não tiver voos do JSON, tenta carregar do CSV
    if not flights:
        csv_path = Path("voos_atrasados_gru.csv")
        if csv_path.exists():
            logger.info(f"📄 Tentando carregar de: {csv_path}")
            flights_csv = convert_csv_to_json_flights(csv_path)
            if flights_csv:
                flights = flights_csv
                logger.info(f"✅ {len(flights)} voo(s) carregado(s) do CSV")
                
                # Salva no JSON para próxima vez
                try:
                    json_data = {
                        "flights": flights,
                        "metadata": {
                            "scraped_at": datetime.now().isoformat() + "+00:00",
                            "source": "csv_conversion:voos_atrasados_gru.csv",
                            "total_flights": len(flights)
                        }
                    }
                    with open(data_file, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"💾 Dados salvos em {data_file} para próxima execução")
                except Exception as e:
                    logger.warning(f"⚠️  Não foi possível salvar JSON: {e}")
            else:
                logger.warning("⚠️  CSV não contém voos válidos")
        else:
            logger.warning(f"⚠️  CSV não encontrado: {csv_path}")
    
    # Proteção: se lista estiver vazia após carregar, avisa mas continua
    if not flights:
        logger.warning("⚠️  AVISO: Nenhum voo encontrado no banco de dados!")
        logger.warning("   Isso pode indicar que o scraper não capturou dados ainda.")
        logger.warning("   O site será gerado sem voos (mostrará apenas template).")
    else:
        logger.info(f"✅ {len(flights)} voo(s) carregado(s) com sucesso")
        logger.info("=" * 70)
    
    # 2.5. FILTRO ANTI-N/A: Remove voos sem companhia válida (limpeza de dados)
    flights_before_filter = len(flights)
    flights = [
        f for f in flights
        if f.get('airline', '').strip() and 
           f.get('airline', '').strip().upper() != 'N/A' and
           f.get('airline', '').strip() != ''
    ]
    flights_filtered = flights_before_filter - len(flights)
    if flights_filtered > 0:
        logger.info(f"🧹 Filtrados {flights_filtered} voo(s) sem companhia válida (N/A removidos)")
    
    # 3. Filtrar voos com problemas (Atrasado ou Cancelado)
    problematic_flights = [
        f for f in flights
        if f.get('status', '').upper() in ['ATRASADO', 'CANCELADO']
    ]
    
    logger.info(f"🎯 Voos com problemas encontrados: {len(problematic_flights)}")
    
    # 4. Gerar páginas individuais de voos (estratégia persistente)
    # PERCORRE TODA A LISTA ACUMULADA do banco de dados
    generated_pages = []
    success_count = 0
    failure_count = 0
    skipped_existing = 0
    total_processed = 0
    
    logger.info(f"🔄 Processando {len(problematic_flights)} voo(s) do banco de dados para gerar páginas...")
    
    for flight in problematic_flights:
        total_processed += 1
        flight_num = flight.get('flight_number', 'N/A')
        
        # Pular se for o voo do template (KLM 0792)
        if (flight.get('airline', '').upper() == 'KLM' and 
            flight.get('flight_number', '').strip() == '0792'):
            logger.debug(f"⏭️  [{total_processed}/{len(problematic_flights)}] Pulando voo template: KLM 0792")
            # Adiciona à lista mesmo assim para aparecer na home
            generated_pages.append(flight)
            continue
        
        filename = generate_filename(flight)
        output_path = voo_dir / filename
        
        # Verifica se o arquivo já existe (persistência - não sobrescreve)
        if output_path.exists():
            skipped_existing += 1
            logger.debug(f"⏭️  [{total_processed}/{len(problematic_flights)}] Arquivo já existe (preservado): {filename}")
            # Adiciona à lista mesmo assim para aparecer na home
            generated_pages.append(flight)
            continue
        
        # Gera apenas se não existir (novo voo)
        logger.info(f"📄 [{total_processed}/{len(problematic_flights)}] Gerando página para voo {flight_num}...")
        if generate_flight_page(TEMPLATE_VOO, flight, output_path):
            success_count += 1
            generated_pages.append(flight)
            logger.debug(f"   ✅ Página gerada: {filename}")
        else:
            failure_count += 1
            logger.warning(f"   ❌ Falha ao gerar página para voo {flight_num}")
    
    logger.info(f"📊 Processamento completo:")
    logger.info(f"   • Total processado: {total_processed} voos")
    logger.info(f"   • Novas páginas geradas: {success_count}")
    logger.info(f"   • Páginas já existentes (preservadas): {skipped_existing}")
    logger.info(f"   • Falhas: {failure_count}")
    logger.info(f"   • Total na lista final: {len(generated_pages)} voos")
    
    # 5. Gerar index.html usando template HOME
    # ESTRATÉGIA PERSISTENTE: Listar TODOS os voos do banco de dados na home
    # (não apenas os gerados nesta execução)
    all_flights_for_home = []
    
    # Adicionar TODOS os voos problemáticos do banco (histórico completo)
    all_flights_for_home.extend(problematic_flights)
    
    # Remover duplicatas baseado em flight_number + scheduled_time
    seen = set()
    unique_flights = []
    for flight in all_flights_for_home:
        flight_key = (
            str(flight.get('flight_number', '')).strip(),
            str(flight.get('scheduled_time', '')).strip()
        )
        if flight_key not in seen:
            seen.add(flight_key)
            unique_flights.append(flight)
    
    all_flights_for_home = unique_flights
    
    # Ordenar: mais recentes primeiro (ordenação cronológica rigorosa)
    # Critério 1: Data_Captura (ou Data_Partida) -> Descendente (mais recente no topo)
    # Critério 2: Horario -> Descendente
    def home_sort_key(flight):
        # Converte Data_Captura para datetime para ordenação correta
        capture_date_str = flight.get('capture_date', '')
        data_partida_str = flight.get('Data_Partida', '')
        horario = flight.get('scheduled_time', '') or flight.get('Hora_Partida', '') or ''
        
        # Tenta parsear Data_Captura (formato: YYYY-MM-DD)
        try:
            if capture_date_str:
                date_obj = datetime.strptime(capture_date_str, "%Y-%m-%d")
            elif data_partida_str:
                # Data_Partida está no formato DD/MM, precisa inferir o ano
                # Usa ano atual como fallback
                day, month = data_partida_str.split('/')
                date_obj = datetime(datetime.now().year, int(month), int(day))
            else:
                # Se não tiver data, usa data muito antiga para ir para o final
                date_obj = datetime(1900, 1, 1)
        except (ValueError, AttributeError):
            date_obj = datetime(1900, 1, 1)
        
        # Converte Horario para datetime (formato: HH:MM)
        try:
            if horario and ':' in horario:
                hour, minute = map(int, horario.split(':'))
                time_obj = datetime(1900, 1, 1, hour, minute)
            else:
                time_obj = datetime(1900, 1, 1, 0, 0)
        except (ValueError, AttributeError):
            time_obj = datetime(1900, 1, 1, 0, 0)
        
        # Retorna tupla para ordenação: (data, hora) em ordem reversa
        # Mais recente primeiro = data mais recente + hora mais recente
        return (date_obj, time_obj)
    
    all_flights_for_home.sort(key=home_sort_key, reverse=True)
    
    logger.info(f"📋 Total de voos únicos para home: {len(all_flights_for_home)}")
    
    # Gerar home com todos os voos (histórico completo)
    if generate_home_page(all_flights_for_home, index_file):
        logger.info(f"✅ Index.html gerado com {len(all_flights_for_home)} voos listados (histórico completo)")
    else:
        logger.warning("⚠️  Falha ao gerar index.html")
    
    logger.info("✨ Geração do site concluída!")


if __name__ == "__main__":
    main()
