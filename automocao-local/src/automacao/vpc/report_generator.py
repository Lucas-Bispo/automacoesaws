import pandas as pd
import logging
import json
import os
import io
from openpyxl import load_workbook
from ..utils import formatters

def create_report(data_frames: dict, security_findings_df: pd.DataFrame):
    """
    Cria um relatório em memória, formatando os dados de texto
    e incluindo a aba de análise de segurança.
    """
    logging.info("Formatando texto e criando estrutura do relatório em memória...")
    
    # Adiciona a aba de análise de segurança ao pacote de dados para ser escrita
    data_frames['Security_Analysis'] = security_findings_df

    # Aplica formatadores de texto para criar as células de resumo
    if 'SecurityGroups' in data_frames and not data_frames['SecurityGroups'].empty:
        df_sg = data_frames['SecurityGroups']
        # Cria uma cópia para a formatação, mantendo os dados brutos no DF original
        df_sg_formatted = df_sg.copy()
        # Renomeia as colunas para o nome final desejado na planilha
        df_sg_formatted.rename(columns={'IpPermissions': 'Inbound Rules', 'IpPermissionsEgress': 'Outbound Rules'}, inplace=True, errors='ignore')
        if 'Inbound Rules' in df_sg_formatted.columns:
            df_sg_formatted['Inbound Rules'] = df_sg_formatted['Inbound Rules'].apply(formatters.format_rules)
        if 'Outbound Rules' in df_sg_formatted.columns:
            df_sg_formatted['Outbound Rules'] = df_sg_formatted['Outbound Rules'].apply(formatters.format_rules)
        # Substitui o DataFrame no pacote com a versão formatada para escrita
        data_frames['SecurityGroups'] = df_sg_formatted
    
    # Gera o workbook em memória
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        sheet_order = ['Security_Analysis', 'VPCs', 'Subnets', 'SecurityGroups', 'RouteTables']
        for sheet_name in sheet_order:
            if sheet_name in data_frames and not data_frames[sheet_name].empty:
                data_frames[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)

    workbook = load_workbook(buffer)
    logging.info("Relatório base em memória gerado com sucesso.")
    return workbook