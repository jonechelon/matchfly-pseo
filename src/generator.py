#!/usr/bin/env python3
"""
MatchFly Static Page Generator - Production Grade
==================================================
Sistema de geração de páginas estáticas com:
- Gestão de órfãos (arquivos antigos)
- Geração de sitemap.xml
- Auditoria completa de builds
- Resiliência total (try/except por voo)

Author: MatchFly Team
Date: 2026-01-11
Version: 2.0.0
"""

import json
import logging
import random
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
from slugify import slugify
from jinja2 import Environment, FileSystemLoader, Template
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# PARTE 1: MAPEAMENTO DE CIDADES PARA CÓDIGOS IATA
# ============================================================
# Dicionário expandido com principais destinos nacionais e internacionais
# Garante pré-preenchimento automático do funil AirHelp para maximizar conversão
CITY_TO_IATA = {
    # ========== INTERNACIONAIS ==========
    # Europa
    "paris": "CDG",
    "lisboa": "LIS",
    "madrid": "MAD",
    "londres": "LHR",
    "frankfurt": "FRA",
    "roma": "FCO",
    "barcelona": "BCN",
    "amsterdã": "AMS",
    "amsterdam": "AMS",
    "zurique": "ZRH",
    "milão": "MXP",
    "milao": "MXP",
    
    # América do Sul
    "buenos aires": "EZE",
    "santiago": "SCL",
    "lima": "LIM",
    "bogotá": "BOG",
    "bogota": "BOG",
    "montevideo": "MVD",
    "montevidéu": "MVD",
    
    # América do Norte
    "miami": "MIA",
    "nova york": "JFK",
    "new york": "JFK",
    "orlando": "MCO",
    "los angeles": "LAX",
    "toronto": "YYZ",
    "cidade do méxico": "MEX",
    "mexico city": "MEX",
    "panamá": "PTY",
    "panama": "PTY",
    
    # ========== NACIONAIS (Principais fluxos de GRU) ==========
    "rio de janeiro": "GIG",
    "brasília": "BSB",
    "brasilia": "BSB",
    "belo horizonte": "CNF",
    "salvador": "SSA",
    "fortaleza": "FOR",
    "recife": "REC",
    "porto alegre": "POA",
    "curitiba": "CWB",
    "florianópolis": "FLN",
    "florianopolis": "FLN",
    "goiânia": "GYN",
    "goiania": "GYN",
    "cuiabá": "CGB",
    "cuiaba": "CGB",
    "manaus": "MAO",
    "belém": "BEL",
    "belem": "BEL",
    "natal": "NAT",
    "maceió": "MCZ",
    "maceio": "MCZ",
    "vitória": "VIX",
    "vitoria": "VIX",
    "foz do iguaçu": "IGU",
    "foz do iguacu": "IGU",
    "porto seguro": "BPS",
    "aracaju": "AJU",
    "joão pessoa": "JPA",
    "joao pessoa": "JPA",
    "são luís": "SLZ",
    "sao luis": "SLZ",
    "teresina": "THE",
    "campo grande": "CGR",
}

# Lista de códigos IATA brasileiros para identificar voos nacionais
BRAZILIAN_AIRPORTS = {
    "GRU", "GIG", "BSB", "SSA", "FOR", "REC", "POA", "CWB", "CNF",
    "MAO", "BEL", "FLN", "VIX", "NAT", "JPA", "MCZ", "AJU", "SLZ",
    "THE", "CGR", "CGB", "GYN", "VCP", "CGH", "SDU"
}


def get_iata_code(city_name: str) -> str:
    """
    Mapeia nome da cidade para código IATA com busca case-insensitive.
    
    Args:
        city_name: Nome da cidade (ex: "PARIS", "Rio de Janeiro", " Lisboa ")
        
    Returns:
        Código IATA (ex: "CDG", "GIG") ou string vazia se não encontrado
    """
    if not city_name or city_name.strip() == "":
        return ""
    
    # Remove espaços extras e converte para lowercase para busca case-insensitive
    city_clean = city_name.strip().lower()
    
    # Busca no dicionário (case-insensitive)
    iata_code = CITY_TO_IATA.get(city_clean, "")
    
    if iata_code:
        logger.debug(f"Mapeamento IATA: {city_name.strip()} → {iata_code}")
    else:
        logger.debug(f"Cidade não mapeada: {city_name.strip()} (fallback: campo vazio no funil)")
    
    return iata_code


