import pandas as pd
import logging
import json
import os
from ..utils import formatters

def create_report_from_json(input_json_path: str, output_excel_path: str):
    """
    Lê os dados brutos de um arquivo JSON, formata o texto e gera a
    planilha Excel base, salvando-a no caminho de saída.
    """
    logging.info(f"Lendo dados brutos do arquivo JSON: {os.path.basename(input_json_path)}")
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        logging.error(f"Arquivo de entrada JSON não encontrado: {input_json_path}")
        raise

    # Converte os dados de volta para DataFrames
    data_frames = {key: pd.DataFrame(value) for key, value in raw_data.items()}

    # Aplica formatadores de texto para melhorar a legibilidade
    logging.info("Formatando texto das células para o relatório...")
    for sheet_name, df in data_frames.items():
        if df.empty: continue
        for col in df.columns:
            if 'Tags' in col: df[col] = df[col].apply(formatters.format_tags)

    # Garante que o diretório de saída exista
    os.makedirs(os.path.dirname(output_excel_path), exist_ok=True)
    
    logging.info(f"Gerando relatório Excel base em: {os.path.basename(output_excel_path)}")
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        # Ordem definida das abas para melhor organização
        sheet_order = [
            'VPCs', 'Subnets', 'SecurityGroups', 
            'RouteTables', 'NetworkACLs', 'InternetGateways'
            # Adicione aqui outras abas principais se o coletor as gerar
        ]
        for sheet_name in sheet_order:
            if sheet_name in data_frames and not data_frames[sheet_name].empty:
                data_frames[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)

    logging.info("Relatório Excel base gerado com sucesso.")