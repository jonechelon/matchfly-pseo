#!/usr/bin/env python3
"""
GRU Airport Flight Disruption Monitor
=====================================

Operational analytics tool for tracking flight schedule disruptions and anomalies.
Monitors IROPS (Irregular Operations) for operational stability analysis.

Features:
1. Tracks operational disruptions: Cancelled, Delayed, Postponed flights
2. Generates timestamped CSV reports in logs_operational_metrics/
3. Rotating User-Agent to avoid blocking
4. Professional error handling and logging
5. Dynamic status target configuration

REQUIREMENTS:
- Playwright installed: pip install playwright && playwright install chromium
- pandas installed: pip install pandas
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scrapers.gru_proximos.scraper_engine import ScraperEngine
from src.scrapers.gru_proximos.logger_config import setup_logger
from src.scrapers.gru_proximos.config import (
    STATUS_OPERATIONAL_DISRUPTIONS, DIR_LOGS_OPERATIONAL_METRICS, CSV_PREFIX_OPERATIONAL_REPORT,
    MAX_LOAD_MORE_CLICKS, DEFAULT_HEADLESS
)


def main():
    """
    Main function for operational disruption monitoring.
    """
    # Create operational metrics logging directory
    os.makedirs(DIR_LOGS_OPERATIONAL_METRICS, exist_ok=True)
    
    # Setup professional logging
    logger = setup_logger()
    
    logger.info("=" * 70)
    logger.info("📡 STARTING GRU FLIGHT DISRUPTION MONITOR")
    logger.info("=" * 70)
    logger.info(f"🎯 Target: Operational Anomalies Tracking (IROPS)")
    logger.info(f"📊 Monitoring Status: {STATUS_OPERATIONAL_DISRUPTIONS}")
    logger.info(f"📂 Output Directory: {os.path.abspath(DIR_LOGS_OPERATIONAL_METRICS)}")
    logger.info("")
    
    # Initialize scraper focused on operational disruptions
    scraper = ScraperEngine(
        headless=DEFAULT_HEADLESS,
        max_clicks=MAX_LOAD_MORE_CLICKS,
        logger=logger,
        enable_mcp=False,  # Disable MCP for faster execution
        target_statuses=STATUS_OPERATIONAL_DISRUPTIONS,
        output_dir=DIR_LOGS_OPERATIONAL_METRICS,
        csv_prefix=CSV_PREFIX_OPERATIONAL_REPORT
    )
    
    # Execute scraping and save CSV
    flights_count = scraper.run()
    
    if flights_count == 0:
        logger.warning("\n⚠️  No flights with operational disruption status found.")
        logger.info("   💡 Tip: To test, temporarily add 'Confirmado' to STATUS_OPERATIONAL_DISRUPTIONS list")
    else:
        logger.info(f"\n✅ {flights_count} flight(s) with operational disruptions captured for analysis!")


if __name__ == "__main__":
    main()
# Force Update
