"""
Módulo de navegação e scraping com Playwright.
Implementa Modo Offline/Congelamento de DOM.
"""
import random
import logging
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Route

from .config import (
    VOOS_URL, USER_AGENTS, PAGE_LOAD_TIMEOUT, ELEMENT_WAIT_TIMEOUT,
    INITIAL_PAGE_WAIT, CLICK_WAIT_OBLIGATORY, CLICK_WAIT_ADDITIONAL,
    SCROLL_WAIT, FINAL_RENDER_WAIT, OFFLINE_STABILIZATION_WAIT,
    LOAD_MORE_SELECTORS, MAX_LOAD_MORE_CLICKS, WAIT_BETWEEN_CLICKS_MS
)
from .data_processor import FlightDataProcessor

# Importação opcional do MCPDiagnostics
try:
    from .mcp_diagnostics import MCPDiagnostics
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPDiagnostics = None
class ScraperEngine:
    """Engine de scraping com Playwright."""
    
    def __init__(self, headless: bool = True, max_clicks: int = 5, logger: logging.Logger = None, 
                 enable_mcp: bool = True, target_statuses: Optional[List[str]] = None, 
                 output_dir: Optional[str] = None, csv_prefix: Optional[str] = None):
        """
        Inicializa o engine de scraping.
        
        Args:
            headless: Modo headless (sem interface gráfica)
            max_clicks: Número máximo de cliques no botão "Carregar mais"
            logger: Logger opcional para substituir prints
            enable_mcp: Se True, habilita diagnóstico MCP (padrão: True)
            target_statuses: Lista de status alvo (sobrescreve STATUS_ALVO do config)
            output_dir: Diretório de saída (sobrescreve LOG_DIR do config)
            csv_prefix: Prefixo do arquivo CSV (sobrescreve CSV_FILE_NAME_TEMPLATE)
        """
        from .config import STATUS_ALVO, LOG_DIR, CSV_FILE_NAME_TEMPLATE
        
        self.headless = headless
        self.max_clicks = max_clicks
        self.logger = logger
        self.log = logger.info if logger else print
        self.log_error = logger.error if logger else print
        
        # Configurações dinâmicas (sobrescrevem config.py)
        self.target_statuses = target_statuses if target_statuses else STATUS_ALVO
        self.output_dir = output_dir if output_dir else LOG_DIR
        self.csv_prefix = csv_prefix
        
        self.processor = FlightDataProcessor(logger=logger, enable_mcp=enable_mcp, target_statuses=self.target_statuses)
        
        # Inicializa MCPDiagnostics se disponível
        self.mcp_diagnostics = None
        if enable_mcp and MCP_AVAILABLE and MCPDiagnostics:
            try:
                self.mcp_diagnostics = MCPDiagnostics(logger=logger)
                self.log("   ✅ MCP Diagnostics habilitado")
            except Exception as e:
                self.log_error(f"Erro ao inicializar MCP Diagnostics: {e}")
                self.mcp_diagnostics = None
    
    def _get_random_user_agent(self) -> str:
        """Retorna um User-Agent aleatório da lista."""
        return random.choice(USER_AGENTS)
    
    def _load_all_pages(self, page) -> int:
        """
        Carrega todas as páginas clicando no botão "Carregar mais".
        
        MANTÉM: Lógica de cliques obrigatórios e waits
        
        Returns:
            Número de cliques realizados
        """
        self.log(f"\n🔄 Procurando botão 'Carregar mais' (OBRIGATÓRIO: {self.max_clicks} cliques completos)...")
        clicks_performed = 0
        
        for attempt in range(self.max_clicks):
            button_found = False
            for selector in LOAD_MORE_SELECTORS:
                try:
                    button = page.query_selector(selector)
                    if button and button.is_visible():
                        self.log(f"   [{attempt + 1}/{self.max_clicks}] Clicando no botão 'Carregar mais'...")
                        button.click()
                        button_found = True
                        clicks_performed += 1
                        self.log(f"      ⏳ Aguardando {CLICK_WAIT_OBLIGATORY}ms OBRIGATÓRIOS para crescimento da tabela...")
                        page.wait_for_timeout(CLICK_WAIT_OBLIGATORY)
                        page.wait_for_timeout(CLICK_WAIT_ADDITIONAL)
                        break
                except Exception as e:
                    if attempt == 0:
                        self.log(f"      ⚠️  Erro ao clicar (tentativa {attempt + 1}): {e}")
                    continue
            
            if not button_found:
                if attempt < 2:
                    try:
                        self.log(f"      🔄 Rolando página para encontrar botão (tentativa {attempt + 1})...")
                        page.mouse.wheel(0, 2000)
                        page.wait_for_timeout(WAIT_BETWEEN_CLICKS_MS)
                        continue
                    except Exception:
                        pass
                
                if clicks_performed < self.max_clicks:
                    self.log(f"      ⚠️  Botão não encontrado na tentativa {attempt + 1}, tentando novamente...")
                    page.wait_for_timeout(WAIT_BETWEEN_CLICKS_MS)
                    continue
                else:
                    break
        
        if clicks_performed < self.max_clicks:
            self.log(f"      ⚠️  AVISO: Apenas {clicks_performed} de {self.max_clicks} cliques foram realizados")
            self.log(f"      ⚠️  Alguns voos podem não ter sido carregados")
        else:
            self.log(f"      ✅ Todos os {self.max_clicks} cliques foram realizados com sucesso")
        
        self.log(f"\n✅ Carregamento concluído ({clicks_performed} clique(s))")
        
        return clicks_performed
    
    def _scroll_to_render(self, page) -> None:
        """
        Rola a página até o final para garantir que todos os logos foram renderizados.
        """
        self.log(f"   📜 Rolando página até o final para garantir renderização de todos os logos...")
        try:
            for scroll_attempt in range(3):
                page.mouse.wheel(0, 5000)
                page.wait_for_timeout(SCROLL_WAIT)
            page.mouse.wheel(0, -1000)
            page.wait_for_timeout(SCROLL_WAIT)
            self.log(f"   ✅ Scroll completo - todos os logos devem estar renderizados")
        except Exception as e:
            self.log(f"   ⚠️  Erro durante scroll: {e} (continuando mesmo assim)")
    
    def _freeze_dom(self, context) -> None:
        """
        Ativa modo offline para congelar o DOM.
        
        MANTÉM: Modo Offline/Congelamento de DOM (context.set_offline(True))
        """
        self.log(f"   🔒 Ativando modo offline para congelar o DOM...")
        context.set_offline(True)
        self.log(f"   ✅ Modo offline ativado - DOM congelado")
        self.log(f"   ⏳ Aguardando {OFFLINE_STABILIZATION_WAIT}ms para estabilização total...")
        # Nota: wait_for_timeout precisa ser chamado na page, não no context
        # Mas como estamos congelando, não precisamos esperar na page
        # A espera será feita na page antes de chamar este método
    
    def _unfreeze_dom(self, context) -> None:
        """Retorna ao modo online."""
        self.log(f"   🔄 Retornando ao modo online...")
        context.set_offline(False)
        self.log(f"   ✅ Modo online restaurado")
    
    def scrape(self) -> List[Dict[str, str]]:
        """
        Executa scraping completo do GRU.
        
        Fases:
        1. ONLINE: Carrega todas as páginas
        2. OFFLINE: Congela o DOM
        3. EXTRAÇÃO: Extrai dados com snapshot estático
        4. ONLINE: Retorna ao modo online
        
        MANTÉM: Fases de carregamento (ONLINE → OFFLINE → EXTRAÇÃO → ONLINE)
        
        Returns:
            Lista de dicionários com dados dos voos extraídos
        """
        self.log("=" * 70)
        self.log("🌐 SCRAPING GRU - STATUS ALVO")
        self.log("=" * 70)
        self.log(f"   • URL: {VOOS_URL}")
        self.log(f"   • Modo visual: {'DESATIVADO' if self.headless else 'ATIVADO'}")
        self.log(f"   • Máximo de cliques 'Carregar mais': {self.max_clicks}")
        status_msg = ", ".join(self.target_statuses[:3]) + ("..." if len(self.target_statuses) > 3 else "")
        self.log(f"   • Filtro: Status {status_msg}")
        self.log("")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                user_agent_selected = self._get_random_user_agent()
                context = browser.new_context(user_agent=user_agent_selected)
                page = context.new_page()
                
                # Economia de dados (bloqueio de imagens)
                def handle_route(route: Route):
                    url = route.request.url
                    if route.request.resource_type == "image" and any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        route.abort()
                    else:
                        route.continue_()
                
                page.route("**/*", handle_route)
                self.log("   ✅ Economia de dados ativada")
                self.log(f"   🔄 User-Agent: {user_agent_selected[:50]}...")
                
                try:
                    self.log("📡 Carregando página...")
                    page.goto(VOOS_URL, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
                    self.log("✅ Página carregada")
                    
                    # Wait explícito: aguarda elementos estarem visíveis
                    try:
                        page.wait_for_selector("div, :has-text('Detalhes')", timeout=ELEMENT_WAIT_TIMEOUT, state="attached")
                    except Exception:
                        pass
                    
                    page.wait_for_timeout(INITIAL_PAGE_WAIT)
                    
                    # ====================================================================
                    # FASE 1: CARREGAMENTO (ONLINE) - Carrega todas as páginas
                    # ====================================================================
                    self.log(f"\n{'='*70}")
                    self.log(f"📡 FASE 1: CARREGAMENTO (ONLINE)")
                    self.log(f"{'='*70}")
                    
                    clicks_performed = self._load_all_pages(page)
                    
                    self._scroll_to_render(page)
                    
                    # GARANTIA DE ALCANCE: Aguarda antes do modo offline
                    self.log(f"   ⏳ Aguardando {FINAL_RENDER_WAIT}ms OBRIGATÓRIOS para renderização completa (garantia de alcance)...")
                    page.wait_for_timeout(FINAL_RENDER_WAIT)
                    
                    # ====================================================================
                    # FASE 1.5: CONSULTA MCP PARA MELHORES PRÁTICAS (antes do congelamento)
                    # ====================================================================
                    if self.mcp_diagnostics:
                        self.log(f"\n{'='*70}")
                        self.log(f"🤖 CONSULTANDO MCP: Melhores Práticas Playwright")
                        self.log(f"{'='*70}")
                        try:
                            recommendations = self.mcp_diagnostics.ask_playwright_best_practices(VOOS_URL)
                            if recommendations and "recommendations" in recommendations:
                                self.log("   ✅ Recomendações MCP obtidas (verifique logs para detalhes)")
                                # TODO: Implementar uso das recomendações para ajustar waits dinamicamente
                        except Exception as e:
                            self.log_error(f"Erro ao consultar MCP: {e}")
                    
                    # ====================================================================
                    # FASE 2: CONGELAMENTO (OFFLINE) - Congela o DOM para evitar desalinhamento
                    # ====================================================================
                    self.log(f"\n{'='*70}")
                    self.log(f"❄️  FASE 2: CONGELAMENTO (OFFLINE)")
                    self.log(f"{'='*70}")
                    
                    # Aguarda última linha da tabela antes de congelar (se possível)
                    try:
                        # Tenta esperar por indicador de fim de carregamento
                        page.wait_for_timeout(1000)  # Espera adicional antes de congelar
                    except Exception:
                        pass
                    
                    self._freeze_dom(context)
                    page.wait_for_timeout(OFFLINE_STABILIZATION_WAIT)
                    self.log(f"   ✅ DOM estabilizado - extração pode começar sem risco de desalinhamento")
                    
                    # ====================================================================
                    # FASE 3: EXTRAÇÃO (SNAPSHOT ESTÁTICO) - Extrai com todas as Regras de Ouro
                    # ====================================================================
                    self.log(f"\n{'='*70}")
                    self.log(f"📊 FASE 3: EXTRAÇÃO (SNAPSHOT ESTÁTICO)")
                    self.log(f"{'='*70}")
                    self.log(f"   🔍 Extraindo voos com DOM congelado...")
                    self.log(f"   📋 Regras de Ouro Mantidas:")
                    self.log(f"      ✅ Identificação por Prefixo (TP, AA, LA, AD, G3, etc.)")
                    self.log(f"      ✅ Dicionário de Aeroportos (SSA→Salvador, FOR→Fortaleza, etc.)")
                    self.log(f"      ✅ Filtro de Status Flexível (Embarque Próximo, Imediato Embarque)")
                    self.log(f"      ✅ Consolidação de Codeshare (Parceiras)")
                    self.log("")
                    
                    # Extrai voos com DOM congelado
                    flights = self.processor.extract_from_snapshot(page)
                    status_msg = ", ".join(self.target_statuses[:2]) + ("..." if len(self.target_statuses) > 2 else "")
                    self.log(f"\n   ✅ {len(flights)} voo(s) extraído(s) com status alvo ({status_msg})")
                    
                    # ====================================================================
                    # FASE 4: FINALIZAÇÃO - Retorna ao modo online antes de encerrar
                    # ====================================================================
                    self.log(f"\n{'='*70}")
                    self.log(f"🔓 FASE 4: FINALIZAÇÃO")
                    self.log(f"{'='*70}")
                    self._unfreeze_dom(context)
                    
                    return flights
                
                except Exception as e:
                    error_msg = f"❌ Erro durante scraping: {e}"
                    self.log_error(error_msg)
                    if self.logger:
                        import traceback
                        self.logger.debug(traceback.format_exc())
                finally:
                    try:
                        if 'context' in locals():
                            self._unfreeze_dom(context)
                            context.close()
                        if 'browser' in locals():
                            browser.close()
                    except Exception:
                        pass
        
        except Exception as e:
            error_msg = f"❌ Erro fatal no scraping: {e}"
            self.log_error(error_msg)
            if self.logger:
                import traceback
                self.logger.debug(traceback.format_exc())
        
        return []
    
    def run(self) -> int:
        """
        Executes complete scraping and saves results to CSV.
        
        Performs operational disruption monitoring and generates timestamped reports.
        
        Returns:
            Number of flights saved to CSV
        """
        # Atualiza mensagem de log com status alvo
        status_msg = ", ".join(self.target_statuses[:3]) + ("..." if len(self.target_statuses) > 3 else "")
        self.log(f"   • Filtro: Status {status_msg}")
        
        # Executa scraping
        flights = self.scrape()
        
        if not flights:
            self.log(f"\n⚠️  Nenhum voo encontrado com os status alvo")
            return 0
        
        # Cria nome do arquivo CSV com configurações dinâmicas
        csv_file_path = self.processor.create_csv_filename(
            output_dir=self.output_dir,
            csv_prefix=self.csv_prefix
        )
        
        self.log(f"\n" + "=" * 70)
        self.log("💾 SALVANDO: Processando CSV (novo arquivo com timestamp)")
        self.log("=" * 70)
        
        # Salva voos em novo arquivo CSV
        flights_count = self.processor.save_to_csv(flights, csv_file_path)
        
        self.log(f"\n" + "=" * 70)
        self.log("📊 RESUMO FINAL")
        self.log("=" * 70)
        self.log(f"   • Total de voos encontrados: {len(flights)}")
        self.log(f"   • Voos salvos no CSV: {flights_count}")
        self.log(f"📄 Arquivo CSV: {csv_file_path}")
        self.log("=" * 70)
        self.log("✅ Scraping concluído!")
        self.log("=" * 70)
        
        return flights_count