import pandas as pd
import logging
import json
import os
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

HIGH_RISK_PORTS = {22, 3389, 3306, 5432, 1433, 27017}
ACCEPTABLE_PUBLIC_PORTS = {80, 443}
ANYWHERE_CIDR = '0.0.0.0/0'

def analyze_sgs(sg_dataframe: pd.DataFrame):
    # (A função que analisa e retorna 'findings_df, sg_risk_map' permanece a mesma)
    pass

def analyze_and_update_report(input_path: str, output_path: str, json_path: str):
    logging.info(f"Analisando segurança a partir de: {os.path.basename(json_path)}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f: raw_data = json.load(f)
        sg_df_raw = pd.DataFrame(raw_data.get('SecurityGroups', []))
        findings_df, sg_risk_map = analyze_sgs(sg_dataframe=sg_df_raw)
        
        workbook = load_workbook(input_path)
        if 'Security_Analysis' in workbook.sheetnames: del workbook['Security_Analysis']
        analysis_sheet = workbook.create_sheet('Security_Analysis', 0)
        
        for r in dataframe_to_rows(findings_df, index=False, header=True):
            analysis_sheet.append(r)
        
        workbook.save(output_path)
        logging.info(f"Relatório analisado salvo em: {os.path.basename(output_path)}")
        return sg_risk_map
    except FileNotFoundError:
        logging.error(f"Arquivo não encontrado: {input_path} ou {json_path}"); raise