import pandas as pd
import logging
import json
import os

def create_report_from_json(input_json_path: str, output_excel_path: str):
    """
    Lê os dados brutos de um arquivo JSON e gera a planilha Excel base
    com todas as abas.
    """
    logging.info(f"Lendo dados brutos do arquivo JSON: {input_json_path}")
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        logging.error(f"Arquivo de entrada JSON não encontrado: {input_json_path}")
        raise

    data_frames = {key: pd.DataFrame(value) for key, value in raw_data.items()}

    os.makedirs(os.path.dirname(output_excel_path), exist_ok=True)
    logging.info(f"Gerando relatório Excel base em: {output_excel_path}")
    
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        # Ordem definida das abas para melhor organização
        sheet_order = ['VPCs', 'Subnets', 'SecurityGroups', 'RouteTables', 'NetworkACLs', 'InternetGateways']
        for sheet_name in sheet_order:
            if sheet_name in data_frames and not data_frames[sheet_name].empty:
                data_frames[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)
    
    logging.info("Relatório Excel base gerado com sucesso.")