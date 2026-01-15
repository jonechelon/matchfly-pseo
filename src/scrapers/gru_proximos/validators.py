"""
Módulo de validações e identificação de dados de voos.
Contém todas as regras de negócio para validação de voos, companhias e destinos.
"""
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .config import (
    PREFIX_TO_COMPANY, COMPANHIAS_CONHECIDAS, NON_CITY_WORDS,
    VALID_IATA_CODES, INVALID_IATA_CODES, AIRPORT_DICT
)


class FlightValidator:
    """Validações de dados de voos."""
    
    @staticmethod
    def is_valid_number(voo: str) -> bool:
        """
        Valida se o número do voo contém APENAS números (REGRA DE OURO).
        Aceita: 4138, 4838, 6719 (apenas números 3-4 dígitos)
        Rejeita: qualquer letra (ex: RJ6719, LA3598), textos longos, palavras como "YouTube", etc.
        """
        if not voo or voo == "N/A":
            return False
        
        voo_clean = voo.strip()
        
        # REGRA DE OURO: Voo deve conter APENAS números (sem letras)
        if not voo_clean.isdigit():
            return False
        
        # Aceita apenas números de 3-4 dígitos
        if re.match(r'^\d{3,4}$', voo_clean):
            return True
        
        # Rejeita qualquer outro padrão
        return False
    
    @staticmethod
    def is_valid_destination(destino: str) -> bool:
        """
        Valida se o destino não está na lista negra de textos inválidos (NON_CITY_WORDS).
        Rejeita: YouTube, Instagram, Facebook, Detalhes, Detalhe, Ver mais, CIA, SKY, etc.
        
        Validação de Siglas IATA:
        - Códigos de 3 letras são aceitos APENAS se estiverem em VALID_IATA_CODES
        - Rejeita códigos inválidos (CIA, SKY, etc)
        """
        if not destino or destino == "N/A":
            return False
        
        destino_upper = destino.strip().upper()
        destino_clean = destino.strip()
        
        # VALIDAÇÃO 1: Verifica lista negra rigorosa (NON_CITY_WORDS)
        if destino_upper in NON_CITY_WORDS:
            return False
        
        # VALIDAÇÃO 2: Verifica se contém alguma palavra da lista negra
        for invalid in NON_CITY_WORDS:
            if invalid in destino_upper:
                return False
        
        # VALIDAÇÃO 3: Verifica se não é companhia aérea conhecida
        if destino_upper in COMPANHIAS_CONHECIDAS:
            return False
        
        # VALIDAÇÃO 4: Validação de siglas IATA (3 letras)
        if len(destino_clean) == 3 and destino_upper.isalpha():
            # Se é código IATA inválido, rejeita
            if destino_upper in INVALID_IATA_CODES:
                return False
            # Se é código IATA válido, aceita
            if destino_upper in VALID_IATA_CODES:
                return True
            # Se não está em nenhuma lista, rejeita (não aceita códigos desconhecidos)
            return False
        
        # VALIDAÇÃO 5: Se destino < 3 caracteres, rejeita (exceto códigos IATA que já foram validados acima)
        if len(destino_clean) < 3:
            return False
        
        # VALIDAÇÃO 6: Se destino == Status (ex: "Embarque"), rejeita
        if destino_upper in ["EMBARQUE", "EMBARQUE PRÓXIMO", "EMBARQUE PROXIMO"]:
            return False
        
        return True
    
    @staticmethod
    def validate(flight_data: Dict[str, str]) -> bool:
        """
        Valida se os dados do voo são válidos antes de adicionar à lista.
        
        LÓGICA PERMISSIVA (pSEO): Aceita voo se tiver Número de Voo e Status válidos.
        Não rejeita por falta de destino ou companhia.
        
        Validações:
        1. Voo válido (padrão de código de voo ou números) - OBRIGATÓRIO
        2. Status válido - OBRIGATÓRIO
        3. Destino válido (se não for "N/A", deve estar na lista negra) - OPCIONAL
        4. Companhia pode ser "N/A" - OPCIONAL
        """
        if not flight_data:
            return False
        
        companhia = str(flight_data.get('Companhia', '')).strip()
        voo = str(flight_data.get('Voo', '')).strip()
        destino = str(flight_data.get('Destino', '')).strip()
        status = str(flight_data.get('Status', '')).strip()
        
        # VALIDAÇÃO 1: Voo válido (OBRIGATÓRIO)
        # CORREÇÃO: Aceita voo com prefixo (ex: A6509) ou apenas números (ex: 7586)
        # Remove prefixo se houver para validar apenas os números
        voo_clean = re.sub(r'^[A-Z]{1,3}', '', voo) if re.match(r'^[A-Z]{1,3}\d{3,4}$', voo) else voo
        if not FlightValidator.is_valid_number(voo_clean):
            return False
        
        # VALIDAÇÃO 2: Status válido (OBRIGATÓRIO)
        if not status or status == "N/A":
            return False
        
        # VALIDAÇÃO 3: Destino válido (OPCIONAL - só valida se não for "N/A")
        # Permite destino "N/A" quando não houver destino identificável
        if destino != "N/A" and not FlightValidator.is_valid_destination(destino):
            return False
        
        # VALIDAÇÃO 4: Separação rígida de colunas - Destino != Status
        destino_upper = destino.upper()
        status_upper = status.upper()
        if destino_upper == status_upper or destino_upper in ["EMBARQUE", "EMBARQUE PRÓXIMO", "EMBARQUE PROXIMO"]:
            return False
        
        # Companhia pode ser "N/A" - não rejeita por isso (lógica permissiva)
        
        return True
    
    @staticmethod
    def is_invalid_destination_for_dedup(destino: str) -> bool:
        """Verifica se destino está na lista negra (ex: Detalhes, YouTube, Embarque, etc)"""
        if not destino or destino == "N/A":
            return True
        destino_upper = destino.strip().upper()
        return destino_upper in NON_CITY_WORDS or destino_upper in INVALID_IATA_CODES


