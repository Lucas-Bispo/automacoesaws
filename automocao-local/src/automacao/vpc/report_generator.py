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
        df_sg_formatted = df_sg.copy()
        df_sg_formatted.rename(columns={'IpPermissions': 'Inbound Rules', 'IpPermissionsEgress': 'Outbound Rules'}, inplace=True, errors='ignore')
        if 'Inbound Rules' in df_sg_formatted.columns:
            df_sg_formatted['Inbound Rules'] = df_sg_formatted['Inbound Rules'].apply(formatters.format_rules)
        if 'Outbound Rules' in df_sg_formatted.columns:
            df_sg_formatted['Outbound Rules'] = df_sg_formatted['Outbound Rules'].apply(formatters.format_rules)
        data_frames['SecurityGroups'] = df_sg_formatted
    
    os.makedirs(os.path.dirname(output_excel_path), exist_ok=True)
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        sheet_order = ['VPCs', 'Subnets', 'SecurityGroups', 'RouteTables']
        for sheet_name in sheet_order:
            if sheet_name in data_frames and not data_frames[sheet_name].empty:
                data_frames[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)
    
    logging.info(f"Relatório Excel base gerado: {os.path.basename(output_excel_path)}")