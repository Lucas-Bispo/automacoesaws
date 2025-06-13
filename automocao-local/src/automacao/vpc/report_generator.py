import pandas as pd
import logging
import io
from openpyxl import load_workbook
from ..utils import formatters

def create_report(data_frames: dict, security_findings_df: pd.DataFrame):
    """
    Recebe os DataFrames brutos e os de análise, formata os textos
    e cria um workbook Excel em memória com todas as abas.
    """
    logging.info("Formatando dados de texto e criando estrutura do relatório em memória...")
    
    # Adiciona a aba de análise de segurança ao pacote de dados para ser escrita
    if not security_findings_df.empty:
        data_frames['Security_Analysis'] = security_findings_df

    # Aplica formatadores de texto para melhorar a legibilidade ANTES de escrever no Excel
    if 'VPCs' in data_frames and not data_frames['VPCs'].empty:
        df = data_frames['VPCs']
        if 'Tags' in df.columns: df['Tags'] = df['Tags'].apply(formatters.format_tags)
    
    if 'SecurityGroups' in data_frames and not data_frames['SecurityGroups'].empty:
        # A formatação de texto para SGs agora é feita no 'final_formatter'
        # para preservar os dados brutos para os hyperlinks.
        # Aqui, apenas renomeamos as colunas para o relatório final.
        df = data_frames['SecurityGroups']
        df.rename(columns={'IpPermissions': 'Inbound Rules', 'IpPermissionsEgress': 'Outbound Rules'}, inplace=True, errors='ignore')

    if 'RouteTables' in data_frames and not data_frames['RouteTables'].empty:
        df = data_frames['RouteTables']
        if 'Associations' in df.columns: df['Associations'] = df['Associations'].apply(formatters.format_associations)
        if 'Routes' in df.columns: df['Routes'] = df['Routes'].apply(formatters.format_routes)
    
    # Gera o workbook em memória
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Ordem definida das abas para melhor organização
        sheet_order = [
            'Security_Analysis', 'VPCs', 'Subnets', 'SecurityGroups', 
            'RouteTables', 'NetworkACLs', 'InternetGateways'
        ]
        
        for sheet_name in sheet_order:
            if sheet_name in data_frames and not data_frames[sheet_name].empty:
                data_frames[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)

    # Carrega o workbook a partir do buffer em memória
    workbook = load_workbook(buffer)
    logging.info("Relatório base em memória gerado com sucesso.")
    
    # --- A LINHA CRÍTICA QUE FALTAVA ---
    return workbook