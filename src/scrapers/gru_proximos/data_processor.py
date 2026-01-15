"""
Módulo de processamento de dados de voos.
Implementa Isolamento Atômico de Linha e processamento em memória.
"""
import csv
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging

try:
    import pandas as pd
except ImportError:
    pd = None

from .config import (
    CSV_COLUMNS, CSV_ENCODING, CSV_FILE_NAME_TEMPLATE, LOG_DIR, DISCARD_LOG_PATH, LOG_ENCODING,
    COMPANHIAS_CONHECIDAS, NON_CITY_WORDS, INVALID_IATA_CODES, AIRPORT_DICT
)
from .validators import (
    FlightValidator, CompanyIdentifier, DestinationExtractor, calculate_delay_alerts
)

# Importação opcional do MCPDiagnostics (pode não estar disponível)
try:
    from .mcp_diagnostics import MCPDiagnostics
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPDiagnostics = None


class FlightDataProcessor:
    """Processador de dados de voos com Isolamento Atômico."""
    
    def __init__(self, logger: Optional[logging.Logger] = None, enable_mcp: bool = True, target_statuses: Optional[List[str]] = None):
        """
        Inicializa o processador.
        
        Args:
            logger: Logger opcional para substituir prints
            enable_mcp: Se True, habilita diagnóstico MCP (padrão: True)
            target_statuses: Lista de status alvo (sobrescreve STATUS_ALVO do config)
        """
        self.logger = logger
        self.log = logger.info if logger else print
        self.log_error = logger.error if logger else print
        self.log_debug = logger.debug if logger else print
        
        if pd is None:
            raise ImportError("pandas não está instalado. Execute: pip install pandas")
        
        # Configuração de status alvo (dinâmica)
        from .config import STATUS_ALVO
        self.target_statuses = target_statuses if target_statuses else STATUS_ALVO
        
        # Inicializa MCPDiagnostics se disponível
        self.mcp_diagnostics = None
        if enable_mcp and MCP_AVAILABLE and MCPDiagnostics:
            try:
                self.mcp_diagnostics = MCPDiagnostics(logger=logger)
                self.log_debug("MCP Diagnostics habilitado")
            except Exception as e:
                self.log_error(f"Erro ao inicializar MCP Diagnostics: {e}")
                self.mcp_diagnostics = None
    
    def _log_discard(self, row_text: str, reason: str) -> None:
        """
        Registra descarte em arquivo separado para análise posterior.
        
        Formato: TIMESTAMP|REASON|ROW_TEXT
        """
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp}|{reason}|{row_text[:500]}\n"
        
        try:
            with open(DISCARD_LOG_PATH, 'a', encoding=LOG_ENCODING) as f:
                f.write(log_entry)
        except Exception as e:
            self.log_error(f"Erro ao registrar descarte: {e}")
    
    def create_csv_filename(self, output_dir: Optional[str] = None, csv_prefix: Optional[str] = None) -> str:
        """
        Cria nome do arquivo CSV com timestamp.
        
        Args:
            output_dir: Diretório de saída (sobrescreve LOG_DIR do config)
            csv_prefix: Prefixo do arquivo CSV (sobrescreve CSV_FILE_NAME_TEMPLATE)
        
        Returns:
            Caminho completo do arquivo CSV com timestamp
        """
        from .config import LOG_DIR, CSV_FILE_NAME_TEMPLATE
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Usa configurações dinâmicas se fornecidas, senão usa do config
        if csv_prefix:
            csv_filename = f"{csv_prefix}_{timestamp}.csv"
        else:
            csv_filename = CSV_FILE_NAME_TEMPLATE.format(timestamp)
        
        output_directory = output_dir if output_dir else LOG_DIR
        csv_file_path = os.path.join(output_directory, csv_filename)
        
        # Garante que o diretório existe
        os.makedirs(output_directory, exist_ok=True)
        
        return csv_file_path
    
    def find_containers(self, page) -> List:
        """
        Identifica containers de voos dentro da área da tabela de voos (limita busca).
        Busca apenas dentro do corpo principal da lista de voos (flights-table ou similar).
        """
        flight_blocks = []
        
        self.log("   🔍 Buscando containers de voos dentro da área da tabela...")
        
        try:
            # ESTRATÉGIA 0: Limita busca à área da tabela de voos (se existir)
            table_container = None
            table_selectors = [
                "[class*='flight']",
                "[class*='voos']",
                "[class*='table']",
                "[id*='flight']",
                "[id*='voos']",
                "[id*='table']",
                "main",
                "section",
                ".container"
            ]
            
            for selector in table_selectors:
                try:
                    container = page.query_selector(selector)
                    if container:
                        test_elements = container.query_selector_all(":has-text('Detalhes'), :has-text(':')")
                        if len(test_elements) > 5:
                            table_container = container
                            self.log(f"   ✅ Área da tabela identificada: {selector}")
                            break
                except Exception:
                    continue
            
            search_scope = table_container if table_container else page
            
            # ESTRATÉGIA 1: Busca por texto "Detalhes" dentro do escopo
            detalhes_elements = search_scope.query_selector_all(":has-text('Detalhes')")
            
            if detalhes_elements and len(detalhes_elements) > 0:
                self.log(f"   ✅ Encontrados {len(detalhes_elements)} elemento(s) com 'Detalhes'")
                flight_blocks = list(detalhes_elements)
            else:
                # ESTRATÉGIA 2: Busca por formato de hora dentro do escopo
                self.log("   📋 Buscando por formato de hora (XX:XX) dentro do escopo...")
                all_divs = search_scope.query_selector_all("div")
                
                for div in all_divs:
                    try:
                        text = div.inner_text().strip()
                        if re.search(r'\b\d{1,2}:\d{2}\b', text) and 15 < len(text) < 500:
                            flight_blocks.append(div)
                    except Exception:
                        continue
                
                if flight_blocks:
                    self.log(f"   ✅ Encontrados {len(flight_blocks)} elemento(s) com formato de hora")
                else:
                    error_msg = "❌ ERRO CRÍTICO: Não foi possível mapear a lista de voos."
                    self.log_error(error_msg)
        
        except Exception as e:
            error_msg = f"❌ Erro na busca de containers: {e}"
            self.log_error(error_msg)
        
        return flight_blocks
    
    def extract_from_snapshot(self, page) -> List[Dict[str, str]]:
        """
        Extrai todos os voos da página com status "Embarque Próximo" ou "Imediato Embarque" (flexível).
        
        ESTRATÉGIA: Captura em Memória (Snapshot) com Validações Rigorosas
        - Captura todos os dados brutos em lista (snapshot)
        - Valida rigorosamente: Companhia != "N/A", Voo válido, Destino válido
        - Sincronização horizontal: Garante que todos os dados vêm do mesmo elemento pai
        - Status flexível: Aceita variações de ordem
        
        MANTÉM: Isolamento Atômico de Linha (row_text = block.inner_text())
        """
        all_flights_raw = []
        
        flight_blocks = self.find_containers(page)
        
        if not flight_blocks:
            return all_flights_raw
        
        self.log(f"   📸 Criando snapshot do DOM (captura todos os elementos de uma vez)...")
        self.log(f"   📋 Capturados {len(flight_blocks)} container(s) no snapshot")
        self.log("   💾 Acumulando dados em memória (extraindo texto de todos os elementos)...")
        
        # ETAPA 1: ACÚMULO - ISOLAMENTO ATÔMICO: Captura apenas texto puro (snapshot)
        row_texts = []
        for block in flight_blocks:
            try:
                # SNAPSHOT DE TEXTO PURO: PRIMEIRA e ÚNICA interação com o navegador
                row_text = block.inner_text()
                
                if row_text and len(row_text.strip()) > 10:
                    row_texts.append(row_text.strip())
            except Exception:
                continue
        
        self.log(f"   ✅ {len(row_texts)} linha(s) capturada(s) no snapshot (isolamento atômico)")
        self.log("   🔄 Processando voos únicos com validações rigorosas (processamento em memória)...\n")
        
        # ETAPA 2: PROCESSAMENTO EM MEMÓRIA - NÃO interage mais com o navegador
        seen_flights = set()
        invalid_count = 0
        descartados = 0
        
        for row_text in row_texts:
            try:
                # PROCESSAMENTO EM MEMÓRIA: Extrai dados apenas da string row_text
                flight_data = self.extract_from_text(row_text)
                
                # ==========================================================
                # VALIDAÇÃO FINAL (Permissiva para pSEO)
                # ==========================================================
                # Se o data_processor retornou algo, nós CONFIAMOS nele.
                # Ele já filtrou o que era lixo. O que chegou aqui é ouro.
                
                if flight_data:
                    # Verificação básica de integridade apenas
                    if flight_data.get('Voo') and flight_data.get('Status'):
                        # Usa Horario se Horario_Previsto não estiver disponível
                        horario_previsto = flight_data.get('Horario_Previsto') or flight_data.get('Horario', '').strip()
                        voo = flight_data.get('Voo', '').strip()
                        
                        if not voo or not horario_previsto:
                            self.log_debug(f"      🗑️  Voo incompleto removido no Engine: {flight_data}")
                            descartados += 1
                            continue
                        
                        unique_key = f"{voo}|{horario_previsto}"
                        
                        if unique_key in seen_flights:
                            continue
                        
                        seen_flights.add(unique_key)
                        all_flights_raw.append(flight_data)
                    else:
                        self.log_debug(f"      🗑️  Voo incompleto removido no Engine: {flight_data}")
                        descartados += 1
                else:
                    descartados += 1
            
            except Exception as e:
                self.log_debug(f"      ❌ Erro ao processar linha: {e}")
                invalid_count += 1
                continue
        
        duplicates_removed = len(row_texts) - len(all_flights_raw) - invalid_count - descartados
        if duplicates_removed > 0:
            self.log(f"   ✅ {duplicates_removed} duplicata(s) removida(s) (site reativo)")
        if invalid_count > 0:
            self.log(f"   🗑️  {invalid_count} voo(s) com erro de processamento")
        if descartados > 0:
            self.log(f"   🗑️  {descartados} voo(s) descartado(s) (sem voo ou status)")
        
        self.log(f"   ✅ {len(all_flights_raw)} voo(s) válido(s) processado(s)")
        
        return all_flights_raw
    
    def _clean_text(self, text: str) -> str:
        """Limpeza profunda do texto."""
        # Remove todas as quebras de linha, tabulações e espaços múltiplos
        text = ' '.join(text.split())
        return text.strip()
    
    def _has_valid_status(self, text: str) -> Optional[str]:
        """
        Valida se o texto contém status relevante.
        
        Usa self.target_statuses (configurável dinamicamente) para buscar status.
        
        Returns:
            Status identificado ou None se não encontrar
        """
        text_lower = text.lower()
        
        # Busca por status na lista de target_statuses (dinâmica)
        for status in self.target_statuses:
            # Busca flexível: aceita variações de maiúsculas/minúsculas e acentos
            status_lower = status.lower()
            
            # Busca exata ou parcial (para casos como "Cancelado/Procure Cia.")
            if status_lower in text_lower:
                self.log_debug(f"      ✅ Status identificado: '{status}'")
                return status
        
        # Fallback para lógica antiga (compatibilidade)
        tem_embarque = "embarque" in text_lower
        tem_proximo = "próximo" in text_lower or "proximo" in text_lower
        tem_imediato = "imediato" in text_lower
        tem_ultima_chamada = ("última chamada" in text_lower or "ultima chamada" in text_lower or 
                              "chamada última" in text_lower or "chamada ultima" in text_lower)
        tem_encerrado = "voo encerrado" in text_lower or "encerrado" in text_lower
        tem_confirmado = "confirmado" in text_lower
        tem_cancelado = "cancelado" in text_lower
        
        if tem_ultima_chamada:
            self.log_debug(f"      ✅ Status identificado: 'Última Chamada' (palavras encontradas, ordem flexível)")
            return "Última Chamada"
        elif tem_embarque and tem_proximo:
            self.log_debug(f"      ✅ Status identificado: 'Embarque Próximo' (palavras encontradas, ordem flexível)")
            return "Embarque Próximo"
        elif tem_embarque and tem_imediato:
            self.log_debug(f"      ✅ Status identificado: 'Imediato Embarque' (palavras encontradas, ordem flexível)")
            return "Imediato Embarque"
        elif tem_imediato:
            self.log_debug(f"      ✅ Status identificado: 'Imediato Embarque' (apenas 'Imediato' encontrado)")
            return "Imediato Embarque"
        elif tem_encerrado:
            self.log_debug(f"      ✅ Status identificado: 'Voo encerrado'")
            return "Voo encerrado"
        elif tem_confirmado:
            self.log_debug(f"      ✅ Status identificado: 'Confirmado'")
            return "Confirmado"
        elif tem_cancelado:
            self.log_debug(f"      ✅ Status identificado: 'Cancelado' (CORREÇÃO 3)")
            return "Cancelado"
        else:
            self.log_debug(f"      ❌ DESCARTADO: Status relevante não encontrado")
            return None
    
    def _parse_time(self, text: str) -> Optional[Tuple[str, int]]:
        """
        Extrai horário do texto.
        
        Returns:
            Tupla (horario, posicao) ou None se não encontrar
        """
        horario_match = re.search(r'\b(\d{2}:\d{2})\b', text)
        if not horario_match:
            self.log_debug(f"      ❌ DESCARTADO: Horário não encontrado no texto")
            return None
        
        horario_previsto = horario_match.group(1)
        horario_pos = horario_match.start()
        return (horario_previsto, horario_pos)
    
    def _parse_flight_number(self, text: str, horario_pos: int) -> Optional[Dict]:
        """
        Extrai número de voo do texto próximo ao horário.
        
        Returns:
            Dicionário com voo_data ou None se não encontrar
        """
        # Janela expandida (500 chars) para pegar codeshares distantes
        contexto_inicio = max(0, horario_pos - 100)
        contexto_fim = min(len(text), horario_pos + 500)
        snippet = text[contexto_inicio:contexto_fim]
        
        # Remove 'Terminal' seguido de número
        snippet_sem_terminal = re.sub(r'Terminal\s*\d+', '', snippet, flags=re.IGNORECASE)
        snippet_sem_terminal = re.sub(r'\s+', ' ', snippet_sem_terminal).strip()
        
        # Regex flexível: aceita prefixos de 1-3 letras (permite A6509, B1234, etc.)
        voo_match = re.search(r'\b([A-Z]{1,3})?\s*(\d{3,4})\b', snippet_sem_terminal, re.IGNORECASE)
        if not voo_match:
            self.log_debug(f"      ❌ DESCARTADO: Número de voo não encontrado no contexto próximo ao horário")
            return None
        
        voo_prefixo_raw = voo_match.group(1)
        voo_numeros = voo_match.group(2)
        
        # Posição relativa ao snippet (não ao texto completo)
        voo_pos_relativo = voo_match.start()
        voo_pos = contexto_inicio + voo_pos_relativo
        
        # LÓGICA CRÍTICA: Aceita voo antes ou depois do horário (abs) - REMOÇÃO DE TRAVA DE ORDEM
        distancia = abs(voo_pos - horario_pos)
        if distancia > 500:
            self.log_debug(f"      ❌ DESCARTADO: Voo {voo_numeros} muito distante do horário ({distancia} chars)")
            return None
        
        # Validação de Isolamento Atômico: Se houver outro horário entre o horário alvo e o voo, descarte
        # (pertence a outra linha - evita vazamento entre linhas)
        # Usa posições relativas ao snippet_sem_terminal (já processado)
        relative_horario_in_snippet = horario_pos - contexto_inicio
        # Ajusta para posição no snippet_sem_terminal (pode ter mudado após remoção de "Terminal")
        # Busca o horário no snippet processado
        horario_match_in_snippet = re.search(r'\b(\d{2}:\d{2})\b', snippet_sem_terminal)
        if horario_match_in_snippet:
            horario_pos_in_snippet = horario_match_in_snippet.start()
            # Extrai texto entre horário e voo no snippet processado
            start_pos = min(voo_pos_relativo, horario_pos_in_snippet)
            end_pos = max(voo_pos_relativo, horario_pos_in_snippet)
            snippet_between = snippet_sem_terminal[start_pos:end_pos]
            # Se encontrar outro horário entre eles, descarta (vazamento entre linhas)
            horarios_between = re.findall(r'\b\d{2}:\d{2}\b', snippet_between)
            if len(horarios_between) > 1:  # Mais de um horário = vazamento
                self.log_debug(f"      ❌ DESCARTADO: Voo {voo_numeros} pertence a outra linha (horário intermediário detectado)")
                return None
        
        voo_prefixo = voo_prefixo_raw.upper() if voo_prefixo_raw else None
        voo_completo = f"{voo_prefixo}{voo_numeros}" if voo_prefixo else voo_numeros
        
        self.log_debug(f"      ✅ Voo extraído: {voo_completo} (prefixo: {voo_prefixo or 'N/A'}, números: {voo_numeros}, distância: {distancia} chars)")
        
        return {
            'voo_numeros': voo_numeros,
            'voo_prefixo': voo_prefixo,
            'voo_completo': voo_completo,
            'voo_pos': voo_pos
        }
    
    def _parse_destination(self, full_text: str, horario_pos: int = 0, voo_pos: int = 0, horario_previsto: str = "") -> str:
        """
        Extrai destino usando Reconhecimento de Padrão (Keyword Matching).
        
        NOVA ABORDAGEM: Abandona parsing posicional. Se a palavra da cidade está no texto,
        o destino é essa cidade, independente da posição.
        
        Args:
            full_text: Texto completo da linha
            horario_pos: (ignorado - mantido para compatibilidade)
            voo_pos: (ignorado - mantido para compatibilidade)
            horario_previsto: (ignorado - mantido para compatibilidade)
        
        Returns:
            Destino identificado ou "N/A" se não encontrar
        """
        from .config import KNOWN_CITIES
        
        # Abordagem de Dicionário: Procura a cidade em qualquer lugar do texto
        full_text_upper = full_text.upper()
        
        # PRIORIDADE 1: Busca por sigla IATA (3 letras maiúsculas)
        iata_match = re.search(r'\b([A-Z]{3})\b', full_text)
        if iata_match:
            iata_code = iata_match.group(1)
            if iata_code in AIRPORT_DICT:
                destino = AIRPORT_DICT[iata_code]
                self.log_debug(f"      ✅ Destino identificado por IATA {iata_code}: {destino}")
                return destino
        
        # PRIORIDADE 2: Busca por palavras-chave de cidades conhecidas (Keyword Matching)
        for city in KNOWN_CITIES:
            if city.upper() in full_text_upper:
                # Traduz para nome padrão
                destino_traduzido = DestinationExtractor.translate(city)
                if destino_traduzido:
                    self.log_debug(f"      ✅ Destino identificado por keyword '{city}': {destino_traduzido}")
                    return destino_traduzido
                # Se não traduziu, retorna a cidade encontrada
                self.log_debug(f"      ✅ Destino identificado por keyword '{city}'")
                return city
        
        # Não encontrou cidade - retorna "N/A" (será aceito se voo e status forem válidos)
        self.log_debug(f"      ⚠️  Destino não encontrado no texto, usando 'N/A'")
        return "N/A"
    
    def _match_company(self, text: str, voo_data: Dict, status: str = None) -> Optional[str]:
        """
        Identifica companhia aérea em cascata (4 níveis).
        
        Nível 1: Texto direto (AVIANCA no topo - SOBERANIA)
        Nível 2: Prefixo do voo (com MCP para prefixos desconhecidos)
        Nível 3: Faixa numérica (sempre tentar - inferência direta)
        Nível 4: MCP real-time (se status válido e tudo mais válido)
        """
        text_upper = text.upper()
        voo_numeros = voo_data.get('voo_numeros', '')
        voo_prefixo = voo_data.get('voo_prefixo')
        voo_completo = voo_data.get('voo_completo', '')
        
        # ====================================================================
        # NÍVEL 1: TEXTO DIRETO (PRIORIDADE MÁXIMA - SOBERANIA DO TEXTO)
        # ====================================================================
        # SOBERANIA DO TEXTO: Se "AVIANCA" estiver presente, retorna imediatamente
        # Ignora qualquer outra lógica de código ou prefixo
        if "AVIANCA" in text_upper:
            self.log_debug(f"      ✅ Nível 1 (Texto - SOBERANIA): AVIANCA encontrado no texto, retornando imediatamente")
            return "AVIANCA"
        
        # Demais companhias (após verificar AVIANCA)
        companhias_para_buscar = [
            "EMIRATES", "ETHIOPIAN", "ETHIOPIAN AIRLINES", "QATAR AIRWAYS", "ETIHAD",
            "AMERICAN AIRLINES", "DELTA", "UNITED", "AIR FRANCE", "KLM",
            "LUFTHANSA", "SWISS", "IBERIA", "BRITISH AIRWAYS", "TURKISH AIRLINES",
            "SINGAPORE AIRLINES", "COPA", "AEROMÉXICO", "AEROLINEAS ARGENTINAS",
            "GOL", "AZUL", "TAP", "LATAM"
        ]
        
        companhia_do_texto = None
        for companhia in companhias_para_buscar:
            if companhia.upper() in text_upper:
                companhia_do_texto = companhia
                break
        
        if companhia_do_texto:
            self.log_debug(f"      ✅ Nível 1 (Texto): Companhia identificada - {companhia_do_texto}")
            return companhia_do_texto
        
        # ====================================================================
        # NÍVEL 2: PREFIXO DO VOO (EXPANDIDO COM MCP)
        # ====================================================================
        if voo_prefixo:
            from .config import PREFIX_TO_COMPANY
            
            # 2.1: Prefixo conhecido no dicionário
            if voo_prefixo in PREFIX_TO_COMPANY:
                companhia_principal = PREFIX_TO_COMPANY[voo_prefixo]
                self.log_debug(f"      ✅ Nível 2 (Prefixo conhecido): {voo_prefixo} → {companhia_principal}")
                return companhia_principal
            
            # 2.2: Prefixo de 1 letra (A, B, C) - usar MCP imediatamente
            elif len(voo_prefixo) == 1 and self.mcp_diagnostics:
                if voo_completo:
                    # Usa número completo do voo (ex: "A6509")
                    companhia_mcp = self.mcp_diagnostics.search_airline_codes(voo_completo)
                    if companhia_mcp:
                        self.log_debug(f"      ✅ Nível 2 (MCP 1-letra): {voo_completo} → {companhia_mcp}")
                        return companhia_mcp
            
            # 2.3: Prefixo de 2-3 letras desconhecido - usar research para descobrir
            elif len(voo_prefixo) >= 2 and self.mcp_diagnostics:
                patterns = self.mcp_diagnostics.research_flight_code_patterns()
                # Se encontrar padrão, adicionar ao cache e retornar
                # Por enquanto, continua para próximo nível
        
        # ====================================================================
        # NÍVEL 3: FAIXA NUMÉRICA (SEMPRE TENTAR - INFERÊNCIA DIRETA)
        # ====================================================================
        if voo_numeros and voo_numeros.isdigit():
            companhia_faixa = CompanyIdentifier.prioritize_by_number(voo_numeros, [], self.logger)
            if companhia_faixa and companhia_faixa != "N/A":
                self.log_debug(f"      ✅ Nível 3 (Faixa numérica): Voo {voo_numeros} → {companhia_faixa}")
                return companhia_faixa
        
        # ====================================================================
        # NÍVEL 4: CONSULTA REAL-TIME (MCP) - ÚLTIMO RECURSO
        # ====================================================================
        # Se status válido E voo válido, mas companhia não identificada
        if status and voo_completo and self.mcp_diagnostics:
            # Busca real-time do voo específico
            companhia_realtime = self.mcp_diagnostics.search_airline_codes(voo_completo)
            if companhia_realtime:
                self.log_debug(f"      ✅ Nível 4 (MCP real-time): {voo_completo} → {companhia_realtime}")
                return companhia_realtime
        
        # CORREÇÃO pSEO: Não descarta aqui - deixa a validação final decidir
        # Se voo e status são válidos, aceita mesmo sem companhia
        self.log_debug(f"      ⚠️  Companhia não identificada após 4 níveis (será 'N/A' se voo e status válidos)")
        return None  # Retorna None, mas validação final pode aceitar como "N/A"
    
    def _build_flight_dict(self, horario: Tuple[str, int], voo_data: Dict, 
                          destino: str, companhia: str, status: str) -> Dict[str, str]:
        """Constrói dicionário final com dados do voo."""
        horario_previsto, horario_pos = horario
        voo_numeros = voo_data.get('voo_numeros')
        voo_completo = voo_data.get('voo_completo')
        voo_prefixo = voo_data.get('voo_prefixo')
        
        # Extrai horário estimado (segundo horário no texto, se houver)
        # Nota: Precisamos do texto original para isso, mas por enquanto deixamos N/A
        horario_estimado = "N/A"
        
        # CORREÇÃO: Retorna voo_completo no campo "Voo" quando há prefixo (ex: A6509)
        # Mantém compatibilidade: voo_numeros quando não há prefixo
        voo_display = voo_completo if voo_prefixo else voo_numeros
        
        return {
            "Horario_Previsto": horario_previsto,
            "Horario_Estimado": horario_estimado,
            "Voo": voo_display,
            "Voo_Completo": voo_completo,
            "Voo_Prefixo": voo_prefixo if voo_prefixo else "",
            "Companhia": companhia,
            "Companhia_Imagem": companhia,  # Por padrão, usa a principal
            "Destino": destino,
            "Status": status,
        }
    
    def extract_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extração 'Greedy' (Gananciosa): Tenta capturar dados independentes.
        Não aborta se faltar destino ou companhia.
        """
        from .config import STATUS_ALVO, KNOWN_CITIES
        
        try:
            # 1. Limpeza básica
            text_clean = " ".join(text.split())
            
            if not text_clean or len(text_clean) < 10:
                return None
            
            # 2. Busca de Horário (Pivô)
            time_pattern = re.compile(r'\b(\d{2}:\d{2})\b')
            horario_match = time_pattern.search(text_clean)
            if not horario_match:
                return None
            horario_previsto = horario_match.group(1)
            
            # 3. Busca de Status (Independente) - Usa target_statuses configurável
            status_encontrado = None
            for status in self.target_statuses:
                if status.lower() in text_clean.lower():
                    status_encontrado = status
                    break
            
            # 4. Busca de Voo (Regex Flexível 1-3 letras + 3-4 números)
            # Ex: A6509, 7586, LA3030
            flight_pattern = re.compile(r'\b([A-Z]{1,3})?\s*(\d{3,4})\b')
            flight_matches = list(flight_pattern.finditer(text_clean))
            
            best_flight = None
            
            # Escolhe o melhor candidato a voo (o mais próximo do horário ou único)
            if flight_matches:
                # Se houver mais de um, tenta evitar o que parece horário (ex: 0545)
                candidates = []
                for m in flight_matches:
                    num_part = m.group(2)
                    # Evita confundir horário '0545' com voo se estiver muito perto do horário real
                    if num_part == horario_previsto.replace(":", ""):
                        continue
                    candidates.append(m)
                
                if candidates:
                    best_flight = candidates[0]  # Pega o primeiro válido
            
            if not best_flight:
                self.log_debug(f"      ❌ DESCARTADO: Nenhum número de voo encontrado em '{text_clean}'")
                return None
            
            # Processa dados do voo
            prefixo = best_flight.group(1) or ""
            numero = best_flight.group(2)
            # Garante formatação correta: prefixo + número (ex: "A6509" ou "7586")
            voo_completo = f"{prefixo}{numero}" if prefixo else numero
            
            # 5. Busca de Destino (Dicionário Global - Independente da posição)
            destino = "N/A"
            for cidade in KNOWN_CITIES:
                # Usa boundaries para evitar match parcial (ex: 'Rio' em 'Rio de Janeiro')
                if cidade.upper() in text_clean.upper():
                    destino = cidade
                    break
            
            # 6. Identificação de Companhia (Cascata)
            # Tenta pelo texto bruto primeiro (Soberania)
            companhia = "N/A"
            
            # Usa a lógica de identificação existente
            text_upper = text_clean.upper()
            
            # Nível 1: Texto direto (Soberania)
            if "AVIANCA" in text_upper:
                companhia = "AVIANCA"
            elif "LATAM" in text_upper or "TAM" in text_upper:
                companhia = "LATAM"
            elif "GOL" in text_upper:
                companhia = "GOL"
            elif "AZUL" in text_upper:
                companhia = "AZUL"
            elif "EMIRATES" in text_upper:
                companhia = "EMIRATES"
            else:
                # Nível 2: Prefixo do voo
                if prefixo:
                    companhia_prefixo = CompanyIdentifier.from_prefix(prefixo)
                    if companhia_prefixo:
                        companhia = companhia_prefixo
                
                # Nível 3: Faixa numérica (tenta mesmo se prefixo não funcionou)
                if companhia == "N/A" and numero.isdigit():
                    voo_num = int(numero)
                    # Usa a lógica de prioritize_by_number (chama o método estático)
                    companhia_por_numero = CompanyIdentifier.prioritize_by_number(numero, [], self.logger)
                    if companhia_por_numero and companhia_por_numero != "N/A":
                        companhia = companhia_por_numero
            
            # 7. VALIDAÇÃO FINAL "pSEO" (O Ultimato Real)
            # Se tem VOO e tem STATUS, salvamos. O resto é lucro.
            if status_encontrado:
                
                if destino == "N/A":
                    self.log(f"      ⚠️  SALVANDO VOO {voo_completo} SEM DESTINO (pSEO)")
                
                return {
                    "Horario": horario_previsto,
                    "Voo": numero,
                    "Voo_Completo": voo_completo,
                    "Companhia": companhia,
                    "Destino": destino,
                    "Status": status_encontrado,
                    "Terminal": "N/A",  # Terminal é secundário
                    "Snapshot_Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            
            self.log_debug(f"      ❌ DESCARTADO: Tem voo ({voo_completo}) mas sem status válido.")
            return None
        
        except Exception as e:
            self.log_error(f"   ❌ Erro ao extrair dados: {e}")
            if self.logger:
                import traceback
                self.logger.debug(traceback.format_exc())
            return None
    
    def consolidate_codeshare(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Consolida voos codeshare em uma única linha.
        
        Identifica voos com mesmo Horario_Previsto e Destino (mesma aeronave física).
        Cria coluna 'Parceiras' com todas as companhias exceto a principal.
        """
        self.log(f"   🔗 Consolidando voos codeshare (mesmo Horario_Previsto + Destino)...")
        
        def consolidate_group(group):
            """Consolida um grupo de voos codeshare"""
            if len(group) == 1:
                group = group.copy()
                if 'Parceiras' not in group.columns:
                    group['Parceiras'] = ""
                return group
            
            all_companies_main = group['Companhia'].unique().tolist()
            all_companies_main = [c for c in all_companies_main if c and c != "N/A"]
            
            all_companies_images = []
            if 'Companhia_Imagem' in group.columns:
                all_companies_images = group['Companhia_Imagem'].unique().tolist()
                all_companies_images = [c for c in all_companies_images if c and c != "N/A"]
            
            all_companies = list(set(all_companies_main + all_companies_images))
            all_companies = [c for c in all_companies if c and c != "N/A"]
            
            all_voos = group['Voo'].unique().tolist()
            all_voos = [v for v in all_voos if v and v != "N/A"]
            
            all_prefixos = []
            prefixo_to_company = {}
            if 'Voo_Prefixo' in group.columns:
                for idx, row in group.iterrows():
                    prefixo = str(row.get('Voo_Prefixo', '')).strip()
                    if prefixo and prefixo != "":
                        company_from_prefix = CompanyIdentifier.from_prefix(prefixo)
                        if company_from_prefix:
                            all_prefixos.append(prefixo)
                            prefixo_to_company[prefixo] = company_from_prefix
            
            all_prefixos = list(dict.fromkeys(all_prefixos))
            
            destino = group['Destino'].iloc[0]
            voo_principal = all_voos[0] if all_voos else "N/A"
            
            prefixo_principal = ""
            if all_prefixos:
                prefixo_principal = all_prefixos[0]
                main_company_by_prefix = prefixo_to_company.get(prefixo_principal)
                if main_company_by_prefix:
                    self.log(f"      🎯 Consolidação: Prefixo {prefixo_principal} identificado → Companhia principal: {main_company_by_prefix}")
                    main_company = main_company_by_prefix
                else:
                    main_company = CompanyIdentifier.choose_main(all_companies, destino, voo_principal, prefixo_principal, self.logger)
            else:
                main_company = CompanyIdentifier.choose_main(all_companies, destino, voo_principal, "", self.logger)
            
            parceiras = [c for c in all_companies if c != main_company and c and c != "N/A"]
            parceiras_str = ", ".join(sorted(parceiras)) if parceiras else ""
            
            voo_final = voo_principal
            if prefixo_principal:
                prefixo_rows = group[group['Voo_Prefixo'] == prefixo_principal] if 'Voo_Prefixo' in group.columns else pd.DataFrame()
                if len(prefixo_rows) > 0:
                    voo_final = prefixo_rows['Voo'].iloc[0]
                    self.log(f"      ✅ Voo final escolhido pelo prefixo {prefixo_principal}: {voo_final}")
                else:
                    main_company_rows = group[group['Companhia'] == main_company]
                    if len(main_company_rows) > 0:
                        voo_final = main_company_rows['Voo'].iloc[0]
            else:
                main_company_rows = group[group['Companhia'] == main_company]
                if len(main_company_rows) > 0:
                    voo_final = main_company_rows['Voo'].iloc[0]
            
            consolidated_row = group.iloc[0].copy()
            consolidated_row['Companhia'] = main_company
            consolidated_row['Voo'] = voo_final
            consolidated_row['Parceiras'] = parceiras_str
            
            if 'Voo_Completo' in consolidated_row:
                del consolidated_row['Voo_Completo']
            if 'Voo_Prefixo' in consolidated_row:
                del consolidated_row['Voo_Prefixo']
            if 'Companhia_Imagem' in consolidated_row:
                del consolidated_row['Companhia_Imagem']
            
            horarios_estimados = group['Horario_Estimado'].unique()
            horarios_validos = [h for h in horarios_estimados if h and h != "N/A"]
            if horarios_validos:
                consolidated_row['Horario_Estimado'] = horarios_validos[0]
            
            return pd.DataFrame([consolidated_row])
        
        df_consolidated = df.groupby(['Horario_Previsto', 'Destino'], group_keys=False).apply(
            consolidate_group
        ).reset_index(drop=True)
        
        return df_consolidated
    
    def save_to_csv(self, scraped_flights: List[Dict[str, str]], csv_path: str) -> int:
        """
        Salva voos no CSV (novo arquivo com timestamp) com limpeza de dados usando Pandas.
        
        Returns:
            Número de voos salvos
        """
        agora = datetime.now()
        data_captura = agora.strftime("%Y-%m-%d")
        databusca_timestamp = agora.strftime("%Y-%m-%d %H:%M:%S")
        
        if not scraped_flights:
            self.log(f"\n💾 Nenhum voo encontrado para salvar.")
            return 0
        
        self.log(f"\n💾 SALVANDO: Processando voos em novo arquivo CSV...")
        
        flights_to_save = []
        self.log(f"   📋 Processando {len(scraped_flights)} voo(s) da busca atual...")
        
        for flight in scraped_flights:
            voo = str(flight.get('Voo', '')).strip()
            # Usa Horario se Horario_Previsto não estiver disponível (compatibilidade)
            horario_previsto = str(flight.get('Horario_Previsto') or flight.get('Horario', '')).strip()
            
            # Validação permissiva: só descarta se realmente não tiver voo ou horário
            if not voo or voo == "N/A" or not horario_previsto or horario_previsto == "N/A":
                self.log_debug(f"      🗑️  Voo incompleto no save_to_csv: Voo={voo}, Horario={horario_previsto}")
                continue
            
            alerta_1h, alerta_2h, atraso_minutos = calculate_delay_alerts(
                horario_previsto, 
                str(flight.get('Horario_Estimado', 'N/A')).strip()
            )
            
            destino = str(flight.get('Destino', 'N/A')).strip()
            if destino in COMPANHIAS_CONHECIDAS:
                destino = "N/A"
            
            destino = DestinationExtractor.translate(destino)
            
            flight_data = {
                "databusca": databusca_timestamp.strip(),
                "Data": data_captura.strip(),
                "Horario_Previsto": horario_previsto.strip(),
                "Horario_Estimado": str(flight.get('Horario_Estimado', 'N/A')).strip(),
                "Voo": voo.strip(),
                "Voo_Completo": str(flight.get('Voo_Completo', voo)).strip(),
                "Voo_Prefixo": str(flight.get('Voo_Prefixo', '')).strip(),
                "Companhia": str(flight.get('Companhia', 'N/A')).strip(),
                "Companhia_Imagem": str(flight.get('Companhia_Imagem', '')).strip(),
                "Destino": destino.strip(),
                "Status": str(flight.get('Status', 'N/A')).strip(),
                "Alerta_1H": str(alerta_1h).strip(),
                "Alerta_2H": str(alerta_2h).strip(),
                "Status_Monitoramento": "Ativo".strip(),
            }
            
            flights_to_save.append(flight_data)
        
        if not flights_to_save:
            self.log(f"\n💾 Nenhum voo válido para salvar após processamento.")
            return 0
        
        # Processamento e Deduplicação Inteligente com Pandas
        self.log(f"   🔄 Convertendo para DataFrame do Pandas...")
        df = pd.DataFrame(flights_to_save)
        
        self.log(f"   🔍 Deduplicação inteligente (manter destino correto quando houver duplicatas)...")
        duplicates_before = len(df)
        
        def keep_best_row(group):
            """Para cada grupo de duplicatas, mantém a linha com destino válido"""
            if len(group) == 1:
                return group
            
            valid_destinations = group[~group['Destino'].apply(FlightValidator.is_invalid_destination_for_dedup)]
            invalid_destinations = group[group['Destino'].apply(FlightValidator.is_invalid_destination_for_dedup)]
            
            if len(valid_destinations) > 0:
                return valid_destinations.iloc[[0]]
            else:
                return group.iloc[[0]]
        
        df_deduplicated = df.groupby(['Voo', 'Horario_Previsto'], group_keys=False).apply(keep_best_row).reset_index(drop=True)
        df = df_deduplicated
        
        duplicates_removed = duplicates_before - len(df)
        if duplicates_removed > 0:
            self.log(f"   ✅ {duplicates_removed} duplicata(s) removida(s) (mantido destino correto)")
        
        # Limpeza: strip() em todas as colunas de texto
        self.log(f"   🧹 Aplicando strip() em todas as colunas de texto...")
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        
        # Aplica AIRPORT_DICT (tradução de siglas IATA e nomes cortados)
        self.log(f"   🌍 Aplicando tradução de destinos (AIRPORT_DICT)...")
        df['Destino'] = df['Destino'].apply(DestinationExtractor.translate)
        
        # Limpeza Final da Coluna Companhia
        self.log(f"   🧹 Limpeza final da coluna Companhia (removendo barras '/')...")
        df['Companhia'] = df['Companhia'].astype(str).str.split('/').str[0].str.strip()
        df['Companhia'] = df['Companhia'].str.replace(r'^\s*/\s*|\s*/\s*$', '', regex=True).str.strip()
        # CORREÇÃO: Garante que "N" (truncamento) seja convertido para "N/A"
        df['Companhia'] = df['Companhia'].replace(['N', 'n', 'nan', 'None', ''], 'N/A')
        
        # CONSOLIDAÇÃO DE VOOS CODESHARE
        before_consolidation = len(df)
        df = self.consolidate_codeshare(df)
        after_consolidation = len(df)
        consolidated_count = before_consolidation - after_consolidation
        if consolidated_count > 0:
            self.log(f"   ✅ {consolidated_count} linha(s) codeshare consolidada(s) em {after_consolidation} linha(s) única(s)")
        
        if 'Parceiras' not in df.columns:
            df['Parceiras'] = ""
        
        # Limpeza Final
        self.log(f"   🧹 Limpeza final (removendo N/A e 'Detalhes' inválidos)...")
        df = df[df['Companhia'] != 'N/A']
        df = df[~df['Destino'].apply(FlightValidator.is_invalid_destination_for_dedup)]
        df = df[~df['Destino'].str.upper().isin(NON_CITY_WORDS)]
        
        # Remove colunas internas
        self.log(f"   🧹 Removendo colunas internas de processamento...")
        columns_to_remove = ['Voo_Completo', 'Voo_Prefixo', 'Companhia_Imagem']
        for col in columns_to_remove:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        # Define ordem das colunas
        column_order = [
            'databusca', 'Data', 'Horario_Previsto', 'Horario_Estimado', 
            'Voo', 'Companhia', 'Parceiras', 'Destino', 'Status', 
            'Alerta_1H', 'Alerta_2H', 'Status_Monitoramento'
        ]
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
        
        # Exportação Final
        try:
            self.log(f"   💾 Exportando CSV final...")
            df.to_csv(csv_path, index=False, encoding=CSV_ENCODING)
            
            flights_count = len(df)
            self.log(f"\n   ✅ {flights_count} voo(s) salvo(s) no CSV")
            
            # Mostra alguns exemplos
            for idx, row in df.head(10).iterrows():
                voo = row['Voo']
                companhia = row['Companhia']
                destino = row['Destino']
                self.log(f"      ✅ SALVO: Voo {voo} da {companhia} → {destino}")
            if flights_count > 10:
                self.log(f"      ... e mais {flights_count - 10} voo(s)")
        
        except Exception as e:
            error_msg = f"   ❌ ERRO CRÍTICO ao salvar CSV: {e}"
            self.log_error(error_msg)
            if self.logger:
                import traceback
                self.logger.debug(traceback.format_exc())
            return 0
        
        return flights_count