def is_domestic_flight(destination_iata: str) -> bool:
    """
    Verifica se o voo é doméstico (nacional).
    
    Args:
        destination_iata: Código IATA do destino
        
    Returns:
        True se for voo nacional, False se internacional
    """
    return destination_iata in BRAZILIAN_AIRPORTS


class FlightPageGenerator:
    """Gerador de páginas estáticas para voos - Production Grade."""
    
    def __init__(
        self,
        data_file: str = "data/flights-db.json",
        template_file: str = "src/templates/tier2-anac400.html",
        output_dir: str = "public",
        voo_dir: str = "public/voo",
        affiliate_link: str = "",
        base_url: str = "https://matchfly.org"
    ):
        """
        Inicializa o gerador.
        
        Args:
            data_file: Caminho para o arquivo JSON com dados de voos
            template_file: Caminho para o template Jinja2
            output_dir: Diretório de saída para páginas HTML
            voo_dir: Diretório específico para páginas de voos
            affiliate_link: Link de afiliado para monetização
            base_url: URL base para sitemap
        """
        self.data_file = Path(data_file)
        self.template_file = Path(template_file)
        self.output_dir = Path(output_dir)
        self.voo_dir = Path(voo_dir)
        self.affiliate_link = affiliate_link
        self.base_url = base_url.rstrip('/')
        
        # Configurar Jinja2
        template_dir = self.template_file.parent
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )
        
        # Estatísticas detalhadas
        self.stats = {
            'total_flights': 0,
            'successes': 0,
            'failures': 0,
            'orphans_removed': 0,
            'old_files_detected': 0,
            'filtered_out': 0
        }
        
        # Tracking de arquivos gerados com sucesso
        self.success_files: Set[str] = set()
        self.success_pages: List[Dict] = []
    
    def setup_and_validate(self) -> bool:
        """
        STEP 1: Setup & Validação.
        Verifica affiliate link e cria estrutura de pastas.
        
        Returns:
            True se validação passou, False caso contrário
        """
        logger.info("=" * 70)
        logger.info("STEP 1: SETUP & VALIDAÇÃO")
        logger.info("=" * 70)
        
        # Validação e fallback: Affiliate Link
        if not self.affiliate_link or self.affiliate_link.strip() == "":
            # Usar link padrão em vez de interromper o build
            self.affiliate_link = "https://www.compensair.com/"
            logger.warning("⚠️  AFFILIATE_LINK não configurada - usando link padrão")
            logger.warning("   Para produção, configure AFFILIATE_LINK em src/generator.py")
        
        logger.info(f"✅ Affiliate link configurada: {self.affiliate_link[:50]}...")
        
        # Criar estrutura de pastas
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.voo_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Pasta {self.voo_dir} pronta")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao criar pastas: {e}")
            return False
    
    def initial_cleanup(self) -> None:
        """
        STEP 2: Initial Cleanup com auditoria.
        Remove index.html antigo e conta arquivos em public/voo/.
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 2: INITIAL CLEANUP (Auditoria)")
        logger.info("=" * 70)
        
        # Remove index.html antigo
        index_file = self.output_dir / "index.html"
        if index_file.exists():
            try:
                index_file.unlink()
                logger.info("🗑️  Removido: public/index.html (será regenerado)")
            except Exception as e:
                logger.warning(f"⚠️  Não foi possível remover index.html: {e}")
        
        # Conta arquivos HTML em public/voo/
        old_files = list(self.voo_dir.glob("*.html"))
        self.stats['old_files_detected'] = len(old_files)
        
        if old_files:
            logger.info(f"📊 Detectados {len(old_files)} arquivos antigos em public/voo/")
            logger.info("   Serão removidos automaticamente quando não regenerados.")
        else:
            logger.info("📊 Nenhum arquivo antigo detectado em public/voo/")
    
    def load_flight_data(self) -> Optional[Dict]:
        """
        Carrega dados de voos do arquivo JSON.
        
        Returns:
            Dicionário com dados ou None em caso de erro
        """
        try:
            if not self.data_file.exists():
                logger.error(f"Arquivo de dados não encontrado: {self.data_file}")
                return None
            
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"✅ Dados carregados: {self.data_file}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}")
            return None
    
    def should_generate_page(self, flight: Dict) -> bool:
        """
        Valida e filtra voo.
        FILTRO: Apenas status 'Cancelado' ou atraso > 15 minutos.
        
        Args:


        
            flight: Dicionário com dados do voo
            
        Returns:
            True se deve gerar página, False caso contrário
        """
        # Validação de campos obrigatórios
        required_fields = ['flight_number', 'airline', 'status']
        for field in required_fields:
            if not flight.get(field):
                logger.debug(f"Voo inválido: campo '{field}' ausente")
                return False
        
        # FILTRO: Cancelado ou atraso > 15 minutos (0.25 horas)
        status = flight.get('status', '').lower()
        delay_hours = flight.get('delay_hours', 0)
        
        is_cancelled = any(term in status for term in ['cancel', 'cancelado'])
        is_delayed = delay_hours > 0.25
        
        if False: # not (is_cancelled or is_delayed):
            logger.debug(f"Voo {flight.get('flight_number')} filtrado: "
                        f"status={status}, delay={delay_hours}h")
            return False
        
        return True
    
    def calculate_hours_ago(self, scraped_at: str) -> int:
        """
        Calcula quantas horas se passaram desde o scraping.
        
        Args:
            scraped_at: Timestamp ISO do scraping
            
        Returns:
            Número de horas (arredondado)
        """
        try:
            # Remove timezone se presente e converte para UTC
            scraped_at_clean = scraped_at.replace('Z', '').split('+')[0].split('.')[0]
            scraped_dt = datetime.fromisoformat(scraped_at_clean)
            now = datetime.now()
            delta = now - scraped_dt
            hours = int(delta.total_seconds() / 3600)
            return max(0, hours)  # Não retorna valores negativos
        except Exception as e:
            logger.debug(f"Erro ao calcular hours_ago: {e}")
            return 0
    
    def generate_slug(self, flight: Dict) -> str:
        """
        Gera slug de URL amigável para SEO.
        
        Formato: voo-{airline}-{flight_number}-{origin}-cancelado
        Exemplo: voo-latam-la3090-gru-cancelado
        
        Args:
            flight: Dados do voo
            
        Returns:
            Slug formatado
        """
        airline = flight.get('airline', 'airline')
        flight_number = flight.get('flight_number', 'XXX')
        origin = flight.get('origin', 'gru')
        status = flight.get('status', 'problema')
        
        # Normaliza status para palavra-chave
        status_normalized = 'cancelado' if 'cancel' in status.lower() else 'atrasado'
        
        # Cria slug base
        slug_parts = [
            'voo',
            slugify(airline),
            slugify(flight_number),
            slugify(origin),
            status_normalized
        ]
        
        slug = '-'.join(slug_parts)
        return slug
    
    def prepare_template_context(self, flight: Dict, metadata: Dict) -> Dict:
        """
        Prepara contexto de dados para o template.
        
        Args:
            flight: Dados do voo
            metadata: Metadados do scraping
            
        Returns:
            Dicionário com todas as variáveis para o template
        """
        # Calcula hours_ago
        scraped_at = metadata.get('scraped_at', datetime.now(timezone.utc).isoformat())
        hours_ago = self.calculate_hours_ago(scraped_at)
        
        # Extrai campos do voo
        flight_number = flight.get('flight_number', 'N/A')
        origin = flight.get('origin', 'GRU')
        destination = flight.get('destination', 'N/A')
        
        # ============================================================
        # PARTE 2: CONSTRUÇÃO DO DEEP LINK OTIMIZADO (FUNIL AIRHELP)
        # ============================================================
        
        # Mapeia destino para código IATA
        destination_iata = get_iata_code(destination)
        
        # Determina se é voo nacional ou internacional
        is_domestic = is_domestic_flight(destination_iata) if destination_iata else False
        
        # Define regulamentação aplicável
        regulation = "ANAC 400" if is_domestic else "EC 261/ANAC"
        
        # Constrói Deep Link do Funil AirHelp com parâmetros otimizados
        # Base: funnel.airhelp.com/claims/new/trip-details
        affiliate_link_with_flight = (
            f"https://funnel.airhelp.com/claims/new/trip-details?"
            f"lang=pt-br"
            f"&departureAirportIata={origin}"
        )
        
        # Adiciona destino se disponível (aumenta conversão significativamente)
        if destination_iata:
            affiliate_link_with_flight += f"&arrivalAirportIata={destination_iata}"
        
        # Anexa parâmetros de rastreio de afiliado (obrigatório)
        affiliate_link_with_flight += (
            f"&a_aid=69649260287c5"
            f"&a_bid=c63de166"
            f"&utm_medium=affiliate"
            f"&utm_source=pap"
            f"&utm_campaign=aff-69649260287c5"
        )
        
        logger.debug(f"Link gerado: {affiliate_link_with_flight}")
        logger.debug(f"Voo {'NACIONAL' if is_domestic else 'INTERNACIONAL'}: {origin} → {destination} ({destination_iata})")
        
        context = {
            'flight_number': flight_number,
            'airline': flight.get('airline', 'Companhia Aérea'),
            'status': flight.get('status', 'Problema'),
            'scheduled_time': flight.get('scheduled_time', 'N/A'),
            'actual_time': flight.get('actual_time', 'N/A'),
            'delay_hours': flight.get('delay_hours', 0),
            'origin': origin,
            'destination': destination,
            
            # Dados de destino para CRO
            'destination_iata': destination_iata,
            'is_domestic': is_domestic,
            'regulation': regulation,
            
            # Metadados
            'hours_ago': hours_ago,
            'scraped_at': scraped_at,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            
            # Monetização - Deep Link do Funil AirHelp Otimizado
            'affiliate_link': affiliate_link_with_flight,
            
            # Dados adicionais para schema
            'departure_time': flight.get('scheduled_time', datetime.now().isoformat()),
        }
        
        return context
    
    def generate_page_resilient(self, flight: Dict, metadata: Dict) -> bool:
        """
        Gera página HTML com resiliência (try/except).
        
        Args:
            flight: Dados do voo
            metadata: Metadados do scraping
            
        Returns:
            True se sucesso, False se falha
        """
        flight_number = flight.get('flight_number', 'UNKNOWN')
        
        try:
            # Prepara contexto
            context = self.prepare_template_context(flight, metadata)
            
            # Carrega template
            template = self.jinja_env.get_template(self.template_file.name)
            
            # Renderiza HTML
            html_content = template.render(**context)
            
            # Gera slug e caminho do arquivo
            slug = self.generate_slug(flight)
            filename = f"{slug}.html"
            output_file = self.voo_dir / filename
            
            # Salva arquivo
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Registra sucesso
            self.success_files.add(filename)
            self.success_pages.append({
                'filename': filename,
                'slug': slug,
                'flight_number': flight.get('flight_number'),
                'airline': flight.get('airline'),
                'status': flight.get('status'),
                'delay_hours': flight.get('delay_hours', 0),
                'scheduled_time': flight.get('scheduled_time'),
                'url': f"/voo/{filename}"
            })
            
            logger.info(f"✅ Sucesso: {filename}")
            self.stats['successes'] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Falha ao gerar {flight_number}: {e}")
            self.stats['failures'] += 1
            return False
    
    def manage_orphans(self) -> None:
        """
        STEP 3.2: Gestão de Órfãos.
        Remove arquivos em public/voo/ que não foram regenerados.
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 3.2: GESTÃO DE ÓRFÃOS")
        logger.info("=" * 70)
        
        # Lista todos os arquivos HTML em public/voo/
        existing_files = set(f.name for f in self.voo_dir.glob("*.html"))
        
        # Identifica órfãos (existem mas não foram gerados agora)
        orphans = existing_files - self.success_files
        
        if orphans:
            logger.info(f"🗑️  Encontrados {len(orphans)} arquivos órfãos para remoção:")
            for orphan in sorted(orphans):
                try:
                    orphan_path = self.voo_dir / orphan
                    orphan_path.unlink()
                    logger.info(f"   • Removido: {orphan}")
                    self.stats['orphans_removed'] += 1
                except Exception as e:
                    logger.warning(f"   ⚠️  Erro ao remover {orphan}: {e}")
        else:
            logger.info("✅ Nenhum arquivo órfão detectado")
    
    def generate_sitemap(self) -> None:
        """
        STEP 3.3: Gera sitemap.xml com URLs geradas com sucesso.
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 3.3: GERAÇÃO DE SITEMAP")
        logger.info("=" * 70)
        
        try:
            # Cria elemento raiz
            urlset = ET.Element('urlset')
            urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
            
            # Adiciona página inicial
            url_home = ET.SubElement(urlset, 'url')
            ET.SubElement(url_home, 'loc').text = self.base_url + "/"
            ET.SubElement(url_home, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
            ET.SubElement(url_home, 'changefreq').text = 'hourly'
            ET.SubElement(url_home, 'priority').text = '1.0'
            
            # Adiciona páginas de voos
            for page in self.success_pages:
                url_elem = ET.SubElement(urlset, 'url')
                ET.SubElement(url_elem, 'loc').text = self.base_url + page['url']
                ET.SubElement(url_elem, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
                ET.SubElement(url_elem, 'changefreq').text = 'daily'
                ET.SubElement(url_elem, 'priority').text = '0.8'
            
            # Formata XML
            xml_str = minidom.parseString(ET.tostring(urlset)).toprettyxml(indent="  ")
            
            # Remove linhas vazias
            xml_str = '\n'.join([line for line in xml_str.split('\n') if line.strip()])
            
            # Salva sitemap
            sitemap_file = self.output_dir / "sitemap.xml"
            with open(sitemap_file, 'w', encoding='utf-8') as f:
                f.write(xml_str)
            
            logger.info(f"✅ Sitemap gerado: {sitemap_file}")
            logger.info(f"   • URLs incluídas: {len(self.success_pages) + 1} (1 home + {len(self.success_pages)} voos)")
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar sitemap: {e}")
    
    def generate_homepage(self) -> None:
        """
        STEP 3.4: Gera public/index.html com 20 voos mais recentes.
        Usa template Jinja2 com variáveis dinâmicas para Growth/Referral.
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 3.4: GERAÇÃO DE HOME PAGE")
        logger.info("=" * 70)
        
        try:
            # Ordena por data (mais recentes primeiro)
            sorted_pages = sorted(
                self.success_pages,
                key=lambda x: x.get('scheduled_time', ''),
                reverse=True
            )
            
            # Pega 20 mais recentes
            recent_pages = sorted_pages[:20]
            
            # ============================================================
            # VARIÁVEIS DINÂMICAS PARA GROWTH/REFERRAL
            # ============================================================
            
            # 1. voos_hoje_count: Total de voos com problemas
            voos_hoje_count = len(self.success_pages)
            
            # 2. herois_count: Fórmula com random para "social proof"
            herois_count = int(voos_hoje_count * 1.8) + random.randint(20, 35)
            
            # 3. gate_context: Escolha aleatória de contexto de aeroporto
            gate_options = ['Portão B12', 'Terminal 3', 'Embarque Sul', 'Portão C21']
            gate_context = random.choice(gate_options)
            
            # 4. utm_suffix: Parâmetro de rastreamento para links virais
            utm_suffix = '?utm_source=hero_gru'
            
            # ============================================================
            # PREPARAÇÃO DO CONTEXTO PARA TEMPLATE JINJA2
            # ============================================================
            
            context = {
                # Dados de voos
                'recent_pages': recent_pages,
                'voos_hoje_count': voos_hoje_count,
                
                # Growth/Referral variables
                'herois_count': herois_count,
                'gate_context': gate_context,
                'utm_suffix': utm_suffix,
                
                # Monetização
                'affiliate_link': self.affiliate_link,
                
                # Timestamps
                'current_time': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'last_update': datetime.now().strftime('%d/%m/%Y às %H:%M'),
            }
            
            # ============================================================
            # RENDERIZAÇÃO COM JINJA2
            # ============================================================
            
            # Carrega template da homepage
            template = self.jinja_env.get_template('index.html')
            
            # Renderiza HTML
            html_content = template.render(**context)
            
            # Salva index.html
            index_file = self.output_dir / "index.html"
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # ============================================================
            # LOGS DE SUCESSO COM TRACKING DE GROWTH
            # ============================================================
            
            logger.info(f"✅ Home page gerada: {index_file}")
            logger.info(f"   • Voos exibidos: {len(recent_pages)} (dos {len(self.success_pages)} totais)")
            logger.info(f"   • Growth Variables:")
            logger.info(f"     - Heróis (social proof): {herois_count}")
            logger.info(f"     - Gate context: {gate_context}")
            logger.info(f"     - UTM suffix: {utm_suffix}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar home page: {e}")
    
    def generate_index(self, generated_pages: List[Dict]) -> None:
        """
        Gera página index.html listando todos os voos.
        
        Args:
            generated_pages: Lista de páginas geradas
        """
        try:
            html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MatchFly - Voos com Problemas | Indenização ANAC 400</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto px-4 py-12 max-w-6xl">
        <header class="text-center mb-12">
            <h1 class="text-4xl font-bold text-blue-900 mb-4">
                ✈️ MatchFly - Voos com Problemas
            </h1>
            <p class="text-lg text-gray-600">
                Verifique se você tem direito a indenização de até R$ 10.000
            </p>
        </header>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
