#!/usr/bin/env python3
"""
Script de Sincronização - MatchFly PSEO
Versão: Blindada (Auto-Detect Separator + Explicit Mapping)
"""

import sys
import os
import requests
import pandas as pd
import json
import logging
import datetime
import io

# Configuração de Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
REMOTE_CSV_URL = "https://raw.githubusercontent.com/jonechelon/gru-flight-reliability-monitor/main/voos_atrasados_gru.csv"
FIXED_CSV_NAME = "voos_atrasados_gru.csv"
JSON_OUTPUT_PATH = "data/flights-db.json"

def main():
    logger.info("🚀 MATCHFLY - INICIANDO SINCRONIZAÇÃO BLINDADA")
    
    base_dir = os.getcwd()
    path_csv = os.path.join(base_dir, FIXED_CSV_NAME)
    path_json = os.path.join(base_dir, JSON_OUTPUT_PATH)
    
    # 1. Download
    try:
        logger.info(f"⬇️ Baixando CSV...")
        response = requests.get(REMOTE_CSV_URL, timeout=30)
        response.raise_for_status()
        
        # Salva o conteúdo cru para análise se precisar
        content = response.content
        with open(path_csv, 'wb') as f:
            f.write(content)
            
    except Exception as e:
        logger.error(f"🛑 Erro no download: {e}")
        sys.exit(1)

    # 2. Leitura Inteligente (Detecta ; ou ,)
    try:
        # Tenta ler com pandas detectando automaticamente, mas forçando engine python
        try:
            df = pd.read_csv(path_csv, sep=None, engine='python')
        except:
            # Fallback para ponto-e-vírgula explícito (comum no Brasil/Excel)
            logger.warning("⚠️ Falha na detecção automática. Tentando separador ';'")
            df = pd.read_csv(path_csv, sep=';')

        logger.info(f"📋 Colunas detectadas: {list(df.columns)}")
        
        # 3. Normalização de Nomes
        # Remove espaços e converte para minúsculo para facilitar o match
        df.columns = df.columns.str.strip().str.lower()
        
        # Mapa Explicito baseado no seu CSV (Numero_Voo -> flight_number)
        rename_map = {
            'numero_voo': 'flight_number',
            'numero': 'flight_number',
            'voo': 'flight_number',
            
            'companhia': 'airline',
            'operadora': 'airline',
            
            'status': 'status',
            'situacao': 'status',
            
            'origem': 'origin',
            
            # Caso não tenha destino, vamos inferir ou deixar vazio
            'destino': 'destination',
            
            'horario': 'scheduled_time',
            'hora_partida': 'scheduled_time'
        }
        
        # Aplica a renomeação
        df.rename(columns=rename_map, inplace=True)
        
        # Validação Pós-Renomeação
        logger.info(f"✅ Colunas após mapeamento: {list(df.columns)}")

        # Garante colunas obrigatórias
        if 'flight_number' not in df.columns:
            logger.error("🛑 ERRO CRÍTICO: Não encontrei a coluna do número do voo (Numero_Voo)!")
            # Tenta encontrar a coluna 'number' ou similar na força bruta
            for col in df.columns:
                if 'num' in col or 'voo' in col:
                    logger.info(f"🔧 Tentando usar '{col}' como flight_number de emergência")
                    df.rename(columns={col: 'flight_number'}, inplace=True)
                    break
        
        # Preenche valores vazios
        required = ['flight_number', 'airline', 'status']
        for col in required:
            if col not in df.columns:
                df[col] = "DESCONHECIDO"
            else:
                df[col] = df[col].fillna("DESCONHECIDO")

        # Garante ORIGEM (GRU por padrão se não vier)
        if 'origin' not in df.columns:
            df['origin'] = 'GRU'

        # Atualiza timestamp
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
            
        logger.info(f"✅ JSON gerado com sucesso: {path_json}")
        logger.info(f"📊 Total de voos processados: {len(flights_list)}")
        
    except Exception as e:
        logger.error(f"🛑 Erro no processamento: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()