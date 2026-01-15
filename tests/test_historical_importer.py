#!/usr/bin/env python3
"""
Testes para o Historical Importer
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from historical_importer import ANACHistoricalImporter, AIRLINE_MAPPING


class TestAirlineMapping:
    """Testa o mapeamento de companhias aéreas."""
    
    def test_brazilian_airlines(self):
        """Testa companhias brasileiras."""
        assert AIRLINE_MAPPING['G3'] == 'GOL'
        assert AIRLINE_MAPPING['AD'] == 'AZUL'
        assert AIRLINE_MAPPING['LA'] == 'LATAM'
    
    def test_international_airlines(self):
        """Testa companhias internacionais."""
        assert AIRLINE_MAPPING['AF'] == 'Air France'
        assert AIRLINE_MAPPING['KL'] == 'KLM'
        assert AIRLINE_MAPPING['AA'] == 'American Airlines'
    
    def test_mapping_completeness(self):
        """Testa se o dicionário tem entradas suficientes."""
        assert len(AIRLINE_MAPPING) >= 20  # Mínimo esperado


class TestDateTimeParsing:
    """Testa parsing de datas e horas."""
    
    @pytest.fixture
    def importer(self):
        """Cria instância do importer para testes."""
        return ANACHistoricalImporter()
    
    def test_parse_datetime_ddmmyyyy(self, importer):
        """Testa formato DD/MM/YYYY HH:MM."""
        dt = importer.parse_datetime('15/12/2025', '14:30')
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 12
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30
    
    def test_parse_datetime_iso(self, importer):
        """Testa formato ISO YYYY-MM-DD HH:MM."""
        dt = importer.parse_datetime('2025-12-15', '14:30')
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 12
        assert dt.day == 15
    
    def test_parse_datetime_with_seconds(self, importer):
        """Testa formato com segundos HH:MM:SS."""
        dt = importer.parse_datetime('15/12/2025', '14:30:45')
        assert dt is not None
        assert dt.hour == 14
        assert dt.minute == 30
    
    def test_parse_datetime_invalid(self, importer):
        """Testa entrada inválida."""
        dt = importer.parse_datetime('invalid', 'invalid')
        assert dt is None
    
    def test_parse_datetime_whitespace(self, importer):
        """Testa entrada com espaços."""
        dt = importer.parse_datetime('  15/12/2025  ', '  14:30  ')
        assert dt is not None
        assert dt.day == 15


class TestDelayCalculation:
    """Testa cálculo de atrasos."""
    
    @pytest.fixture
    def importer(self):
        """Cria instância do importer para testes."""
        return ANACHistoricalImporter()
    
    def test_calculate_delay_positive(self, importer):
        """Testa atraso positivo."""
        scheduled = datetime(2025, 12, 15, 14, 0)
        actual = datetime(2025, 12, 15, 15, 30)
        delay = importer.calculate_delay(scheduled, actual)
        assert delay == 90  # 1h30min = 90 minutos
    
    def test_calculate_delay_negative(self, importer):
        """Testa adiantamento (atraso negativo)."""
        scheduled = datetime(2025, 12, 15, 14, 0)
        actual = datetime(2025, 12, 15, 13, 45)
        delay = importer.calculate_delay(scheduled, actual)
        assert delay == -15  # Adiantou 15 minutos
    
    def test_calculate_delay_zero(self, importer):
        """Testa pontualidade (sem atraso)."""
        scheduled = datetime(2025, 12, 15, 14, 0)
        actual = datetime(2025, 12, 15, 14, 0)
        delay = importer.calculate_delay(scheduled, actual)
        assert delay == 0


class TestFlightIDGeneration:
    """Testa geração de IDs únicos para voos."""
    
    @pytest.fixture
    def importer(self):
        """Cria instância do importer para testes."""
        return ANACHistoricalImporter()
    
    def test_flight_id_unique(self, importer):
        """Testa que IDs diferentes são gerados para voos diferentes."""
        flight1 = {
            'airline': 'GOL',
            'flight_number': '1234',
            'scheduled_date': '2025-12-15'
        }
        flight2 = {
            'airline': 'AZUL',
            'flight_number': '5678',
            'scheduled_date': '2025-12-16'
        }
        
        id1 = importer._get_flight_id(flight1)
        id2 = importer._get_flight_id(flight2)
        
        assert id1 != id2
    
    def test_flight_id_same(self, importer):
        """Testa que IDs iguais são gerados para voos idênticos."""
        flight1 = {
            'airline': 'GOL',
            'flight_number': '1234',
            'scheduled_date': '2025-12-15'
        }
        flight2 = {
            'airline': 'GOL',
            'flight_number': '1234',
            'scheduled_date': '2025-12-15'
        }
        
        id1 = importer._get_flight_id(flight1)
        id2 = importer._get_flight_id(flight2)
        
        assert id1 == id2
    
    def test_flight_id_case_insensitive(self, importer):
        """Testa que IDs são case-insensitive."""
        flight1 = {
            'airline': 'GOL',
            'flight_number': '1234',
            'scheduled_date': '2025-12-15'
        }
        flight2 = {
            'airline': 'gol',
            'flight_number': '1234',
            'scheduled_date': '2025-12-15'
        }
        
        id1 = importer._get_flight_id(flight1)
        id2 = importer._get_flight_id(flight2)
        
        assert id1 == id2


class TestColumnNormalization:
    """Testa normalização de nomes de colunas."""
    
    @pytest.fixture
    def importer(self):
        """Cria instância do importer para testes."""
        return ANACHistoricalImporter()
    
    def test_normalize_accent_removal(self, importer):
        """Testa remoção de acentos."""
        normalized = importer._normalize_column_name('Número do Vôo')
        assert 'numero' in normalized
        assert 'voo' in normalized
        # Não deve ter acentos
        assert 'ú' not in normalized
        assert 'ô' not in normalized
    
    def test_normalize_lowercase(self, importer):
        """Testa conversão para lowercase."""
        normalized = importer._normalize_column_name('NUMERO VOO')
        assert normalized == normalized.lower()
    
    def test_normalize_spaces_to_underscores(self, importer):
        """Testa conversão de espaços para underscores."""
        normalized = importer._normalize_column_name('Numero do Voo')
        assert ' ' not in normalized
        assert '_' in normalized
    
    def test_normalize_special_chars(self, importer):
        """Testa remoção de caracteres especiais."""
        normalized = importer._normalize_column_name('Número (Voo)')
        assert '(' not in normalized
        assert ')' not in normalized


class TestANACDownloadURLs:
    """Testa geração de URLs de download."""
    
    @pytest.fixture
    def importer(self):
        """Cria instância do importer para testes."""
        return ANACHistoricalImporter()
    
    def test_get_anac_urls_returns_list(self, importer):
        """Testa que retorna lista."""
        urls = importer.get_anac_download_urls()
        assert isinstance(urls, list)
        assert len(urls) > 0
    
    def test_get_anac_urls_format(self, importer):
        """Testa formato das URLs."""
        urls = importer.get_anac_download_urls()
        
        for url in urls:
            assert url.startswith('https://')
            assert 'anac.gov.br' in url
            assert 'VRA' in url
            assert '.csv' in url


class TestIntegration:
    """Testes de integração."""
    
    def test_importer_initialization(self):
        """Testa inicialização do importer."""
        importer = ANACHistoricalImporter(
            output_file='test_output.json',
            airport_code='SBGR',
            min_delay_minutes=15,
            days_lookback=30
        )
        
        assert importer.output_file.name == 'test_output.json'
        assert importer.airport_code == 'SBGR'
        assert importer.min_delay_minutes == 15
        assert importer.days_lookback == 30
    
    def test_stats_initialization(self):
        """Testa que estatísticas são inicializadas."""
        importer = ANACHistoricalImporter()
        
        assert 'downloaded_files' in importer.stats
        assert 'total_rows' in importer.stats
        assert 'filtered_sbgr' in importer.stats
        assert 'delayed_flights' in importer.stats
        assert 'imported' in importer.stats
        assert 'duplicates' in importer.stats
        assert 'errors' in importer.stats
        
        # Todos devem iniciar em 0
        for value in importer.stats.values():
            assert value == 0


class TestColumnIdentification:
    """Testa identificação de colunas do CSV."""
    
    @pytest.fixture
    def importer(self):
        """Cria instância do importer para testes."""
        return ANACHistoricalImporter()
    
    def test_identify_columns_basic(self, importer):
        """Testa identificação com nomes padrão."""
        columns = [
            'sigla_empresa',
            'numero_voo',
            'aeroporto_origem',
            'aeroporto_destino',
            'data_partida_prevista',
            'hora_partida_prevista'
        ]
        
        mapping = importer._identify_columns(columns)
        
        assert 'airline_code' in mapping
        assert 'flight_number' in mapping
        assert 'origin' in mapping
        assert 'destination' in mapping
    
    def test_identify_columns_variations(self, importer):
        """Testa identificação com variações de nomes."""
        columns = [
            'icao_empresa',
            'voo',
            'origem',
            'destino',
            'data_prevista',
            'hora_prevista'
        ]
        
        mapping = importer._identify_columns(columns)
        
        assert 'airline_code' in mapping
        assert 'flight_number' in mapping
        assert 'origin' in mapping
        assert 'destination' in mapping


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
