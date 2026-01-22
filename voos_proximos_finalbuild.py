#!/usr/bin/env python3
"""
Script de Sincronização - MatchFly PSEO
Versão: DateTime Sort Fix (Combina Data + Hora para ordenação correta)
"""

import sys
import os
import requests
import pandas as pd
import json
import logging
import datetime

# Configuração de Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
REMOTE_CSV_URL = "https://raw.githubusercontent.com/jonechelon/gru-flight-reliability-monitor/main/voos_atrasados_gru.csv"
FIXED_CSV_NAME = "voos_atrasados_gru.csv"
JSON_OUTPUT_PATH = "data/flights-db.json"

def main():
    logger.info("🚀 MATCHFLY - SINCRONIZAÇÃO COM CORREÇÃO DE DATA/HORA")
    
    base_dir = os.getcwd()
    path_csv = os.path.join(base_dir, FIXED_CSV_NAME)
    path_json = os.path.join(base_dir, JSON_OUTPUT_PATH)
    
    # 1. Download
    try:
        logger.info(f"⬇️ Baixando CSV...")
        response = requests.get(REMOTE_CSV_URL, timeout=30)
        response.raise_for_status()
        with open(path_csv, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        logger.error(f"🛑 Erro no download: {e}")
        sys.exit(1)

    # 2. Leitura Inteligente
    try:
        # Tenta detectar separador automaticamente, fallback para ';'
        try:
            df = pd.read_csv(path_csv, sep=None, engine='python')
        except:
            df = pd.read_csv(path_csv, sep=';')

        # Normaliza colunas
        df.columns = df.columns.str.strip().str.lower()
        logger.info(f"📋 Colunas detectadas: {list(df.columns)}")
        
        # --- CORREÇÃO CRÍTICA DE DATA/HORA ---
        # Tenta encontrar colunas de data e hora para combinar
        col_date = next((c for c in df.columns if 'data_partida' in c), None)
        if not col_date:
            col_date = next((c for c in df.columns if 'data_captura' in c), None)
            
        col_time = next((c for c in df.columns if 'hora_partida' in c), None)
        if not col_time:
            col_time = next((c for c in df.columns if 'horario' in c), None)
            
        # Função para criar timestamp completo ISO (YYYY-MM-DD HH:MM)
        def make_iso_timestamp(row):
            try:
                d_str = str(row[col_date]).strip()
                t_str = str(row[col_time]).strip()
                
                # Trata data DD/MM (ex: 21/01) -> assume 2026
                if len(d_str) <= 5 and '/' in d_str:
                    parts = d_str.split('/')
                    d_iso = f"2026-{parts[1]}-{parts[0]}"
                # Trata data YYYY-MM-DD
                else:
                    d_iso = d_str
                
                return f"{d_iso} {t_str}"
            except:
                return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # Se achou as colunas, cria o campo combinado
        if col_date and col_time:
            logger.info(f"🕒 Combinando colunas '{col_date}' + '{col_time}' para ordenação...")
            df['scheduled_time_iso'] = df.apply(make_iso_timestamp, axis=1)
        else:
            logger.warning("⚠️ Colunas de data/hora não encontradas para combinação.")
            df['scheduled_time_iso'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # 3. Mapeamento de Colunas (Atualizado para usar o campo ISO)
        rename_map = {
            'numero_voo': 'flight_number',
            'numero': 'flight_number',
            'voo': 'flight_number',
            'companhia': 'airline',
            'operadora': 'airline',
            'status': 'status',
            'situacao': 'status',
            'origem': 'origin',
            'destino': 'destination',
            
            # AGORA MAPEAMOS O CAMPO NOVO PARA SER O OFICIAL DE TEMPO
            'scheduled_time_iso': 'scheduled_time'
        }
        
        df.rename(columns=rename_map, inplace=True)
        
        # Garante colunas obrigatórias
        if 'flight_number' not in df.columns:
            # Fallback de emergência
            for col in df.columns:
                if 'num' in col: 
                    df.rename(columns={col: 'flight_number'}, inplace=True)
                    break
        
        required = ['flight_number', 'airline', 'status']
        for col in required:
            if col not in df.columns:
                df[col] = "DESCONHECIDO"
            else:
                df[col] = df[col].fillna("DESCONHECIDO")
                
        if 'origin' not in df.columns: df['origin'] = 'GRU'

        # Exporta
        flights_list = df.to_dict(orient='records')
        final_structure = {
            "flights": flights_list,
            "metadata": {
                "generated_at": datetime.datetime.now().isoformat(),
                "count": len(flights_list)
            }
        }
        
        os.makedirs(os.path.dirname(path_json), exist_ok=True)
        with open(path_json, 'w', encoding='utf-8') as f:
            json.dump(final_structure, f, indent=2, ensure_ascii=False)
            
        logger.info(f"✅ JSON gerado com {len(flights_list)} voos.")

    except Exception as e:
        logger.error(f"🛑 Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()