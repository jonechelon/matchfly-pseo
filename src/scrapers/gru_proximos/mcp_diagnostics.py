"""
Módulo de diagnóstico inteligente via MCP Perplexity.
Centraliza todas as chamadas MCP para diagnóstico e aprendizado contínuo.
"""
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import LOG_DIR, LOG_ENCODING

# Garante que o diretório de logs existe
os.makedirs(LOG_DIR, exist_ok=True)

# Caminho do arquivo de cache
CACHE_FILE = os.path.join(LOG_DIR, "mcp_cache.json")
DIAGNOSTICS_LOG = os.path.join(LOG_DIR, "mcp_diagnostics.log")

# Configuração de cache (em horas)
CACHE_TTL_PATTERNS = 24  # Padrões de códigos: 24h
CACHE_TTL_AIRLINE = 168  # Identificação de companhia: 7 dias
CACHE_TTL_PLAYWRIGHT = 168  # Recomendações Playwright: 7 dias

# Rate limiting
MAX_MCP_CALLS_PER_RUN = 10
_mcp_call_count = 0


class MCPDiagnostics:
    """Diagnóstico inteligente via MCP Perplexity."""
    
    def __init__(self, logger: Optional[logging.Logger] = None, dry_run: bool = False):
        """
        Inicializa o módulo de diagnóstico.
        
        Args:
            logger: Logger opcional para substituir prints
            dry_run: Se True, não faz chamadas MCP reais (apenas simula)
        """
        self.logger = logger
        self.log = logger.info if logger else print
        self.log_error = logger.error if logger else print
        self.log_debug = logger.debug if logger else print
        self.dry_run = dry_run or os.getenv("MCP_DRY_RUN", "false").lower() == "true"
        self.cache = self._load_cache()
        self._setup_diagnostics_logger()
    
    def _setup_diagnostics_logger(self) -> None:
        """Configura logger específico para diagnóstico MCP."""
        self.diag_logger = logging.getLogger("mcp_diagnostics")
        self.diag_logger.setLevel(logging.DEBUG)
        
        # Handler para arquivo de diagnóstico
        file_handler = logging.FileHandler(DIAGNOSTICS_LOG, encoding=LOG_ENCODING)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.diag_logger.addHandler(file_handler)
    
    def _load_cache(self) -> Dict[str, Any]:
        """Carrega cache de resultados MCP."""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.log_error(f"Erro ao carregar cache MCP: {e}")
        return {}
    
    def _save_cache(self) -> None:
        """Salva cache de resultados MCP."""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_error(f"Erro ao salvar cache MCP: {e}")
    
    def _is_cache_valid(self, key: str, ttl_hours: int) -> bool:
        """Verifica se item do cache ainda é válido."""
        if key not in self.cache:
            return False
        
        cached_time = self.cache[key].get('timestamp')
        if not cached_time:
            return False
        
        try:
            cached_dt = datetime.fromisoformat(cached_time)
            age = datetime.now() - cached_dt
            return age < timedelta(hours=ttl_hours)
        except Exception:
            return False
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Retorna valor do cache se válido."""
        if key in self.cache and self.cache[key].get('data'):
            return self.cache[key]['data']
        return None
    
    def _set_cached(self, key: str, value: Any) -> None:
        """Armazena valor no cache."""
        self.cache[key] = {
            'data': value,
            'timestamp': datetime.now().isoformat()
        }
        self._save_cache()
    
    def _call_mcp_tool(self, server: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Chama uma ferramenta MCP via call_mcp_tool.
        
        Nota: Esta função será implementada quando houver integração direta com MCP.
        Por enquanto, retorna None em modo dry_run ou lança NotImplementedError.
        
        Args:
            server: Nome do servidor MCP (ex: "user-perplexity-search")
            tool_name: Nome da ferramenta (ex: "perplexity_research")
            arguments: Argumentos para a ferramenta
        
        Returns:
            Resposta da ferramenta MCP ou None
        """
        global _mcp_call_count
        
        if _mcp_call_count >= MAX_MCP_CALLS_PER_RUN:
            self.log_debug(f"Rate limit atingido: {MAX_MCP_CALLS_PER_RUN} chamadas MCP por execução")
            return None
        
        if self.dry_run:
            self.log_debug(f"[DRY-RUN] Chamada MCP: {server}.{tool_name}({arguments})")
            return {"response": "Dry-run mode: no actual MCP call made"}
        
        _mcp_call_count += 1
        self.diag_logger.info(f"MCP Call #{_mcp_call_count}: {server}.{tool_name}")
        self.diag_logger.debug(f"Arguments: {json.dumps(arguments, indent=2)}")
        
        # NOTA: Para implementar chamadas MCP reais, você pode:
        # 1. Usar uma biblioteca Python MCP quando disponível
        # 2. Criar um serviço intermediário que chama MCP tools
        # 3. Usar subprocess para chamar ferramentas MCP via CLI
        # 
        # Por enquanto, o código está estruturado para funcionar em modo dry-run
        # e com fallbacks para lógica estática quando MCP não está disponível.
        
        # Em modo de produção, você pode descomentar e adaptar:
        # try:
        #     from mcp import Client
        #     client = Client(server)
        #     result = client.call_tool(tool_name, arguments)
        #     return result
        # except ImportError:
        #     pass
        
        self.log_debug(f"MCP call not yet implemented (dry-run ou fallback): {server}.{tool_name}")
        return None
    
    def research_flight_code_patterns(self) -> Dict[str, List[str]]:
        """
        Usa perplexity_research para descobrir todos os padrões de códigos de voo.
        
        Returns:
            Dict com padrões IATA (2 letras), ICAO (3 letras) e códigos especiais (1 letra)
        """
        cache_key = "flight_code_patterns"
        
        # Verifica cache
        if self._is_cache_valid(cache_key, CACHE_TTL_PATTERNS):
            cached = self._get_cached(cache_key)
            if cached:
                self.log_debug("Usando padrões de códigos de voo do cache")
                return cached
        
        query = """
        List all variations of flight codes that operate at GRU Airport (São Paulo):
        - IATA codes (2 letters): LA, G3, AD, TP, etc.
        - ICAO codes (3 letters): TAM, GLO, AZU, etc.
        - Special regional codes (1 letter): A, B, C (for regional partners)
        - Hybrid formats: A6509, B1234, etc.
        
        Focus on codes used by airlines operating at GRU in 2024-2025.
        Provide a comprehensive list with examples.
        """
        
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]
        
        try:
            result = self._call_mcp_tool(
                "user-perplexity-search",
                "perplexity_research",
                {"messages": messages, "strip_thinking": True}
            )
            
            if result and "response" in result:
                # Parse da resposta para extrair padrões
                # Por enquanto, retorna padrões conhecidos + descobertos
                patterns = self._parse_flight_patterns(result["response"])
                self._set_cached(cache_key, patterns)
                self.diag_logger.info(f"Padrões descobertos: {len(patterns)} categorias")
                return patterns
        except Exception as e:
            self.log_error(f"Erro ao pesquisar padrões de códigos: {e}")
            self.diag_logger.error(f"Erro em research_flight_code_patterns: {e}", exc_info=True)
        
        # Fallback: retorna padrões conhecidos
        return self._get_known_patterns()
    
    def _parse_flight_patterns(self, response: str) -> Dict[str, List[str]]:
        """
        Parse da resposta do Perplexity para extrair padrões.
        
        Args:
            response: Resposta do Perplexity
        
        Returns:
            Dict com padrões categorizados
        """
        patterns = {
            "iata_2_letters": [],
            "icao_3_letters": [],
            "single_letter": [],
            "hybrid": []
        }
        
        # Extrai padrões conhecidos da resposta
        # Por enquanto, retorna padrões conhecidos
        return self._get_known_patterns()
    
    def _get_known_patterns(self) -> Dict[str, List[str]]:
        """Retorna padrões conhecidos de códigos de voo."""
        from .config import PREFIX_TO_COMPANY
        
        return {
            "iata_2_letters": list(PREFIX_TO_COMPANY.keys()),
            "icao_3_letters": ["TAM", "GLO", "AZU", "LAT"],
            "single_letter": ["A", "B", "C"],  # Códigos regionais
            "hybrid": ["A6509", "B1234"]  # Exemplos
        }
    
    def search_airline_codes(self, code: str) -> Optional[str]:
        """
        Usa perplexity_search para identificar companhia aérea por código.
        
        Aceita tanto prefixo parcial quanto número completo do voo.
        
        Args:
            code: Pode ser prefixo parcial (ex: "A65") ou número completo (ex: "A6509", "7586")
        
        Returns:
            Nome da companhia aérea ou None
        """
        if not code or len(code) < 2:
            return None
        
        cache_key = f"airline_code_{code.upper()}"
        
        # Verifica cache
        if self._is_cache_valid(cache_key, CACHE_TTL_AIRLINE):
            cached = self._get_cached(cache_key)
            if cached:
                self.log_debug(f"Companhia {cached} encontrada no cache para código {partial_code}")
                return cached
        
        # Adapta query para número completo ou prefixo parcial
        if len(code) >= 4 and code[0].isalpha() and code[1:].isdigit():
            # Número completo (ex: "A6509", "G31234")
            query = f"flight number {code} GRU airport São Paulo airline"
        else:
            # Prefixo parcial (ex: "A65", "LA")
            query = f"airline code {code} flight number GRU airport São Paulo"
        
        try:
            result = self._call_mcp_tool(
                "user-perplexity-search",
                "perplexity_search",
                {
                    "query": query,
                    "max_results": 5,
                    "country": "BR"
                }
            )
            
            if result and "results" in result:
                # Parse da resposta para identificar companhia
                airline = self._parse_airline_from_search(result["results"], code)
                if airline:
                    self._set_cached(cache_key, airline)
                    self.diag_logger.info(f"Código {code} identificado como {airline}")
                    return airline
        except Exception as e:
            self.log_error(f"Erro ao buscar companhia por código {code}: {e}")
            self.diag_logger.error(f"Erro em search_airline_codes: {e}", exc_info=True)
        
        return None
    
    def _parse_airline_from_search(self, results: str, code: str) -> Optional[str]:
        """
        Parse dos resultados de busca para identificar companhia.
        
        Args:
            results: Resultados da busca Perplexity
            code: Código usado na busca (pode ser parcial ou completo)
        
        Returns:
            Nome da companhia ou None
        """
        # Por enquanto, tenta identificar por padrões conhecidos
        from .config import PREFIX_TO_COMPANY
        
        # Se o código começa com prefixo conhecido (2-3 letras)
        if len(code) >= 2:
            prefix_2 = code[:2].upper()
            if prefix_2 in PREFIX_TO_COMPANY:
                return PREFIX_TO_COMPANY[prefix_2]
            
            # Tenta prefixo de 1 letra
            if len(code) >= 1:
                prefix_1 = code[0].upper()
                if prefix_1 in PREFIX_TO_COMPANY:
                    return PREFIX_TO_COMPANY[prefix_1]
        
        # Tenta identificar por palavras-chave nos resultados
        results_upper = results.upper()
        known_airlines = [
            "AVIANCA", "LATAM", "GOL", "AZUL", "EMIRATES", "TURKISH",
            "AMERICAN", "DELTA", "UNITED", "AIR FRANCE", "KLM"
        ]
        
        for airline in known_airlines:
            if airline in results_upper:
                return airline
        
        return None
    
    def reason_about_discard(self, row_text: str, discard_reason: str) -> Dict[str, Any]:
        """
        Usa perplexity_reason para analisar por que um voo foi descartado.
        
        Args:
            row_text: Texto bruto capturado da linha
            discard_reason: Razão do descarte (ex: "distância > 200", "sem companhia")
        
        Returns:
            Dict com análise causal e sugestões de correção
        """
        query = f"""
        Analyze why this flight data extraction failed:
        
        Row Text: {row_text[:500]}  # Limita para não exceder tokens
        Discard Reason: {discard_reason}
        Context: Flight numbers 7586, 7484, A6509 were visible in PDF but not captured.
        
        Was the discard caused by:
        1. Visual noise (terminal numbers, ads, etc.)?
        2. Missing airport dictionary entry?
        3. Distance threshold too strict (200 chars)?
        4. Missing airline in static dictionary?
        5. Regex pattern too restrictive?
        
        Provide specific recommendations to fix this pattern.
        """
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert in web scraping and data extraction. Analyze flight data extraction failures and provide actionable recommendations."
            },
            {
                "role": "user",
                "content": query
            }
        ]
        
        try:
            result = self._call_mcp_tool(
                "user-perplexity-search",
                "perplexity_reason",
                {"messages": messages, "strip_thinking": True}
            )
            
            if result and "response" in result:
                analysis = {
                    "discard_reason": discard_reason,
                    "row_text_sample": row_text[:200],
                    "analysis": result["response"],
                    "timestamp": datetime.now().isoformat()
                }
                self.diag_logger.info(f"Análise de descarte: {discard_reason}")
                self.diag_logger.debug(f"Análise completa: {json.dumps(analysis, indent=2)}")
                return analysis
        except Exception as e:
            self.log_error(f"Erro ao analisar descarte: {e}")
            self.diag_logger.error(f"Erro em reason_about_discard: {e}", exc_info=True)
        
        # Fallback: retorna análise básica
        return {
            "discard_reason": discard_reason,
            "row_text_sample": row_text[:200],
            "analysis": "Análise MCP não disponível - usando fallback",
            "timestamp": datetime.now().isoformat()
        }
    
    def ask_playwright_best_practices(self, site_url: str) -> Dict[str, Any]:
        """
        Usa perplexity_ask para consultar melhores práticas de scraping.
        
        Args:
            site_url: URL do site (ex: "https://www.gru.com.br")
        
        Returns:
            Dict com seletores recomendados e estratégias de wait
        """
        cache_key = f"playwright_practices_{site_url}"
        
        # Verifica cache
        if self._is_cache_valid(cache_key, CACHE_TTL_PLAYWRIGHT):
            cached = self._get_cached(cache_key)
            if cached:
                self.log_debug("Usando recomendações Playwright do cache")
                return cached
        
        query = f"""
        What are the best Playwright practices for scraping dynamic content from:
        - Site: {site_url}/pt/passageiro/voos
        - Framework: Aena (airport management system)
        
        Specifically:
        1. What selectors indicate "loading complete" (spinners, loading states)?
        2. How long to wait after "Carregar mais" button click?
        3. What is the best selector for the last row of the flights table?
        4. Should I use wait_for_selector, wait_for_load_state, or custom waits?
        
        Provide specific CSS selectors and wait strategies.
        """
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert in Playwright web automation and scraping dynamic content."
            },
            {
                "role": "user",
                "content": query
            }
        ]
        
        try:
            result = self._call_mcp_tool(
                "user-perplexity-search",
                "perplexity_ask",
                {"messages": messages}
            )
            
            if result and "response" in result:
                recommendations = {
                    "site_url": site_url,
                    "recommendations": result["response"],
                    "timestamp": datetime.now().isoformat()
                }
                self._set_cached(cache_key, recommendations)
                self.diag_logger.info(f"Recomendações Playwright obtidas para {site_url}")
                return recommendations
        except Exception as e:
            self.log_error(f"Erro ao consultar práticas Playwright: {e}")
            self.diag_logger.error(f"Erro em ask_playwright_best_practices: {e}", exc_info=True)
        
        # Fallback: retorna recomendações padrão
        return {
            "site_url": site_url,
            "recommendations": "Recomendações MCP não disponíveis - usando padrões",
            "timestamp": datetime.now().isoformat()
        }
