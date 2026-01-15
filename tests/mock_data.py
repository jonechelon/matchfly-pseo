# Casos reais conforme FASE 3 - Operação Resgate v2.0
REAL_MOCK_STRINGS = {
    "BOGOTA_CASE": "01:20 Bogotá 0248 Terminal 2 01:20 Última Chamada",  # Deve ser AVIANCA
    "A6509_CASE": "05:45 05:45 A6509 Última Chamada Detalhes",          # Deve aceitar Destino N/A
    "ORPHAN_7586": "06:30 06:30 7586 Embarque Próximo Detalhes"          # Deve aceitar Destino N/A
}

MOCK_SCENARIOS = {
    "CASE_1_BOGOTA_AVIANCA": {
        "raw_text": "AVIANCA A6509 BOGOTA 01:25",
        "expected": {"Voo": "A6509", "Companhia": "AVIANCA", "Destino": "BOGOTA"}
    },
    "CASE_2_ONE_LETTER_PREFIX": {
        "raw_text": "GOL G7586 RIO DE JANEIRO 02:10",
        "expected": {"Voo": "G7586", "Companhia": "GOL", "Destino": "RIO DE JANEIRO"}
    }
}

MOCK_FLIGHT_DATA = {
    "A6509": {
        "row_text": "AVIANCA A6509 BOGOTA 01:25",
        "expected": {"Voo": "A6509", "Companhia": "AVIANCA"}
    }
}

REAL_ROW_TEXTS = []

"""
Mock data para testes de extração de voos problemáticos.
Inclui strings reais coletadas dos logs para validação offline.
Estes são os textos reais que falharam nas últimas 5 horas.
"""

# Mock data para voos problemáticos identificados
MOCK_FLIGHT_DATA = {
    "A6509": {
        "row_text": "05:45 05:45 A6509 Última Chamada Detalhes",
        "expected": {
            "Horario_Previsto": "05:45",
            "Horario_Estimado": "05:45",
            "Voo": "6509",
            "Voo_Prefixo": "A",
            "Companhia": "AVIANCA",  # Esperado via MCP ou fallback
            "Destino": "BOG",  # Bogotá
            "Status": "Última Chamada"
        }
    },
    "7586": {
        "row_text": "06:30 06:30 7586 Embarque Próximo Detalhes",
        "expected": {
            "Horario_Previsto": "06:30",
            "Horario_Estimado": "06:30",
            "Voo": "7586",
            "Voo_Prefixo": None,
            "Companhia": "LATAM",  # Esperado por faixa numérica
            "Destino": "N/A",  # Precisa ser identificado
            "Status": "Embarque Próximo"
        }
    },
    "7484": {
        "row_text": "07:15 07:15 7484 Embarque Próximo Detalhes",
        "expected": {
            "Horario_Previsto": "07:15",
            "Horario_Estimado": "07:15",
            "Voo": "7484",
            "Voo_Prefixo": None,
            "Companhia": "LATAM",  # Esperado por faixa numérica
            "Destino": "N/A",  # Precisa ser identificado
            "Status": "Embarque Próximo"
        }
    },
    "Bogota_Emirates": {
        "row_text": "05:45 05:45 0215 EMIRATES Santiag Última Chamada Detalhes",
        "expected": {
            "Horario_Previsto": "05:45",
            "Horario_Estimado": "05:45",
            "Voo": "0215",
            "Voo_Prefixo": None,
            "Companhia": "EMIRATES",
            "Destino": "BOG",  # Bogotá (Santiag = Santiago/Bogotá)
            "Status": "Última Chamada"
        }
    }
}

# Casos de teste EXATOS do checklist consolidado
MOCK_SCENARIOS = {
    "CASE_1_BOGOTA_AVIANCA": {
        "raw_text": "01:20 Bogotá 0248 Terminal 2 01:20 Última Chamada Detalhes",
        "expected": {"Voo": "0248", "Companhia": "AVIANCA", "Destino": "Bogotá"}
    },
    "CASE_2_ONE_LETTER_PREFIX": {
        "raw_text": "05:45 05:45 A6509 Última Chamada Detalhes",
        "expected": {"Voo": "A6509", "Destino": "N/A", "Status": "Última Chamada"} 
    },
    "CASE_3_ORPHAN_NUMBER_DISTANT": {
        "raw_text": "06:30 06:30 7586 Embarque Próximo Detalhes Mais Informações",
        "expected": {"Voo": "7586", "Status": "Embarque Próximo"}
    },
    "CASE_4_TERMINAL_CONFUSION": {
        "raw_text": "01:00 Santiago 8038 Terminal 3 01:00 Imediato Embarque",
        "expected": {"Voo": "8038", "Companhia": "LATAM", "Terminal": "3"}
    }
}

# Strings reais coletadas dos logs (para validação)
REAL_ROW_TEXTS = [
    "05:45 05:45 0215 EMIRATES Santiag Última Chamada Detalhes",
    "06:30 06:30 7586 Embarque Próximo Detalhes",
    "07:15 07:15 7484 Embarque Próximo Detalhes",
    "05:45 05:45 A6509 Última Chamada Detalhes",
]

# Strings reais dos logs com contexto completo (para validação de isolamento atômico)
REAL_ROW_TEXTS_WITH_CONTEXT = [
    # Voo 7586 - contexto real do log
    "06:00 Brasília 3607 Terminal 2 06:00 Última Chamada Detalhes 06:00 Belo Horizonte 7202 Terminal 1 06:00 Última Chamada Detalhes 06:30 06:30 7586 Embarque Próximo Detalhes",
    
    # Voo 7484 - contexto real do log
    "07:15 07:15 7484 Embarque Próximo Detalhes",
    
    # Voo A6509 - contexto real do log
    "05:45 05:45 A6509 Última Chamada Detalhes",
    
    # Voo para Santiago/Bogotá (caso especial)
    "05:45 Santiago 0215 Terminal 3 05:45 Voo encerrado Detalhes 05:55 Santiago 8168 Terminal 3 05:55 Embarque Imediato Detalhes",
]
