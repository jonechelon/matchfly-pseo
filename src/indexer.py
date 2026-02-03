import os
import json
import logging
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração da API Google
SCOPES = ["https://www.googleapis.com/auth/indexing"]
ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"


def get_credentials():
    """Carrega credenciais do arquivo local ou variável de ambiente."""
    # 1. Tenta carregar de arquivo local (dev)
    if os.path.exists("credentials/service_account.json"):
        return service_account.Credentials.from_service_account_file(
            "credentials/service_account.json",
            scopes=SCOPES
        )

    # 2. Tenta carregar de variável de ambiente (GitHub Actions)
    if "GOOGLE_INDEXING_JSON" in os.environ:
        try:
            info = json.loads(os.environ["GOOGLE_INDEXING_JSON"])
            return service_account.Credentials.from_service_account_info(
                info,
                scopes=SCOPES
            )
        except json.JSONDecodeError:
            logger.error("❌ Erro ao decodificar JSON da variável de ambiente.")
            return None

    return None


def index_urls(urls: list):
    """Envia uma lista de URLs para a Google Indexing API."""
    creds = get_credentials()
    if not creds:
        logger.warning("⚠️ Nenhuma credencial do Google encontrada. Pulando indexação.")
        return

    try:
        # Atualiza token de autenticação
        creds.refresh(Request())

        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {creds.token}"})

        for url in urls:
            try:
                content = {
                    "url": url,
                    "type": "URL_UPDATED"
                }

                # Envia POST request
                response = session.post(ENDPOINT, json=content)

                if response.status_code == 200:
                    logger.info(f"✅ Indexado com sucesso: {url}")
                else:
                    logger.error(
                        f"❌ Erro ao indexar {url}: "
                        f"{response.status_code} - {response.text}"
                    )
            except Exception as e:
                logger.error(f"❌ Falha de conexão ao enviar {url}: {e}")

    except Exception as e:
        logger.error(f"❌ Erro geral na autenticação ou sessão: {e}")


if __name__ == "__main__":
    # Teste isolado: apenas valida se as credenciais carregam
    creds = get_credentials()
    if creds:
        logger.info("🔐 Credenciais do Google carregadas com sucesso.")
    else:
        logger.warning("⚠️ Credenciais não configuradas ou não encontradas.")