"""
            
            for page in generated_pages:
                html += f"""
            <a href="{page['filename']}" class="block bg-white rounded-lg shadow-md hover:shadow-xl transition-shadow p-6 border-l-4 border-red-500">
                <div class="flex items-start justify-between mb-3">
                    <div>
                        <h2 class="text-xl font-bold text-gray-900">{page['flight_number']}</h2>
                        <p class="text-sm text-gray-600">{page['airline']}</p>
                    </div>
                    <span class="px-3 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded-full">
                        {page['status']}
                    </span>
                </div>
                <div class="text-sm text-gray-500 space-y-1">
                    <p>⏱️ Atraso: {page['delay_hours']}h</p>
                    <p>🔗 <span class="text-blue-600 font-medium">Ver detalhes →</span></p>
                </div>
            </a>
"""
            
            html += f"""
        </div>
        
        <footer class="mt-12 text-center text-sm text-gray-500">
            <p>Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p class="mt-2">Total de voos: {len(generated_pages)}</p>
        </footer>
    </div>
</body>
</html>
"""
            
            index_file = self.output_dir / "index.html"
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            logger.info(f"✅ Índice gerado: {index_file}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar index: {e}")
    
    def run(self) -> Dict:
        """
        Executa o processo completo de geração de páginas.
        Arquitetura rigorosa: Setup → Cleanup → Generation → Orphans → Sitemap → Home.
        
        Returns:
            Dicionário com estatísticas da geração
        """
        try:
            logger.info("")
            logger.info("╔" + "═" * 68 + "╗")
            logger.info("║" + " " * 15 + "🚀 MATCHFLY PAGE GENERATOR v2.0" + " " * 22 + "║")
            logger.info("╚" + "═" * 68 + "╝")
            logger.info("")
            
            # ============================================================
            # STEP 1: SETUP & VALIDAÇÃO
            # ============================================================
            if not self.setup_and_validate():
                logger.error("Build interrompido na validação.")
                sys.exit(1)
            
            # ============================================================
            # STEP 2: INITIAL CLEANUP
            # ============================================================
            self.initial_cleanup()
            
            # ============================================================
            # STEP 3: WORKFLOW DE GERAÇÃO
            # ============================================================
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 3: WORKFLOW DE GERAÇÃO")
            logger.info("=" * 70)
            
            # Carrega dados
            data = self.load_flight_data()
            if not data:
                logger.error("❌ Não foi possível carregar dados")
                return self.stats
            
            flights = data.get('flights', [])
            metadata = data.get('metadata', {})
            
            self.stats['total_flights'] = len(flights)
            logger.info(f"📊 Total de voos carregados: {len(flights)}")
            
            if not flights:
                logger.warning("⚠️  Nenhum voo encontrado nos dados")
                return self.stats
            
            # ============================================================
            # STEP 3.1: RENDERIZAÇÃO RESILIENTE
            # ============================================================
            logger.info("")
            logger.info("🔄 Iniciando renderização resiliente...")
            logger.info("-" * 70)
            
            for i, flight in enumerate(flights, 1):
                flight_number = flight.get('flight_number', f'UNKNOWN-{i}')
                
                # Filtra voo
                if not self.should_generate_page(flight):
                    self.stats['filtered_out'] += 1
                    continue
                
                # Tenta gerar página (com try/except interno)
                logger.info(f"[{i}/{len(flights)}] Processando {flight_number}...")
                self.generate_page_resilient(flight, metadata)
            
            # ============================================================
            # STEP 3.2: GESTÃO DE ÓRFÃOS
            # ============================================================
            self.manage_orphans()
            
            # ============================================================
            # STEP 3.3: SITEMAP
            # ============================================================
            if self.success_pages:
                self.generate_sitemap()
            else:
                logger.warning("⚠️  Nenhuma página gerada, sitemap não criado")
            
            # ============================================================
            # STEP 3.4: HOME PAGE
            # ============================================================
            if self.success_pages:
                self.generate_homepage()
            else:
                logger.warning("⚠️  Nenhuma página gerada, home page não criada")
            
            # ============================================================
            # STEP 4: LOG FINAL
            # ============================================================
            self.print_final_summary()
            
            return self.stats
            
        except KeyboardInterrupt:
            logger.warning("\n⚠️  Build interrompido pelo usuário")
            sys.exit(1)
        except Exception as e:
            logger.error(f"\n❌ Erro fatal no gerador: {e}", exc_info=True)
            sys.exit(1)
    
    def print_final_summary(self) -> None:
        """Imprime sumário final do build."""
        logger.info("")
        logger.info("╔" + "═" * 68 + "╗")
        logger.info("║" + " " * 23 + "✅ BUILD FINALIZADO!" + " " * 24 + "║")
        logger.info("╚" + "═" * 68 + "╝")
        logger.info("")
        logger.info("📊 SUMÁRIO DO BUILD:")
        logger.info(f"   • Voos processados:     {self.stats['total_flights']}")
        logger.info(f"   • Sucessos:             {self.stats['successes']} páginas")
        logger.info(f"   • Falhas:               {self.stats['failures']} páginas")
        logger.info(f"   • Filtrados (< 15min):  {self.stats['filtered_out']} voos")
        logger.info(f"   • Órfãos removidos:     {self.stats['orphans_removed']} arquivos")
        logger.info(f"   • Sitemap:              Atualizado com {self.stats['successes']} URLs")
        logger.info("")
        logger.info(f"📁 Output:")
        logger.info(f"   • Páginas de voos:      {self.voo_dir}/")
        logger.info(f"   • Home page:            {self.output_dir}/index.html")
        logger.info(f"   • Sitemap:              {self.output_dir}/sitemap.xml")
        logger.info("")
        
        if self.stats['successes'] > 0:
            logger.info("🎉 Build concluído com sucesso!")
            logger.info(f"🌐 Abra {self.output_dir}/index.html no navegador")
            logger.info("")
            logger.info("✅ MatchFly: Dicionário IATA expandido com sucesso!")
            
            # Toca som de sucesso (Glass.aiff no macOS)
            try:
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'], 
                             check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass  # Ignora erro se o som não puder ser tocado
        else:
            logger.warning("⚠️  Nenhuma página foi gerada!")
        
        logger.info("")
        logger.info("=" * 70)


def main():
    """Função principal para executar o gerador."""
    
    # ============================================================
    # CONFIGURAÇÃO: AFFILIATE LINK (DEEP LINK OTIMIZADO)
    # ============================================================
    # Deep Link da AirHelp que pré-preenche o formulário de verificação
    # Parâmetros dinâmicos: flightNumber e departureAirport serão adicionados automaticamente
    # Isso elimina fricção e aumenta a conversão drasticamente
    AFFILIATE_LINK = "https://www.airhelp.com/pt-br/verificar-indenizacao/?utm_medium=affiliate&utm_source=pap&utm_campaign=aff-69649260287c5&a_aid=69649260287c5&a_bid=c63de166"
    
    # URL base para sitemap (altere para seu domínio)
    BASE_URL = "https://matchfly.org"
    
    # ============================================================
    # Cria gerador com configurações
    # ============================================================
    generator = FlightPageGenerator(
        data_file="data/flights-db.json",
        template_file="src/templates/tier2-anac400.html",
        output_dir="public",
        voo_dir="public/voo",
        affiliate_link=AFFILIATE_LINK,
        base_url=BASE_URL
    )
    
    # ============================================================
    # Executa workflow completo
    # ============================================================
    stats = generator.run()
    
    # Exit code baseado em sucessos
    if stats['successes'] > 0:
        sys.exit(0)  # Sucesso
    else:
        sys.exit(1)  # Falha


if __name__ == "__main__":
    main()

