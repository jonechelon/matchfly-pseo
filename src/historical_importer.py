#!/usr/bin/env python3
"""
MatchFly Historical Data Importer - ANAC SIROS Integration
===========================================================
Script de importação massiva de dados históricos da ANAC.
Baixa CSVs DIÁRIOS oficiais do servidor SIROS e popula o banco de dados.

Fonte: SIROS - Sistema de Registro de Operações da ANAC
Dataset: Registros Diários de Voos
URL Base: https://siros.anac.gov.br/siros/registros/registros/serie/{ano}/
Formato: registros_YYYY-MM-DD.csv (um arquivo por dia)

Author: MatchFly Team (Data Engineering)
Date: 2026-01-12
Version: 2.0.0 - Download diário otimizado com processamento em chunks
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
import requests
import urllib3

# Desabilita avisos de SSL do macOS
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Tenta importar pandas (será instalado se necessário)
try:
    import pandas as pd
except ImportError:
    print("❌ pandas não encontrado. Instalando...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])
    import pandas as pd

# Importa funções do gerador
from generator import get_iata_code, CITY_TO_IATA

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('historical_importer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# MAPEAMENTO DE COMPANHIAS AÉREAS (ICAO → Nome Completo)
# ============================================================
AIRLINE_MAPPING = {
    # Brasileiras
    "G3": "GOL",
    "AD": "AZUL",
    "LA": "LATAM",
    "2Z": "Voepass",
    "JJ": "LATAM",  # Código alternativo
    "O6": "Avianca Brasil",
    
    # Internacionais - Europa
    "AF": "Air France",
    "KL": "KLM",
    "LH": "Lufthansa",
    "BA": "British Airways",
    "IB": "Iberia",
    "TP": "TAP Portugal",
    "AZ": "ITA Airways",
    "LX": "Swiss",
    "OS": "Austrian Airlines",
    "SN": "Brussels Airlines",
    
    # Internacionais - América do Sul
    "AR": "Aerolíneas Argentinas",
    "LA": "LATAM",
    "4M": "LATAM Argentina",
    "CM": "Copa Airlines",
    "AV": "Avianca",
    
    # Internacionais - América do Norte
    "AA": "American Airlines",
    "DL": "Delta",
    "UA": "United Airlines",
    "AC": "Air Canada",
    "AM": "Aeroméxico",
    
    # Outras
    "EK": "Emirates",
    "QR": "Qatar Airways",
    "TK": "Turkish Airlines",
    "ET": "Ethiopian Airlines",
    "SA": "South African Airways",
}

# ============================================================
# MAPEAMENTO DE AEROPORTOS ICAO → CIDADE (Destinos Comuns de GRU)
# ============================================================
ICAO_TO_CITY = {
    # Europa
    "LFPG": "Paris",
    "LPPT": "Lisboa",
    "LEMD": "Madrid",
    "LIRF": "Roma",
    "EGLL": "Londres",
    "EDDM": "Munique",
    "EHAM": "Amsterdam",
    "LSZH": "Zurique",
    
    # Brasil
    "SBGL": "Rio de Janeiro",
    "SBBR": "Brasília",
    "SBCF": "Belo Horizonte",
    "SBSV": "Salvador",
    "SBPA": "Porto Alegre",
    "SBCT": "Curitiba",
    "SBRJ": "Rio de Janeiro (Santos Dumont)",
    "SBRF": "Recife",
    "SBFZ": "Fortaleza",
    "SBEG": "Porto Alegre (Salgado Filho)",
    
    # América do Sul
    "SAEZ": "Buenos Aires",
    "SCEL": "Santiago",
    "SUMU": "Montevideo",
    "SLLP": "La Paz",
    "SPIM": "Lima",
    
    # América do Norte
    "KMIA": "Miami",
    "KJFK": "Nova York",
    "KATL": "Atlanta",
    "MMMX": "Cidade do México",
    
    # Oriente Médio/África
    "OMDB": "Dubai",
    "OTHH": "Doha",
    "FAOR": "Joanesburgo",
}


class ANACHistoricalImporter:
    """Importador de dados históricos da ANAC para o MatchFly."""
    
    def __init__(
        self,
        output_file: str = "data/flights-db.json",
        airport_code: str = "SBGR",
        min_delay_minutes: int = 15,
        days_lookback: int = 30
    ):
        """
        Inicializa o importador.
        
        Args:
            output_file: Arquivo JSON de saída
            airport_code: Código ICAO do aeroporto (SBGR = Guarulhos)
            min_delay_minutes: Atraso mínimo para considerar (minutos)
            days_lookback: Quantos dias no passado buscar dados
        """
        self.output_file = Path(output_file)
        self.airport_code = airport_code
        self.min_delay_minutes = min_delay_minutes
        self.days_lookback = days_lookback
        
        # Estatísticas
        self.stats = {
            'downloaded_files': 0,
            'total_rows': 0,
            'filtered_sbgr': 0,
            'delayed_flights': 0,
            'imported': 0,
            'duplicates': 0,
            'errors': 0
        }
        
        # Cache de voos já existentes (para evitar duplicatas)
        self.existing_flights: Set[str] = set()
    
    def get_anac_download_urls(self) -> List[str]:
        """
        Obtém URLs de download dos CSVs DIÁRIOS da ANAC/SIROS.
        
        FORMATO CORRETO SIROS:
        - URL Base: https://siros.anac.gov.br/siros/registros/registros/serie/{ano}/
        - Formato: registros_YYYY-MM-DD.csv (um arquivo POR DIA)
        - Exemplo: registros_2025-05-01.csv
        
        Estratégia:
        - Busca últimos 30 dias (retroativo)
        - Um arquivo por dia
        
        Returns:
            Lista de URLs para download (ordem: mais recente → mais antigo)
        """
        logger.info("🔍 Gerando URLs de download (SIROS - registros diários)...")
        
        # Calcula intervalo de datas (últimos 30 dias)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days_lookback)
        
        logger.info(f"📅 Intervalo de busca:")
        logger.info(f"   De: {start_date.strftime('%d/%m/%Y')} ({start_date.strftime('%A')})")
        logger.info(f"   Até: {end_date.strftime('%d/%m/%Y')} ({end_date.strftime('%A')})")
        logger.info(f"   Total: {self.days_lookback} dias")
        logger.info("")
        
        # Gera lista de datas
        urls = []
        current_date = end_date
        
        while current_date >= start_date:
            year = current_date.year
            date_str = current_date.strftime('%Y-%m-%d')
            
            # URL SIROS correta
            # Para 2025: https://siros.anac.gov.br/siros/registros/registros/serie/2025/registros_2025-05-01.csv
            # Para 2026: https://siros.anac.gov.br/siros/registros/registros/serie/2026/registros_2026-01-12.csv
            base_url = f"https://siros.anac.gov.br/siros/registros/registros/serie/{year}"
            filename = f"registros_{date_str}.csv"
            url = f"{base_url}/{filename}"
            
            urls.append(url)
            current_date -= timedelta(days=1)
        
        logger.info(f"🎯 Total de arquivos a tentar: {len(urls)}")
        logger.info(f"🌐 Servidor: SIROS (siros.anac.gov.br)")
        logger.info(f"📦 Formato: registros_YYYY-MM-DD.csv (um por dia)")
        logger.info("")
        
        return urls
    
    def download_csv(self, url: str, output_path: Path, add_delay: bool = True) -> bool:
        """
        Baixa um arquivo CSV diário da ANAC/SIROS com rate limiting.
        
        Args:
            url: URL do arquivo (formato: .../serie/YYYY/registros_YYYY-MM-DD.csv)
            output_path: Caminho local para salvar
            add_delay: Se True, adiciona delay de 1-2s entre requisições
            
        Returns:
            True se download bem-sucedido, False caso contrário
        """
        try:
            # Extrai data da URL (registros_2025-05-01.csv)
            filename_match = re.search(r'registros_(\d{4}-\d{2}-\d{2})\.csv', url)
            if filename_match:
                date_str = filename_match.group(1)
                
                # Formata para exibição (2025-05-01 → 01/Mai/2025)
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    date_display = date_obj.strftime('%d/%b/%Y')
                except:
                    date_display = date_str
            else:
                date_str = 'desconhecido'
                date_display = date_str
            
            logger.info(f"📥 Baixando: {date_display}...")
            
            # Headers realísticos (simula navegador comum)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Referer': 'https://siros.anac.gov.br/',
            }
            
            # Rate limiting: delay entre requisições (evita bloqueio)
            if add_delay:
                time.sleep(1.5)  # 1.5s entre downloads
            
            # Desabilita verificação SSL para evitar avisos no macOS
            response = requests.get(
                url, 
                headers=headers, 
                timeout=90,  # 90s timeout (arquivos podem ser grandes)
                stream=True,
                verify=False  # Fix SSL macOS
            )
            
            if response.status_code == 200:
                # Salva arquivo em chunks (eficiente para arquivos grandes)
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # Filtra keep-alive chunks
                            f.write(chunk)
                
                file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                logger.info(f"   ✅ {date_display}: {file_size:.2f} MB")
                self.stats['downloaded_files'] += 1
                return True
            
            elif response.status_code == 404:
                # Erro 404: Arquivo ainda não publicado (normal para datas recentes)
                logger.debug(f"   ℹ️  {date_display}: não disponível (404)")
                return False
            
            else:
                # Outros erros HTTP
                logger.warning(f"   ⚠️  {date_display}: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            logger.warning(f"   ⏱️  {date_display}: timeout (>90s)")
            return False
        except requests.exceptions.ConnectionError:
            logger.warning(f"   🔌 {date_display}: erro de conexão")
            return False
        except Exception as e:
            logger.warning(f"   ❌ {date_display}: {str(e)[:50]}")
            return False
    
    def parse_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """
        Parse data e hora da ANAC para datetime.
        
        Args:
            date_str: Data no formato DD/MM/YYYY ou YYYY-MM-DD
            time_str: Hora no formato HH:MM ou HH:MM:SS
            
        Returns:
            Objeto datetime ou None se inválido
        """
        try:
            # Remove espaços extras
            date_str = str(date_str).strip()
            time_str = str(time_str).strip()
            
            # Tenta diferentes formatos de data
            for date_format in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                try:
                    date_obj = datetime.strptime(date_str, date_format)
                    break
                except ValueError:
                    continue
            else:
                logger.debug(f"Formato de data inválido: {date_str}")
                return None
            
            # Parse hora (aceita HH:MM ou HH:MM:SS)
            if len(time_str.split(':')) == 2:
                time_obj = datetime.strptime(time_str, '%H:%M').time()
            else:
                time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
            
            # Combina data e hora
            return datetime.combine(date_obj, time_obj)
            
        except Exception as e:
            logger.debug(f"Erro ao parsear data/hora: {date_str} {time_str} - {e}")
            return None
    
    def calculate_delay(self, scheduled_dt: datetime, actual_dt: datetime) -> int:
        """
        Calcula atraso em minutos.
        
        Args:
            scheduled_dt: Horário previsto
            actual_dt: Horário real
            
        Returns:
            Atraso em minutos (positivo = atrasado, negativo = adiantado)
        """
        delta = actual_dt - scheduled_dt
        return int(delta.total_seconds() / 60)
    
    def process_csv_file(self, csv_path: Path, flight_date: str) -> List[Dict]:
        """
        Processa um arquivo CSV diário da ANAC/SIROS usando chunks para eficiência.
        
        Args:
            csv_path: Caminho do arquivo CSV
            flight_date: Data do voo (extraída do nome do arquivo YYYY-MM-DD)
            
        Returns:
            Lista de voos processados
        """
        logger.info(f"📊 Processando: {csv_path.name}")
        
        delayed_flights = []
        
        try:
            # ============================================================
            # LEITURA EFICIENTE COM CHUNKS (otimizado para i5 16GB)
            # ============================================================
            # Lê apenas colunas necessárias para economizar memória
            columns_needed = [
                'Sigla ICAO Empresa Aérea',
                'Número Voo',
                'Código ICAO Aeródromo Origem',
                'Código ICAO Aeródromo Destino',
                'Situação Voo',
                'Partida Prevista',
                'Partida Real',
            ]
            
            # Tenta ler com encoding padrão ANAC
            encoding = 'latin-1'
            delimiter = ';'
            
            # Lê em chunks de 50k linhas por vez (eficiente para 16GB RAM)
            chunk_size = 50000
            total_processed = 0
            
            logger.info(f"   🔧 Modo: Processamento em chunks ({chunk_size:,} linhas/chunk)")
            logger.info(f"   📦 Encoding: {encoding} | Delimiter: '{delimiter}'")
            
            # Primeira leitura para verificar colunas disponíveis
            try:
                df_sample = pd.read_csv(
                    csv_path, 
                    sep=delimiter, 
                    encoding=encoding, 
                    nrows=5,
                    low_memory=False
                )
                
                # Normaliza nomes de colunas
                normalized_cols = [self._normalize_column_name(col) for col in df_sample.columns]
                df_sample.columns = normalized_cols
                
                # Identifica colunas relevantes
                col_mapping = self._identify_columns(normalized_cols)
                
                if not col_mapping or 'origin' not in col_mapping:
                    logger.error("   ❌ Colunas necessárias não encontradas")
                    logger.info(f"   📋 Colunas disponíveis: {', '.join(normalized_cols[:10])}...")
                    return []
                
                logger.info(f"   🔑 Colunas mapeadas: {len(col_mapping)}")
                
            except Exception as e:
                logger.error(f"   ❌ Erro ao ler arquivo: {e}")
                # Tenta encoding alternativo
                try:
                    encoding = 'cp1252'
                    df_sample = pd.read_csv(csv_path, sep=delimiter, encoding=encoding, nrows=5)
                    logger.info(f"   ✅ Encoding alternativo: {encoding}")
                except:
                    return []
            
            # ============================================================
            # PROCESSAMENTO EM CHUNKS
            # ============================================================
            chunk_num = 0
            
            for chunk in pd.read_csv(
                csv_path, 
                sep=delimiter, 
                encoding=encoding, 
                chunksize=chunk_size,
                low_memory=False
            ):
                chunk_num += 1
                
                # Normaliza colunas do chunk
                chunk.columns = [self._normalize_column_name(col) for col in chunk.columns]
                
                total_processed += len(chunk)
                
                # Filtro 1: Apenas SBGR (origem)
                origin_col = col_mapping.get('origin')
                if origin_col and origin_col in chunk.columns:
                    chunk_sbgr = chunk[chunk[origin_col].astype(str).str.upper() == self.airport_code]
                else:
                    chunk_sbgr = pd.DataFrame()  # Vazio se não encontrar coluna
                
                if len(chunk_sbgr) == 0:
                    continue
                
                # Processa cada linha do chunk
                for idx, row in chunk_sbgr.iterrows():
                    try:
                        flight = self._process_row(row, col_mapping, flight_date)
                        
                        if flight and flight.get('delay_min', 0) >= self.min_delay_minutes:
                            delayed_flights.append(flight)
                            self.stats['delayed_flights'] += 1
                            
                    except Exception as e:
                        logger.debug(f"   ⚠️  Erro linha {idx}: {str(e)[:50]}")
                        self.stats['errors'] += 1
                        continue
                
                # Log de progresso
                if chunk_num % 5 == 0:
                    logger.info(f"   ⏳ Chunk {chunk_num}: {total_processed:,} linhas processadas...")
            
            self.stats['total_rows'] += total_processed
            self.stats['filtered_sbgr'] += len(delayed_flights)
            
            logger.info(f"   ✅ Total processado: {total_processed:,} linhas")
            logger.info(f"   🎯 Voos atrasados SBGR (>{self.min_delay_minutes}min): {len(delayed_flights):,}")
            
        except Exception as e:
            logger.error(f"   ❌ Erro ao processar CSV: {e}")
            self.stats['errors'] += 1
        
        return delayed_flights
    
    def _normalize_column_name(self, col: str) -> str:
        """Normaliza nome de coluna (remove acentos, lowercase, etc.)."""
        import unicodedata
        
        # Remove acentos
        col = unicodedata.normalize('NFKD', str(col))
        col = col.encode('ASCII', 'ignore').decode('ASCII')
        
        # Lowercase e remove espaços extras
        col = col.lower().strip()
        
        # Remove caracteres especiais (mantém apenas letras, números e underscore)
        col = re.sub(r'[^a-z0-9_]', '_', col)
        
        # Remove underscores duplicados
        col = re.sub(r'_+', '_', col)
        
        return col.strip('_')
    
    def _identify_columns(self, columns: List[str]) -> Dict[str, str]:
        """
        Identifica colunas relevantes no CSV da ANAC/SIROS por padrões.
        
        Colunas-alvo do SIROS:
        - Sigla ICAO Empresa Aérea
        - Número Voo
        - Partida Prevista
        - Partida Real
        - ICAO Aeródromo Origem
        - ICAO Aeródromo Destino
        
        Returns:
            Dicionário mapeando nome lógico → nome real da coluna
        """
        col_mapping = {}
        
        # Padrões de busca (priorizando formato SIROS/VRA)
        patterns = {
            'airline_code': [
                'sigla_icao_empresa_aerea',
                'sigla_icao',
                'sigla',
                'empresa',
                'companhia',
                'icao_empresa'
            ],
            'flight_number': [
                'numero_voo',
                'numero',
                'voo',
                'flight'
            ],
            'origin': [
                'icao_aerodromo_origem',
                'aeroporto_origem',
                'origem',
                'origin',
                'icao_origem',
                'aerodromo_origem'
            ],
            'destination': [
                'icao_aerodromo_destino',
                'aeroporto_destino',
                'destino',
                'destination',
                'icao_destino',
                'aerodromo_destino'
            ],
            'scheduled_datetime': [
                'partida_prevista',
                'data_partida_prevista',
                'data_prevista',
                'horario_previsto'
            ],
            'actual_datetime': [
                'partida_real',
                'data_partida_real',
                'data_real',
                'horario_real'
            ],
            'status': [
                'situacao_voo',
                'situacao',
                'status'
            ],
        }
        
        # Busca por padrões (case-insensitive)
        for logical_name, keywords in patterns.items():
            for col in columns:
                if any(keyword in col for keyword in keywords):
                    col_mapping[logical_name] = col
                    break
        
        return col_mapping
    
    def _process_row(self, row: pd.Series, col_mapping: Dict[str, str], flight_date: str = None) -> Optional[Dict]:
        """
        Processa uma linha do CSV SIROS/VRA e converte para formato MatchFly.
        
        Args:
            row: Linha do DataFrame
            col_mapping: Mapeamento de colunas
            
        Returns:
            Dicionário com dados do voo ou None se inválido
        """
        try:
            # Extrai dados básicos
            airline_code = str(row.get(col_mapping.get('airline_code', ''), '')).strip()
            flight_number = str(row.get(col_mapping.get('flight_number', ''), '')).strip()
            origin = str(row.get(col_mapping.get('origin', ''), '')).strip().upper()
            destination_icao = str(row.get(col_mapping.get('destination', ''), '')).strip().upper()
            
            # Valida campos obrigatórios básicos
            if not all([airline_code, flight_number, origin, destination_icao]):
                return None
            
            # FILTRO DE ORIGEM: Apenas SBGR (Guarulhos)
            if origin != self.airport_code:
                return None
            
            # ============================================================
            # PARSE DE DATA/HORA (FORMATO SIROS)
            # ============================================================
            # No SIROS, "Partida Prevista" e "Partida Real" podem conter:
            # - Data + Hora juntos (ex: "2025-11-15 14:30:00")
            # - Ou separados em colunas diferentes
            
            # Tenta obter datetime combinado primeiro
            scheduled_datetime_str = str(row.get(col_mapping.get('scheduled_datetime', ''), '')).strip()
            actual_datetime_str = str(row.get(col_mapping.get('actual_datetime', ''), '')).strip()
            
            # Se não tem datetime combinado, tenta colunas separadas (fallback)
            if not scheduled_datetime_str or scheduled_datetime_str in ['nan', 'None', '']:
                scheduled_date = row.get(col_mapping.get('scheduled_date', ''))
                scheduled_time = row.get(col_mapping.get('scheduled_time', ''))
                if scheduled_date and scheduled_time:
                    scheduled_dt = self.parse_datetime(scheduled_date, scheduled_time)
                else:
                    return None
            else:
                # Parse datetime combinado
                scheduled_dt = None
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M']:
                    try:
                        scheduled_dt = datetime.strptime(scheduled_datetime_str, fmt)
                        break
                    except ValueError:
                        continue
                if not scheduled_dt:
                    return None
            
            # Parse actual datetime
            if not actual_datetime_str or actual_datetime_str in ['nan', 'None', '']:
                actual_date = row.get(col_mapping.get('actual_date', ''))
                actual_time = row.get(col_mapping.get('actual_time', ''))
                if actual_date and actual_time:
                    actual_dt = self.parse_datetime(actual_date, actual_time)
                else:
                    return None
            else:
                actual_dt = None
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M']:
                    try:
                        actual_dt = datetime.strptime(actual_datetime_str, fmt)
                        break
                    except ValueError:
                        continue
                if not actual_dt:
                    return None
            
            # Valida que ambos foram parseados
            if not scheduled_dt or not actual_dt:
                return None
            
            # ============================================================
            # CÁLCULO DE ATRASO
            # ============================================================
            delay_minutes = self.calculate_delay(scheduled_dt, actual_dt)
            
            # Filtra apenas atrasos significativos (> 15 minutos)
            if delay_minutes < self.min_delay_minutes:
                return None
            
            # ============================================================
            # FILTRO DE DATA: Últimos 30 dias
            # ============================================================
            cutoff_date = datetime.now() - timedelta(days=self.days_lookback)
            if scheduled_dt < cutoff_date:
                return None
            
            # ============================================================
            # CONVERSÃO ICAO → CIDADE (usando mapa de aeroportos comuns)
            # ============================================================
            destination_city = ICAO_TO_CITY.get(destination_icao, destination_icao)
            
            # ============================================================
            # MAPEAMENTO PARA FORMATO MATCHFLY
            # ============================================================
            
            # Mapeia companhia aérea
            airline_name = AIRLINE_MAPPING.get(airline_code, airline_code)
            
            # Limpa número do voo (remove espaços e prefixos)
            flight_number_clean = re.sub(r'\s+', '', flight_number)
            # Remove prefixo ICAO se presente (ex: "G31234" → "1234")
            flight_number_clean = re.sub(r'^[A-Z]{1,2}', '', flight_number_clean)
            flight_number_clean = flight_number_clean.lstrip('0')  # Remove zeros à esquerda
            
            # Determina status baseado no atraso
            status = "Atrasado"
            if delay_minutes > 240:  # > 4 horas, provavelmente cancelado
                status_col = col_mapping.get('status')
                if status_col:
                    status_raw = str(row.get(status_col, '')).lower()
                    if 'cancel' in status_raw:
                        status = "Cancelado"
            
            # Monta objeto de voo no formato MatchFly
            flight = {
                'flight_number': flight_number_clean,
                'airline': airline_name,
                'status': status,
                'scheduled_time': scheduled_dt.strftime('%H:%M'),
                'actual_time': actual_dt.strftime('%H:%M'),
                'delay_hours': round(delay_minutes / 60, 2),
                'delay_min': delay_minutes,
                'origin': 'GRU',  # Guarulhos (SBGR → GRU)
                'destination': destination_city,
                'numero': flight_number_clean,
                'companhia': airline_name,
                'horario': scheduled_dt.strftime('%H:%M'),
                
                # Metadados adicionais
                'scheduled_date': scheduled_dt.strftime('%Y-%m-%d'),
                'actual_date': actual_dt.strftime('%Y-%m-%d'),
                'destination_icao': destination_icao,  # Preserva código ICAO original
            }
            
            return flight
            
        except Exception as e:
            logger.debug(f"Erro ao processar linha: {e}")
            return None
    
    def load_existing_flights(self) -> None:
        """Carrega voos existentes do arquivo JSON para evitar duplicatas."""
        try:
            if self.output_file.exists():
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                existing = data.get('flights', [])
                
                # Cria identificador único: airline + flight_number + scheduled_date
                for flight in existing:
                    flight_id = self._get_flight_id(flight)
                    self.existing_flights.add(flight_id)
                
                logger.info(f"📚 Voos existentes carregados: {len(self.existing_flights)}")
            else:
                logger.info("📚 Nenhum banco de dados existente encontrado (será criado)")
                
        except Exception as e:
            logger.error(f"❌ Erro ao carregar voos existentes: {e}")
    
    def _get_flight_id(self, flight: Dict) -> str:
        """
        Gera identificador único para um voo.
        
        Args:
            flight: Dicionário com dados do voo
            
        Returns:
            String identificadora única
        """
        airline = flight.get('airline', '').lower()
        number = flight.get('flight_number', '').lower()
        date = flight.get('scheduled_date', flight.get('scheduled_time', ''))
        
        return f"{airline}-{number}-{date}"
    
    def merge_flights(self, new_flights: List[Dict]) -> int:
        """
        Mescla novos voos com banco existente, evitando duplicatas.
        
        Args:
            new_flights: Lista de novos voos a adicionar
            
        Returns:
            Número de voos adicionados
        """
        logger.info(f"🔄 Mesclando {len(new_flights)} novos voos com banco existente...")
        
        # Carrega dados existentes
        if self.output_file.exists():
            with open(self.output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                'flights': [],
                'metadata': {}
            }
        
        existing_flights = data.get('flights', [])
        added_count = 0
        
        # Adiciona novos voos (evita duplicatas)
        for flight in new_flights:
            flight_id = self._get_flight_id(flight)
            
            if flight_id not in self.existing_flights:
                existing_flights.append(flight)
                self.existing_flights.add(flight_id)
                added_count += 1
            else:
                self.stats['duplicates'] += 1
        
        # Atualiza metadata
        data['flights'] = existing_flights
        data['metadata'] = {
            'last_import': datetime.now(tz=None).isoformat(),
            'source': 'anac_vra_historical',
            'total_flights': len(existing_flights),
            'import_stats': self.stats
        }
        
        # Salva arquivo
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Banco de dados atualizado: {added_count} novos voos adicionados")
        logger.info(f"   Total no banco: {len(existing_flights)} voos")
        
        return added_count
    
    def cleanup_temp_files(self, temp_dir: Path) -> None:
        """Remove arquivos temporários."""
        try:
            if temp_dir.exists():
                for file in temp_dir.glob('*.csv'):
                    file.unlink()
                temp_dir.rmdir()
                logger.info("🧹 Arquivos temporários removidos")
        except Exception as e:
            logger.warning(f"⚠️  Erro ao limpar arquivos temporários: {e}")
    
    def print_summary(self) -> None:
        """Imprime sumário da importação."""
        logger.info("")
        logger.info("╔" + "═" * 68 + "╗")
        logger.info("║" + " " * 18 + "✅ IMPORTAÇÃO FINALIZADA!" + " " * 21 + "║")
        logger.info("╚" + "═" * 68 + "╝")
        logger.info("")
        logger.info("📊 SUMÁRIO DA IMPORTAÇÃO:")
        logger.info(f"   • Arquivos baixados:        {self.stats['downloaded_files']}")
        logger.info(f"   • Total de linhas lidas:    {self.stats['total_rows']:,}")
        logger.info(f"   • Voos de {self.airport_code}:           {self.stats['filtered_sbgr']:,}")
        logger.info(f"   • Voos com atraso >15min:   {self.stats['delayed_flights']:,}")
        logger.info(f"   • Voos importados (novos):  {self.stats['imported']}")
        logger.info(f"   • Duplicatas ignoradas:     {self.stats['duplicates']}")
        logger.info(f"   • Erros:                    {self.stats['errors']}")
        logger.info("")
        logger.info(f"📁 Banco de dados: {self.output_file}")
        logger.info("")
    
    def play_success_sound(self) -> None:
        """Toca som de sucesso (Glass.aiff no macOS)."""
        try:
            subprocess.run(
                ['afplay', '/System/Library/Sounds/Glass.aiff'],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info("🔔 Som de sucesso tocado!")
        except Exception:
            pass  # Ignora erro se o som não puder ser tocado
    
    def run(self) -> bool:
        """
        Executa o processo completo de importação.
        
        Returns:
            True se sucesso, False caso contrário
        """
        logger.info("")
        logger.info("╔" + "═" * 68 + "╗")
        logger.info("║" + " " * 10 + "🚀 MATCHFLY HISTORICAL IMPORTER - ANAC SIROS" + " " * 13 + "║")
        logger.info("╚" + "═" * 68 + "╝")
        logger.info("")
        logger.info(f"🎯 Configuração:")
        logger.info(f"   • Fonte:          SIROS (Registros Diários)")
        logger.info(f"   • Aeroporto:      {self.airport_code} (Guarulhos)")
        logger.info(f"   • Atraso mínimo:  {self.min_delay_minutes} minutos")
        logger.info(f"   • Período:        Últimos {self.days_lookback} dias")
        logger.info(f"   • Output:         {self.output_file}")
        logger.info("")
        
        try:
            # ============================================================
            # STEP 1: Carregar voos existentes
            # ============================================================
            logger.info("=" * 70)
            logger.info("STEP 1: CARREGANDO BANCO DE DADOS EXISTENTE")
            logger.info("=" * 70)
            self.load_existing_flights()
            
            # ============================================================
            # STEP 2: Obter URLs de download
            # ============================================================
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 2: IDENTIFICANDO ARQUIVOS DA ANAC")
            logger.info("=" * 70)
            urls = self.get_anac_download_urls()
            
            if not urls:
                logger.error("❌ Nenhuma URL de download identificada")
                return False
            
            # ============================================================
            # STEP 3: Download e processamento (arquivos diários)
            # ============================================================
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 3: DOWNLOAD E PROCESSAMENTO (ARQUIVOS DIÁRIOS)")
            logger.info("=" * 70)
            
            # Cria diretório temporário
            temp_dir = Path('temp_anac_data')
            temp_dir.mkdir(exist_ok=True)
            
            all_delayed_flights = []
            files_downloaded = 0
            files_processed = 0
            
            logger.info(f"📥 Iniciando download de {len(urls)} arquivos...")
            logger.info(f"⏱️  Rate limiting: 1.5s entre requisições")
            logger.info("")
            
            for idx, url in enumerate(urls, 1):
                # Nome do arquivo
                filename = url.split('/')[-1]
                temp_file = temp_dir / filename
                
                # Extrai data do nome do arquivo (registros_2025-05-01.csv)
                date_match = re.search(r'registros_(\d{4}-\d{2}-\d{2})\.csv', filename)
                flight_date = date_match.group(1) if date_match else None
                
                # Progress indicator a cada 5 arquivos
                if idx % 5 == 1:
                    logger.info(f"📊 Progresso: {idx}/{len(urls)} ({(idx/len(urls)*100):.1f}%)")
                
                # Download com tratamento de 404
                if self.download_csv(url, temp_file, add_delay=(idx > 1)):
                    files_downloaded += 1
                    
                    # Toca som de sucesso no PRIMEIRO arquivo baixado com sucesso
                    if files_downloaded == 1:
                        logger.info("")
                        logger.info("🎉" * 35)
                        logger.info("🎯 PRIMEIRO ARQUIVO BAIXADO COM SUCESSO!")
                        logger.info("🎉" * 35)
                        logger.info("")
                        self.play_success_sound()
                    
                    # Processa o arquivo
                    delayed_flights = self.process_csv_file(temp_file, flight_date)
                    all_delayed_flights.extend(delayed_flights)
                    files_processed += 1
                    
                    # Cleanup: remove arquivo após processar (economiza espaço)
                    try:
                        temp_file.unlink()
                    except:
                        pass
                else:
                    # Continua tentando o próximo dia
                    continue
            
            # Sumário do download
            logger.info("")
            logger.info("=" * 70)
            logger.info("📊 SUMÁRIO DO DOWNLOAD:")
            logger.info(f"   • Arquivos tentados:     {len(urls)}")
            logger.info(f"   • Arquivos baixados:     {files_downloaded}")
            logger.info(f"   • Arquivos processados:  {files_processed}")
            logger.info(f"   • Taxa de sucesso:       {(files_downloaded/len(urls)*100):.1f}%")
            logger.info("=" * 70)
            logger.info("")
            
            # Verifica se encontrou algum arquivo
            if files_downloaded == 0:
                logger.error("")
                logger.error("❌" * 35)
                logger.error("❌ ERRO: Nenhum arquivo ANAC/SIROS encontrado!")
                logger.error("❌ Os últimos 30 dias testados não estão disponíveis.")
                logger.error("❌ Verifique:")
                logger.error("❌   1. Conexão com internet")
                logger.error("❌   2. URL do servidor SIROS")
                logger.error("❌   3. Disponibilidade dos dados na ANAC")
                logger.error("❌" * 35)
                return False
            
            # ============================================================
            # STEP 4: Mesclar com banco existente
            # ============================================================
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 4: MESCLANDO COM BANCO DE DADOS")
            logger.info("=" * 70)
            
            if all_delayed_flights:
                imported = self.merge_flights(all_delayed_flights)
                self.stats['imported'] = imported
            else:
                logger.warning("⚠️  Nenhum voo atrasado encontrado para importar")
            
            # ============================================================
            # STEP 5: Cleanup
            # ============================================================
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 5: LIMPEZA")
            logger.info("=" * 70)
            self.cleanup_temp_files(temp_dir)
            
            # ============================================================
            # STEP 6: Sumário final
            # ============================================================
            self.print_summary()
            
            if self.stats['imported'] > 0:
                logger.info("")
                logger.info("🎉" * 35)
                logger.info("🎉 SUCESSO TOTAL! Dados históricos importados com sucesso!")
                logger.info("🎉" * 35)
                logger.info("")
                logger.info("🚀 Próximo passo: Execute python src/generator.py para gerar as páginas HTML.")
                logger.info("")
                return True
            elif self.stats['delayed_flights'] > 0:
                logger.info("ℹ️  Voos atrasados encontrados, mas todos já estavam no banco de dados (duplicatas)")
                return True
            else:
                logger.warning("⚠️  Nenhum dado novo foi importado")
                return False
                
        except KeyboardInterrupt:
            logger.warning("\n⚠️  Importação interrompida pelo usuário")
            return False
        except Exception as e:
            logger.error(f"\n❌ Erro fatal na importação: {e}", exc_info=True)
            return False


def main():
    """Função principal."""
    
    # Cria importador
    importer = ANACHistoricalImporter(
        output_file="data/flights-db.json",
        airport_code="SBGR",  # Guarulhos
        min_delay_minutes=15,
        days_lookback=30
    )
    
    # Executa importação
    success = importer.run()
    
    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