class CompanyIdentifier:
    """Identificação de companhias aéreas."""
    
    @staticmethod
    def from_prefix(voo_prefixo: str) -> Optional[str]:
        """
        Identifica companhia pelo prefixo do voo.
        
        Args:
            voo_prefixo: Prefixo do voo (ex: "TP", "LA", "AD")
        
        Returns:
            Nome da companhia ou None se não encontrar
        """
        if not voo_prefixo:
            return None
        return PREFIX_TO_COMPANY.get(voo_prefixo.upper())
    
    @staticmethod
    def from_src(src: str) -> str:
        """
        Identifica companhia aérea através de palavras-chave no src (URL) da imagem.
        
        Fallback quando alt/title estão vazios ou genéricos.
        
        Args:
            src: URL completa ou parcial da imagem
        
        Returns:
            Nome da companhia identificada ou string vazia
        """
        if not src:
            return ""
        
        src_lower = src.lower()
        
        # Mapeamento de padrões no src para companhias
        if "/ar" in src_lower or "aerolineas" in src_lower or "aerolineas-argentinas" in src_lower:
            return "AEROLINEAS ARGENTINAS"
        elif "/g3" in src_lower or "/gol" in src_lower or "-gol" in src_lower or "logo-gol" in src_lower:
            return "GOL"
        elif "/ad" in src_lower or "/azul" in src_lower or "-azul" in src_lower or "logo-azul" in src_lower:
            return "AZUL"
        elif "/la" in src_lower or "/latam" in src_lower or "-latam" in src_lower or "logo-latam" in src_lower or "/tam" in src_lower:
            return "LATAM"
        elif "/kl" in src_lower or "/klm" in src_lower or "-klm" in src_lower or "logo-klm" in src_lower:
            return "KLM"
        elif "/af" in src_lower or "/air-france" in src_lower or "-air-france" in src_lower or "logo-air-france" in src_lower:
            return "AIR FRANCE"
        elif "/ba" in src_lower or "/british" in src_lower or "-british" in src_lower or "logo-british" in src_lower:
            return "BRITISH AIRWAYS"
        elif "/ek" in src_lower or "/emirates" in src_lower or "-emirates" in src_lower:
            return "EMIRATES"
        elif "/tk" in src_lower or "/turkish" in src_lower or "-turkish" in src_lower:
            return "TURKISH AIRLINES"
        elif "/lh" in src_lower or "/lufthansa" in src_lower or "-lufthansa" in src_lower:
            return "LUFTHANSA"
        elif "/aa" in src_lower or "/american" in src_lower or "-american" in src_lower:
            return "AMERICAN AIRLINES"
        elif "/dl" in src_lower or "/delta" in src_lower or "-delta" in src_lower:
            return "DELTA"
        elif "/ua" in src_lower or "/united" in src_lower or "-united" in src_lower:
            return "UNITED"
        elif "/tp" in src_lower or "/tap" in src_lower or "-tap" in src_lower:
            return "TAP"
        elif "/co" in src_lower or "/copa" in src_lower or "-copa" in src_lower:
            return "COPA"
        elif "/av" in src_lower or "/avianca" in src_lower or "-avianca" in src_lower:
            return "AVIANCA"
        elif "/ib" in src_lower or "/iberia" in src_lower or "-iberia" in src_lower:
            return "IBERIA"
        elif "/qr" in src_lower or "/qatar" in src_lower or "-qatar" in src_lower:
            return "QATAR AIRWAYS"
        elif "/ey" in src_lower or "/etihad" in src_lower or "-etihad" in src_lower:
            return "ETIHAD"
        elif "/sq" in src_lower or "/singapore" in src_lower or "-singapore" in src_lower:
            return "SINGAPORE AIRLINES"
        
        return ""
    
    @staticmethod
    def map_name(text: str) -> str:
        """
        Mapeia texto (alt, title, src) para nome da companhia aérea.
        Suporta múltiplas formas de escrita e variações.
        """
        text_lower = text.lower()
        
        if "latam" in text_lower or "tam" in text_lower:
            return "LATAM"
        elif "gol" in text_lower:
            return "GOL"
        elif "azul" in text_lower:
            return "AZUL"
        elif "emirates" in text_lower:
            return "EMIRATES"
        elif "turkish" in text_lower:
            return "TURKISH AIRLINES"
        elif "british" in text_lower or "british airways" in text_lower:
            return "BRITISH AIRWAYS"
        elif "air france" in text_lower or "airfrance" in text_lower:
            return "AIR FRANCE"
        elif "klm" in text_lower:
            return "KLM"
        elif "lufthansa" in text_lower:
            return "LUFTHANSA"
        elif "american" in text_lower or "american airlines" in text_lower:
            return "AMERICAN AIRLINES"
        elif "delta" in text_lower:
            return "DELTA"
        elif "united" in text_lower or "united airlines" in text_lower:
            return "UNITED"
        elif "aerolineas" in text_lower or "aerolíneas" in text_lower or "aerolineas argentinas" in text_lower:
            return "AEROLINEAS ARGENTINAS"
        elif "tap" in text_lower or "tap air portugal" in text_lower:
            return "TAP"
        elif "air canada" in text_lower:
            return "AIR CANADA"
        elif "copa" in text_lower or "copa airlines" in text_lower:
            return "COPA"
        elif "avianca" in text_lower:
            return "AVIANCA"
        elif "iberia" in text_lower:
            return "IBERIA"
        elif "alitalia" in text_lower:
            return "ALITALIA"
        elif "swiss" in text_lower or "swiss air" in text_lower:
            return "SWISS"
        elif "qatar" in text_lower:
            return "QATAR AIRWAYS"
        elif "etihad" in text_lower:
            return "ETIHAD"
        elif "singapore" in text_lower:
            return "SINGAPORE AIRLINES"
        
        return ""
    
    @staticmethod
    def from_text(block_text: str, voo: str) -> str:
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
                    "RJ": "AZUL"
                }
                code = voo[:2].upper()
                return airline_codes.get(code, "N/A")
        except Exception:
            pass
        
        return "N/A"
    
    @staticmethod
    def from_image(block, voo: str = "", logger=None) -> str:
        """
        PRIORIDADE DE OPERADORA: Extrai companhia com priorização inteligente baseada em src e faixa numérica.
        
        IMPORTANTE: Usa block.query_selector_all para buscar APENAS dentro da linha atual (row-level),
        nunca usa seletores globais (page.query_selector).
        
        Args:
            block: Elemento do Playwright representando a linha do voo
            voo: Número do voo (ex: "3598", "1500") para priorização e debug
            logger: Logger opcional para substituir prints
        
        Returns:
            Nome da companhia aérea priorizada baseada nas regras
        """
        log = logger.info if logger else print
        log_error = logger.error if logger else print
        
        companies_data = {}
        all_srcs = []
        
        try:
            images = block.query_selector_all("img")
            
            if not images:
                log(f"   ⚠️ Voo {voo}: Nenhuma imagem encontrada na linha")
                return "N/A"
            
            log(f"   🔍 Voo {voo}: {len(images)} imagem(ns) detectada(s) na linha")
            
            for idx, img in enumerate(images):
                src = (img.get_attribute("src") or "").strip()
                alt = (img.get_attribute("alt") or "").strip()
                title = (img.get_attribute("title") or "").strip()
                
                if src:
                    all_srcs.append(src)
                
                # VERIFICAÇÃO POR NOME DE ARQUIVO (SRC) - PRIORIDADE MÁXIMA
                if src:
                    filename = src.split('/')[-1].split('?')[0].upper()
                    
                    if 'AR.PNG' in filename or filename.startswith('AR'):
                        company = "AEROLINEAS ARGENTINAS"
                        if company not in companies_data or companies_data[company]['priority'] > 1:
                            companies_data[company] = {'source': f'src-filename-{filename}', 'priority': 1}
                            log(f"      → Imagem {idx+1}: Companhia '{company}' identificada via SRC (AR.png): '{filename}'")
                    elif 'DL.PNG' in filename or filename.startswith('DL') or '/DL' in src.upper():
                        company = "DELTA"
                        if company not in companies_data or companies_data[company]['priority'] > 1:
                            companies_data[company] = {'source': f'src-filename-{filename}', 'priority': 1}
                            log(f"      → Imagem {idx+1}: Companhia '{company}' identificada via SRC (DL.png): '{filename}'")
                    elif ('LA.PNG' in filename or filename.startswith('LA') or '/LA' in src.upper() or 
                          'JJ.PNG' in filename or filename.startswith('JJ') or '/JJ' in src.upper()):
                        company = "LATAM"
                        if company not in companies_data or companies_data[company]['priority'] > 1:
                            companies_data[company] = {'source': f'src-filename-{filename}', 'priority': 1}
                            log(f"      → Imagem {idx+1}: Companhia '{company}' identificada via SRC (LA/JJ.png): '{filename}'")
                    elif 'G3.PNG' in filename or filename.startswith('G3') or '/G3' in src.upper():
                        company = "GOL"
                        if company not in companies_data or companies_data[company]['priority'] > 1:
                            companies_data[company] = {'source': f'src-filename-{filename}', 'priority': 1}
                            log(f"      → Imagem {idx+1}: Companhia '{company}' identificada via SRC (G3.png): '{filename}'")
                    
                    # Identifica pelo src usando palavras-chave (prioridade 2)
                    company_from_src = CompanyIdentifier.from_src(src)
                    if company_from_src:
                        if company_from_src not in companies_data or companies_data[company_from_src]['priority'] > 2:
                            companies_data[company_from_src] = {'source': f'src-keywords-{src[:50]}', 'priority': 2}
                            log(f"      → Imagem {idx+1}: Companhia '{company_from_src}' identificada via SRC (palavras-chave): '{src[:80]}...'")
                
                # PRIORIDADE 3: Atributo 'alt' da imagem
                if alt and alt.lower() not in ["", "logo", "imagem", "image", "icon", "ícone"]:
                    alt_clean = re.sub(r'\b(logo|imagem|image|icon|ícone)\b', '', alt.lower(), flags=re.IGNORECASE).strip()
                    if alt_clean:
                        company = CompanyIdentifier.map_name(alt_clean)
                        if company:
                            if company not in companies_data or companies_data[company]['priority'] > 3:
                                companies_data[company] = {'source': f'alt-{alt}', 'priority': 3}
                                log(f"      → Imagem {idx+1}: Companhia '{company}' identificada via ALT: '{alt}'")
                
                # PRIORIDADE 4: Atributo 'title' da imagem
                if title and title.lower() not in ["", "logo", "imagem", "image", "icon", "ícone"]:
                    title_clean = re.sub(r'\b(logo|imagem|image|icon|ícone)\b', '', title.lower(), flags=re.IGNORECASE).strip()
                    if title_clean:
                        company = CompanyIdentifier.map_name(title_clean)
                        if company:
                            if company not in companies_data or companies_data[company]['priority'] > 4:
                                companies_data[company] = {'source': f'title-{title}', 'priority': 4}
                                log(f"      → Imagem {idx+1}: Companhia '{company}' identificada via TITLE: '{title}'")
            
            if all_srcs:
                log(f"   📋 Voo {voo}: Imagens detectadas no HTML ({len(all_srcs)} src(s)):")
                for idx, src_item in enumerate(all_srcs[:3]):
                    log(f"      [{idx+1}] {src_item[:100]}...")
                if len(all_srcs) > 3:
                    log(f"      ... e mais {len(all_srcs) - 3} imagem(ns)")
            
            if companies_data:
                sorted_companies = sorted(companies_data.items(), key=lambda x: x[1]['priority'])
                companies_list = [company for company, data in sorted_companies]
                
                result = CompanyIdentifier.prioritize_by_number(voo, companies_list, logger)
                
                log(f"   ✅ Voo {voo}: Encontradas {len(companies_list)}: {', '.join(companies_list)}. Escolhida: {result} devido à faixa numérica")
                
                return result
            else:
                log(f"   ⚠️ Voo {voo}: Nenhuma companhia identificada após escaneamento profundo")
        
        except Exception as e:
            log_error(f"   ❌ Erro ao extrair companhia da imagem (Voo {voo}): {e}")
            if logger:
                import traceback
                logger.debug(traceback.format_exc())
        
        return "N/A"
    
    @staticmethod
    def prioritize_by_number(voo: str, companies_list: List[str] = None, logger=None) -> str:
        """
        MAPEAMENTO DE PREFIXO DE VOO (A REGRA DE OURO): Prioriza companhia baseado na faixa numérica do voo.
        
        Agora funciona mesmo sem lista de companhias (inferência direta por faixa numérica).
        
        Regras de Prioridade:
        - Voo 1000-2999: Prioriza Aerolineas Argentinas, KLM, Air France ou Delta
        - Voo 3000-4999 ou 8000+: Prioriza LATAM
        - Voo 6000-6999: Verifica GOL ou Delta
        - Voo 7000-7999: Prioriza LATAM (faixa comum em GRU)
        - Caso Especial Delta: Se Delta aparecer e for voo internacional (1000-2999 ou 8000+), prioriza Delta
        """
        log = logger.info if logger else print
        
        if companies_list is None:
            companies_list = []
        
        try:
            voo_num = int(voo)
        except (ValueError, TypeError):
            if companies_list:
                return companies_list[0] if len(companies_list) > 0 else "N/A"
            return "N/A"
        
        # INFERÊNCIA DIRETA: Se não há lista, inferir diretamente pela faixa numérica
        if not companies_list:
            # CORREÇÃO 2: Faixa da Avianca (200-299) - comum em GRU para voos regionais
            if 200 <= voo_num <= 299:
                log(f"      📊 Voo {voo} ({voo_num}): Inferindo AVIANCA por faixa numérica (200-299)")
                return "AVIANCA"
            
            # --- GOL LINHAS AÉREAS ---
            # Faixas comuns: 1000-1999, 6000-6999, 9000-9999
            if 1000 <= voo_num <= 1999:
                log(f"      📊 Voo {voo} ({voo_num}): Inferindo GOL por faixa numérica (1000-1999)")
                return "GOL"
            if 6000 <= voo_num <= 6999:
                log(f"      📊 Voo {voo} ({voo_num}): Inferindo GOL por faixa numérica (6000-6999)")
                return "GOL"
            if 9000 <= voo_num <= 9999:
                log(f"      📊 Voo {voo} ({voo_num}): Inferindo GOL por faixa numérica (9000-9999)")
                return "GOL"  # Voos extras/charter GOL ou Azul Conecta (Priorizar GOL se dúvida)
            
            # --- AZUL LINHAS AÉREAS ---
            # Faixas comuns: 2000-2999, 4000-5999, 8000-8899 (Evitar 89xx que pode ser Latam)
            if 2000 <= voo_num <= 2999:
                log(f"      📊 Voo {voo} ({voo_num}): Inferindo AZUL por faixa numérica (2000-2999)")
                return "AZUL"
            if 4000 <= voo_num <= 5999:
                log(f"      📊 Voo {voo} ({voo_num}): Inferindo AZUL por faixa numérica (4000-5999)")
                return "AZUL"  # Grande volume Azul em GRU
            if 8000 <= voo_num <= 8899:
                log(f"      📊 Voo {voo} ({voo_num}): Inferindo AZUL por faixa numérica (8000-8899)")
                return "AZUL"  # Cuidado com overlap Latam
            
            # --- LATAM (Reforço) ---
            if 3000 <= voo_num <= 4999:
                log(f"      📊 Voo {voo} ({voo_num}): Inferindo LATAM por faixa numérica (3000-4999)")
                return "LATAM"
            if 7000 <= voo_num <= 7999:
                log(f"      📊 Voo {voo} ({voo_num}): Inferindo LATAM por faixa numérica (7000-7999)")
                return "LATAM"
            if 8900 <= voo_num <= 8999:
                log(f"      📊 Voo {voo} ({voo_num}): Inferindo LATAM por faixa numérica (8900-8999)")
                return "LATAM"  # Internacionais específicos
            
            return "N/A"
        
        # Se há lista, usar lógica de priorização existente
        if len(companies_list) == 1:
            return companies_list[0]
        
        # REGRA 1: Voo 1000-2999 → Prioriza Aerolineas Argentinas, KLM, Air France ou Delta
        if 1000 <= voo_num <= 2999:
            priority_order = ["AEROLINEAS ARGENTINAS", "KLM", "AIR FRANCE", "DELTA"]
            for company in priority_order:
                if company in companies_list:
                    log(f"      📊 Voo {voo} (1000-2999): Priorizando {company} devido à faixa numérica")
                    return company
        
        # REGRA 2: Voo 3000-4999 → Prioriza LATAM
        if 3000 <= voo_num <= 4999:
            if "LATAM" in companies_list:
                log(f"      📊 Voo {voo} (3000-4999): Priorizando LATAM devido à faixa numérica")
                return "LATAM"
        
        # REGRA 3: Voo 6000-6999 → Verifica GOL ou Delta
        if 6000 <= voo_num <= 6999:
            if "GOL" in companies_list:
                log(f"      📊 Voo {voo} (6000-6999): Priorizando GOL devido à faixa numérica")
                return "GOL"
            elif "DELTA" in companies_list:
                log(f"      📊 Voo {voo} (6000-6999): Priorizando DELTA devido à faixa numérica")
                return "DELTA"
        
        # REGRA 4: Voo 8000+ → Prioriza LATAM (internacionais longa distância)
        if voo_num >= 8000:
            if "LATAM" in companies_list:
                log(f"      📊 Voo {voo} (8000+): Priorizando LATAM (internacional longa distância)")
                return "LATAM"
            elif "KLM" in companies_list:
                log(f"      📊 Voo {voo} (8000+): Priorizando KLM (internacional longa distância)")
                return "KLM"
            elif "AIR FRANCE" in companies_list:
                log(f"      📊 Voo {voo} (8000+): Priorizando AIR FRANCE (internacional longa distância)")
                return "AIR FRANCE"
            elif "BRITISH AIRWAYS" in companies_list:
                log(f"      📊 Voo {voo} (8000+): Priorizando BRITISH AIRWAYS (internacional longa distância)")
                return "BRITISH AIRWAYS"
        
        # CASO ESPECIAL DELTA: Se Delta aparecer em voos internacionais, prioriza
        if "DELTA" in companies_list:
            if (1000 <= voo_num <= 2999) or (voo_num >= 8000):
                log(f"      📊 Voo {voo} (internacional): Priorizando DELTA (caso especial)")
                return "DELTA"
        
        log(f"      📊 Voo {voo}: Nenhuma regra de faixa aplicada, usando primeira da lista: {companies_list[0]}")
        return companies_list[0]
    
    @staticmethod
    def choose_main(companies_list: List[str], destino: str, voo: str, voo_prefixo: str = "", logger=None) -> str:
        """
        Escolhe a companhia principal baseada nas regras de prioridade.
        
        NOVA HIERARQUIA:
        - Prioridade 1 (MÁXIMA): Prefixo do voo (TP, LA, AD, etc.) - O "Dono" do voo
        - Prioridade 2: Se destino é Brasil, escolhe entre LATAM, GOL, AZUL (só se não houver prefixo)
        - Prioridade 3: Regra de faixa numérica do voo (só se não houver prefixo)
        """
        log = logger.info if logger else print
        
        if not companies_list:
            return "N/A"
        
        if len(companies_list) == 1:
            return companies_list[0]
        
        # PRIORIDADE 1 (MÁXIMA): Prefixo do voo - O "Dono" do voo
        if voo_prefixo:
            company_by_prefix = CompanyIdentifier.from_prefix(voo_prefixo)
            if company_by_prefix:
                log(f"      🎯 Companhia definida pelo prefixo {voo_prefixo}: {company_by_prefix} (prioridade máxima)")
                return company_by_prefix
        
        # PRIORIDADE 2: Se destino é doméstico E não há prefixo, prioriza brasileiras
        if DestinationExtractor.is_domestic(destino):
            brazilian_companies = ["LATAM", "GOL", "AZUL"]
            for company in companies_list:
                if company in brazilian_companies:
                    log(f"      📍 Companhia definida por regra doméstica: {company}")
                    return company
        
        # PRIORIDADE 3: Para internacionais ou sem brasileira, usa regra de faixa numérica
        return CompanyIdentifier.prioritize_by_number(voo, companies_list, logger)


