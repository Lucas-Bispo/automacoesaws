import pandas as pd
import logging
import io
from openpyxl import load_workbook
from ..utils import formatters

def create_report(data_frames: dict, security_findings_df: pd.DataFrame):
    """
    Cria um relatório em memória para o serviço VPC, incluindo todas as abas de recursos e mapeamentos.
    """
    logging.info("Formatando dados de texto e criando estrutura do relatório em memória...")
    
    # Adiciona a aba de análise de segurança ao pacote de dados
    data_frames['Security_Analysis'] = security_findings_df

    # Aplica formatadores de texto (se necessário)
    for sheet_name, df in data_frames.items():
        if df.empty: continue
        for col in df.columns:
            if 'Tags' in col: df[col] = df[col].apply(formatters.format_tags)
    
    # Gera o workbook em memória
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Define a ordem final das abas
        sheet_order = [
            'Security_Analysis', 'VPCs', 'Subnets', 'SecurityGroups', 
            'RouteTables', 'NetworkACLs', 'InternetGateways',
            'MAP_VPC_x_SG', 'MAP_Subnet_x_RT'
        ]
        for sheet_name in sheet_order:
            if sheet_name in data_frames and not data_frames[sheet_name].empty:
                data_frames[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)

    workbook = load_workbook(buffer)
    logging.info("Relatório bruto em memória gerado com sucesso.")
    return workbook