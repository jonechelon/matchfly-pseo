#!/usr/bin/env python3
"""
Google Indexing API Integration - MatchFly PSEO
===============================================
Script automatizado para enviar URLs recém-geradas para a Google Indexing API.

Funcionalidades:
- Lê sitemap.xml gerado pelo generator.py
- Autentica usando Service Account JSON
- Envia requisições URL_UPDATED para cada URL de voo
- Implementa rate limiting (respeita cotas da API)
- Tratamento robusto de erros
- Logging detalhado

Author: MatchFly Team
Date: 2026-01-22
Version: 1.0.0
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional
import xml.etree.ElementTree as ET

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    import requests
except ImportError as e:
    print(f"❌ Erro: Dependências não instaladas. Execute: pip install google-auth google-auth-oauthlib google-auth-httplib2 requests")
    sys.exit(1)

# Diretório do projeto para logs
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_DIR.mkdir(exist_ok=True)

# Configuração de logging (logs em logs/indexer.log)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_LOG_DIR / 'indexer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GoogleIndexingClient:
    """
    Cliente para Google Indexing API com autenticação via Service Account.
    """
    
    # Endpoint da Google Indexing API
    INDEXING_API_URL = "https://indexing.googleapis.com/v3/urlNotifications:publish"
    
    # Rate limiting: máximo de requisições por lote e delay entre requisições
    MAX_REQUESTS_PER_BATCH = 100
    DELAY_BETWEEN_REQUESTS = 0.1  # 100ms entre requisições
    DELAY_BETWEEN_BATCHES = 1.0   # 1 segundo entre lotes
    
    def __init__(self, credentials_path: str = "credentials/service_account.json"):
        """
        Inicializa o cliente de indexação.
        
        Args:
            credentials_path: Caminho para o arquivo JSON da Service Account
        """
        self.credentials_path = Path(credentials_path)
        self.credentials = None
        self.access_token = None
        
    def check_credentials_file(self) -> bool:
        """
        Verifica se o arquivo de credenciais existe.
        
        Returns:
            True se o arquivo existe, False caso contrário
        """
        if not self.credentials_path.exists():
            logger.warning(f"⚠️  Arquivo de credenciais não encontrado: {self.credentials_path}")
            logger.warning("   O script continuará sem enviar URLs para a Google Indexing API.")
            logger.warning("   Para habilitar a indexação, adicione o arquivo JSON da Service Account.")
            return False
        return True
    
    def authenticate(self) -> bool:
        """
        Autentica usando Service Account e obtém access token.
        
        Returns:
            True se autenticação bem-sucedida, False caso contrário
        """
        if not self.check_credentials_file():
            return False
        
        try:
            logger.info(f"🔐 Autenticando com Service Account: {self.credentials_path}")
            
            # Carrega credenciais do arquivo JSON
            self.credentials = service_account.Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=['https://www.googleapis.com/auth/indexing']
            )
            
            # Obtém access token
            request = Request()
            self.credentials.refresh(request)
            self.access_token = self.credentials.token
            
            logger.info("✅ Autenticação bem-sucedida")
            return True
            
        except FileNotFoundError:
            logger.error(f"❌ Arquivo de credenciais não encontrado: {self.credentials_path}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao decodificar JSON de credenciais: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro na autenticação: {e}")
            return False
    
    def index_url(self, url: str, notification_type: str = "URL_UPDATED") -> bool:
        """
        Envia uma URL para a Google Indexing API.
        
        Args:
            url: URL completa a ser indexada
            notification_type: Tipo de notificação ("URL_UPDATED" ou "URL_DELETED")
            
        Returns:
            True se sucesso, False caso contrário
        """
        if not self.access_token:
            logger.error("❌ Access token não disponível. Execute authenticate() primeiro.")
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'url': url,
                'type': notification_type
            }
            
            response = requests.post(
                self.INDEXING_API_URL,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug(f"✅ URL indexada: {url}")
                return True
            elif response.status_code == 429:
                logger.warning(f"⚠️  Rate limit atingido para: {url}")
                logger.warning("   Aguardando antes de continuar...")
                time.sleep(5)  # Aguarda 5 segundos em caso de rate limit
                return False
            else:
                error_msg = response.text
                logger.error(f"❌ Erro ao indexar {url}: HTTP {response.status_code}")
                logger.error(f"   Resposta: {error_msg}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout ao indexar {url}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro de requisição ao indexar {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao indexar {url}: {e}")
            return False
    
    def index_urls_batch(self, urls: List[str], notification_type: str = "URL_UPDATED") -> dict:
        """
        Envia múltiplas URLs em lotes com rate limiting.
        
        Args:
            urls: Lista de URLs a serem indexadas
            notification_type: Tipo de notificação
            
        Returns:
            Dicionário com estatísticas: {'total': int, 'successes': int, 'failures': int}
        """
        if not urls:
            logger.warning("⚠️  Nenhuma URL fornecida para indexação")
            return {'total': 0, 'successes': 0, 'failures': 0}
        
        stats = {
            'total': len(urls),
            'successes': 0,
            'failures': 0
        }
        
        logger.info(f"📤 Iniciando indexação de {len(urls)} URLs...")
        logger.info(f"   Rate limiting: {self.DELAY_BETWEEN_REQUESTS}s entre requisições")
        logger.info(f"   Lotes de até {self.MAX_REQUESTS_PER_BATCH} URLs")
        
        # Processa URLs em lotes
        for batch_start in range(0, len(urls), self.MAX_REQUESTS_PER_BATCH):
            batch_end = min(batch_start + self.MAX_REQUESTS_PER_BATCH, len(urls))
            batch_urls = urls[batch_start:batch_end]
            batch_num = (batch_start // self.MAX_REQUESTS_PER_BATCH) + 1
            
            logger.info(f"")
            logger.info(f"📦 Lote {batch_num}: URLs {batch_start + 1} a {batch_end} de {len(urls)}")
            logger.info("-" * 70)
            
            for i, url in enumerate(batch_urls, 1):
                url_num = batch_start + i
                logger.info(f"[{url_num}/{len(urls)}] Indexando: {url}")
                
                success = self.index_url(url, notification_type)
                
                if success:
                    stats['successes'] += 1
                else:
                    stats['failures'] += 1
                
                # Delay entre requisições (exceto na última)
                if i < len(batch_urls):
                    time.sleep(self.DELAY_BETWEEN_REQUESTS)
            
            # Delay entre lotes (exceto no último lote)
            if batch_end < len(urls):
                logger.info(f"⏳ Aguardando {self.DELAY_BETWEEN_BATCHES}s antes do próximo lote...")
                time.sleep(self.DELAY_BETWEEN_BATCHES)
        
        return stats


def parse_sitemap(sitemap_path: str) -> List[str]:
    """
    Extrai URLs de voos do sitemap.xml.
    
    Filtra apenas URLs que contêm '/voo/' (páginas de voos),
    excluindo a página inicial.
    
    Args:
        sitemap_path: Caminho para o arquivo sitemap.xml
        
    Returns:
        Lista de URLs de voos
    """
    sitemap_file = Path(sitemap_path)
    
    if not sitemap_file.exists():
        logger.error(f"❌ Sitemap não encontrado: {sitemap_path}")
        return []
    
    try:
        logger.info(f"📖 Lendo sitemap: {sitemap_path}")
        tree = ET.parse(sitemap_file)
        root = tree.getroot()
        
        # Namespace do sitemap
        namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        urls = []
        for url_elem in root.findall('sitemap:url', namespace):
            loc_elem = url_elem.find('sitemap:loc', namespace)
            if loc_elem is not None:
                url = loc_elem.text.strip()
                # Filtra apenas URLs de voos (contém '/voo/')
                if '/voo/' in url:
                    urls.append(url)
        
        logger.info(f"✅ {len(urls)} URLs de voos extraídas do sitemap")
        return urls
        
    except ET.ParseError as e:
        logger.error(f"❌ Erro ao parsear sitemap XML: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Erro ao ler sitemap: {e}")
        return []


def main():
    """
    Função principal: lê sitemap, autentica e indexa URLs.
    """
    logger.info("")
    logger.info("╔" + "═" * 68 + "╗")
    logger.info("║" + " " * 15 + "🔍 GOOGLE INDEXING API - MatchFly" + " " * 18 + "║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info("")
    
    # ============================================================
    # CONFIGURAÇÃO
    # ============================================================
    SITEMAP_PATH = "public/sitemap.xml"
    CREDENTIALS_PATH = "credentials/service_account.json"
    
    # ============================================================
    # STEP 1: LER SITEMAP
    # ============================================================
    logger.info("=" * 70)
    logger.info("STEP 1: LEITURA DO SITEMAP")
    logger.info("=" * 70)
    
    urls = parse_sitemap(SITEMAP_PATH)
    
    if not urls:
        logger.warning("⚠️  Nenhuma URL de voo encontrada no sitemap.")
        logger.warning("   O script será finalizado sem enviar requisições.")
        sys.exit(0)  # Exit code 0 = sucesso (não é erro se não houver URLs)
    
    logger.info(f"📊 Total de URLs para indexar: {len(urls)}")
    
    # ============================================================
    # STEP 2: AUTENTICAÇÃO
    # ============================================================
    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP 2: AUTENTICAÇÃO")
    logger.info("=" * 70)
    
    client = GoogleIndexingClient(credentials_path=CREDENTIALS_PATH)
    
    if not client.authenticate():
        logger.warning("⚠️  Autenticação falhou ou credenciais não encontradas.")
        logger.warning("   O script será finalizado sem enviar requisições.")
        logger.warning("   Isso é normal se você ainda não configurou as credenciais.")
        sys.exit(0)  # Exit code 0 = sucesso (não quebra o pipeline)
    
    # ============================================================
    # STEP 3: INDEXAÇÃO
    # ============================================================
    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP 3: INDEXAÇÃO DE URLs")
    logger.info("=" * 70)
    
    stats = client.index_urls_batch(urls, notification_type="URL_UPDATED")
    
    # ============================================================
    # STEP 4: SUMÁRIO FINAL
    # ============================================================
    logger.info("")
    logger.info("╔" + "═" * 68 + "╗")
    logger.info("║" + " " * 23 + "✅ INDEXAÇÃO FINALIZADA!" + " " * 24 + "║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info("")
    logger.info("📊 SUMÁRIO:")
    logger.info(f"   • URLs processadas:  {stats['total']}")
    logger.info(f"   • Sucessos:          {stats['successes']}")
    logger.info(f"   • Falhas:            {stats['failures']}")
    logger.info("")
    
    if stats['successes'] > 0:
        logger.info("🎉 URLs enviadas com sucesso para a Google Indexing API!")
    elif stats['failures'] > 0:
        logger.warning("⚠️  Algumas URLs falharam. Verifique os logs acima.")
    
    logger.info("=" * 70)
    logger.info("")
    
    # Exit code baseado em sucessos
    if stats['successes'] > 0:
        sys.exit(0)  # Sucesso
    else:
        sys.exit(0)  # Ainda exit 0 para não quebrar pipeline se credenciais não estiverem configuradas


if __name__ == "__main__":
    main()