class DestinationExtractor:
    """Extração e validação de destinos."""
    
    @staticmethod
    def extract(block, block_text: str, logger=None) -> str:
        """
        Extrai destino PRIORIZANDO get_attribute('title') antes de inner_text().
        No site de GRU, o nome completo da cidade (ex: João Pessoa) geralmente está no atributo title.
        
        TRAVA DE INTEGRIDADE: Garante que o destino extraído pertence estritamente ao block fornecido.
        Todos os seletores usam block.query_selector_all (nunca seletores globais).
        """
        log = logger.info if logger else print
        log_error = logger.error if logger else print
        
        try:
            if not block_text or len(block_text) < 10:
                return "N/A"
            
            # ESTRATÉGIA 1: PRIORIDADE ABSOLUTA - Buscar em atributo 'title' de links <a> ou <span>
            try:
                title_elements = block.query_selector_all("a[title], span[title], [title]")
                for elem in title_elements:
                    title_text = (elem.get_attribute("title") or "").strip()
                    if title_text and len(title_text) >= 2:
                        title_clean = title_text.strip()
                        if FlightValidator.is_valid_destination(title_clean):
                            title_upper = title_clean.upper()
                            block_text_upper = block_text.upper()
                            
                            if title_upper in block_text_upper:
                                if len(title_clean) == 3 and title_clean.upper() in VALID_IATA_CODES:
                                    return title_clean.upper()
                                return title_clean
                            else:
                                palavras_title = title_upper.split()
                                encontrou_palavra = any(palavra in block_text_upper for palavra in palavras_title if len(palavra) > 3)
                                if encontrou_palavra:
                                    if len(title_clean) == 3 and title_clean.upper() in VALID_IATA_CODES:
                                        return title_clean.upper()
                                    return title_clean
            except Exception:
                pass
            
            # ESTRATÉGIA 2: Buscar em classes específicas
            try:
                specific_selectors = [
                    "[class*='city']",
                    "[class*='destination']",
                    "[class*='airport-name']",
                    "[class*='airport_name']",
                    ".city",
                    ".destination",
                    ".airport-name"
                ]
                for selector in specific_selectors:
                    try:
                        elements = block.query_selector_all(selector)
                        for elem in elements:
                            title_text = (elem.get_attribute("title") or "").strip()
                            if title_text and len(title_text) >= 2:
                                title_clean = title_text.strip()
                                if FlightValidator.is_valid_destination(title_clean):
                                    if len(title_clean) == 3 and title_clean.upper() in VALID_IATA_CODES:
                                        return title_clean.upper()
                                    return title_clean
                            elem_text = elem.inner_text().strip()
                            if elem_text and len(elem_text) >= 2:
                                elem_clean = elem_text.strip()
                                if FlightValidator.is_valid_destination(elem_clean):
                                    if len(elem_clean) == 3 and elem_clean.upper() in VALID_IATA_CODES:
                                        return elem_clean.upper()
                                    return elem_clean
                    except Exception:
                        continue
            except Exception:
                pass
            
            # ESTRATÉGIA 3: Buscar em elementos com classe 'hidden-mobile'
            try:
                hidden_mobile_elements = block.query_selector_all(".hidden-mobile, [class*='hidden-mobile'], [class*='hidden_mobile']")
                for elem in hidden_mobile_elements:
                    title_text = (elem.get_attribute("title") or "").strip()
                    if title_text and len(title_text) >= 2:
                        title_clean = title_text.strip()
                        if FlightValidator.is_valid_destination(title_clean):
                            if len(title_clean) == 3 and title_clean.upper() in VALID_IATA_CODES:
                                return title_clean.upper()
                            return title_clean
                    elem_text = elem.inner_text().strip()
                    if elem_text and len(elem_text) >= 2:
                        elem_clean = elem_text.strip()
                        if FlightValidator.is_valid_destination(elem_clean):
                            if len(elem_clean) == 3 and elem_clean.upper() in VALID_IATA_CODES:
                                return elem_clean.upper()
                            return elem_clean
            except Exception:
                pass
            
            # ESTRATÉGIA 4: Buscar códigos IATA no texto (APENAS códigos válidos)
            airport_codes = re.findall(r'\b([A-Z]{3})\b', block_text)
            for code in airport_codes:
                if code in INVALID_IATA_CODES:
                    continue
                if code == "GRU":
                    continue
                if code in COMPANHIAS_CONHECIDAS:
                    continue
                if code in VALID_IATA_CODES:
                    if code in block_text.upper():
                        return code
            
            # ESTRATÉGIA 5: Buscar nomes completos de cidades
            city_phrases = [
                r'\bRio\s+de\s+Janeiro\b',
                r'\bBelo\s+Horizonte\b',
                r'\bPorto\s+Alegre\b',
                r'\bSão\s+Paulo\b',
                r'\bSao\s+Paulo\b',
            ]
            for pattern in city_phrases:
                match = re.search(pattern, block_text, re.IGNORECASE)
                if match:
                    city_full = match.group(0)
                    city_mapping = {
                        "Rio de Janeiro": "GIG",
                        "Rio De Janeiro": "GIG",
                        "Belo Horizonte": "CNF",
                        "Porto Alegre": "POA",
                        "São Paulo": "CGH",
                        "Sao Paulo": "CGH",
                    }
                    if city_full in city_mapping:
                        return city_mapping[city_full]
                    city_full_clean = city_full.strip()
                    if FlightValidator.is_valid_destination(city_full_clean):
                        return city_full_clean
            
            # ESTRATÉGIA 6: Fallback - buscar nomes de cidades
            cities = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', block_text)
            full_city_names = {
                "Salvador": "SSA",
                "Fortaleza": "FOR",
                "Manaus": "MAO",
                "Recife": "REC",
                "Brasília": "BSB",
                "Brasilia": "BSB",
                "Curitiba": "CWB",
                "Florianópolis": "FLN",
                "Florianopolis": "FLN",
                "Belém": "BEL",
                "Belem": "BEL",
            }
            for city in cities:
                city_clean = city.strip()
                if city_clean in ["Rio", "Belo", "Porto", "São", "Sao"]:
                    continue
                city_upper = city_clean.upper()
                if city_upper not in COMPANHIAS_CONHECIDAS and not any(comp.upper() in city_upper for comp in COMPANHIAS_CONHECIDAS):
                    if city_clean in full_city_names:
                        return full_city_names[city_clean]
                    elif len(city_clean) > 4:
                        if FlightValidator.is_valid_destination(city_clean):
                            return city_clean
        
        except Exception as e:
            log_error(f"   ⚠️  Erro ao extrair destino: {e}")
            if logger:
                import traceback
                logger.debug(traceback.format_exc())
        
        return "N/A"
    
    @staticmethod
    def translate(destino: str) -> str:
        """
        Traduz sigla IATA ou nome cortado para nome completo usando AIRPORT_DICT.
        
        Exemplos:
        - SSA -> Salvador
        - Pessoa -> João Pessoa
        - CNF -> Belo Horizonte
        """
        if not destino or destino == "N/A":
            return destino
        
        destino_clean = destino.strip()
        destino_upper = destino_clean.upper()
        
        # Se é sigla IATA (3 letras), traduz
        if len(destino_clean) == 3 and destino_upper in AIRPORT_DICT:
            return AIRPORT_DICT[destino_upper]
        
        # Se é nome cortado conhecido (ex: "Pessoa"), traduz
        if destino_clean in AIRPORT_DICT:
            return AIRPORT_DICT[destino_clean]
        
        # Retorna original se não encontrou tradução
        return destino_clean
    
    @staticmethod
    def is_domestic(destino: str) -> bool:
        """
        Verifica se o destino é no Brasil (doméstico).
        
        Args:
            destino: Nome do destino (ex: "Belo Horizonte", "Miami")
        
        Returns:
            True se for destino doméstico, False caso contrário
        """
        if not destino or destino == "N/A":
            return False
        
        destino_upper = destino.upper()
        
        domestic_cities = {
            'SALVADOR', 'FORTALEZA', 'BELO HORIZONTE', 'PORTO ALEGRE', 'RECIFE',
            'CURITIBA', 'BRASÍLIA', 'RIO DE JANEIRO', 'MANAUS', 'NATAL', 'MACEIÓ',
            'VITÓRIA', 'FLORIANÓPOLIS', 'BELÉM', 'SÃO LUÍS', 'CUIABÁ', 'CAMPO GRANDE',
            'GOIÂNIA', 'PALMAS', 'ARACAJU', 'TERESINA', 'PORTO VELHO', 'BOA VISTA',
            'MACAPÁ', 'RIO BRANCO', 'JOÃO PESSOA', 'PETROLINA', 'ILHÉUS', 'PORTO SEGURO',
            'LONDRINA', 'MARINGÁ', 'NAVEGANTES', 'CHAPECÓ', 'RIBEIRÃO PRETO',
            'SÃO JOSÉ DO RIO PRETO', 'IMPERATRIZ', 'UBERLÂNDIA'
        }
        
        for city in domestic_cities:
            if city in destino_upper:
                return True
        
        if 'RIO DE JANEIRO' in destino_upper or ('RIO' in destino_upper and 'JANEIRO' in destino_upper):
            return True
        
        return False


def calculate_delay_alerts(horario_previsto: str, horario_estimado: str = "N/A") -> tuple:
    """
    Calcula alertas de atraso (1H e 2H).
    
    Returns:
        (alerta_1h, alerta_2h, atraso_minutos)
    """
    try:
        if horario_previsto == "N/A" or not horario_previsto:
            return "NÃO", "NÃO", 0
        
        hora, minuto = map(int, horario_previsto.split(':'))
        previsto = datetime.now().replace(hour=hora, minute=minuto, second=0, microsecond=0)
        
        if horario_estimado != "N/A" and horario_estimado:
            try:
                hora_est, min_est = map(int, horario_estimado.split(':'))
                estimado = datetime.now().replace(hour=hora_est, minute=min_est, second=0, microsecond=0)
                
                if estimado < previsto:
                    estimado = estimado + timedelta(days=1)
                
                atraso_minutos = (estimado - previsto).total_seconds() / 60
            except Exception:
                agora = datetime.now()
                if previsto > agora + timedelta(hours=12):
                    previsto = previsto - timedelta(days=1)
                elif previsto < agora - timedelta(hours=12):
                    previsto = previsto + timedelta(days=1)
                atraso_minutos = (agora - previsto).total_seconds() / 60
        else:
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
