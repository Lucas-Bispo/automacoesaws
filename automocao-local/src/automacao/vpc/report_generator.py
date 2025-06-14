import pandas as pd
import logging
import json
import os
from ..utils import formatters

def create_report_from_json(input_json_path: str, output_excel_path: str):
    logging.info(f"Lendo dados do JSON: {os.path.basename(input_json_path)}")
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f: raw_data = json.load(f)
    except FileNotFoundError:
        logging.error(f"Arquivo JSON não encontrado: {input_json_path}"); raise

    data_frames = {key: pd.DataFrame(value) for key, value in raw_data.items()}
    logging.info("Formatando texto das células para o relatório...")
    if 'SecurityGroups' in data_frames and not data_frames['SecurityGroups'].empty:
        df_sg = data_frames['SecurityGroups']
        # Cria cópias formatadas das colunas de regras
        df_sg['InboundRules_Formatted'] = df_sg['IpPermissions'].apply(formatters.format_rules)
        df_sg['OutboundRules_Formatted'] = df_sg['IpPermissionsEgress'].apply(formatters.format_rules)
    
    os.makedirs(os.path.dirname(output_excel_path), exist_ok=True)
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        for sheet_name, df in data_frames.items():
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    logging.info(f"Relatório Excel base gerado: {os.path.basename(output_excel_path)}")