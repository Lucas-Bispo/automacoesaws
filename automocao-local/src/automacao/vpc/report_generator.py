import pandas as pd
import logging
import io
from openpyxl import load_workbook
from ..utils import formatters

def create_report(data_frames: dict, security_findings_df: pd.DataFrame):
    """
    Cria um relatório em memória, formatando os dados de texto e incluindo a 
    aba de análise de segurança. Retorna o objeto workbook do openpyxl.
    """
    logging.info("Formatando texto e criando estrutura do relatório em memória...")
    
    # Adiciona a aba de análise de segurança ao pacote de dados para ser escrita
    data_frames['Security_Analysis'] = security_findings_df

    # Aplica formatadores de texto para melhorar a legibilidade ANTES de escrever no Excel
    if 'VPCs' in data_frames and not data_frames['VPCs'].empty:
        df = data_frames['VPCs']
        if 'Tags' in df.columns: df['Tags'] = df['Tags'].apply(formatters.format_tags)
    
    if 'SecurityGroups' in data_frames and not data_frames['SecurityGroups'].empty:
        df = data_frames['SecurityGroups']
        # Usamos uma cópia para a formatação de texto, pois a análise precisa dos dados brutos
        df_formatted = df.copy()
        if 'IpPermissions' in df.columns: df_formatted['IpPermissions'] = df_formatted['IpPermissions'].apply(formatters.format_rules)
        if 'IpPermissionsEgress' in df.columns: df_formatted['IpPermissionsEgress'] = df_formatted['IpPermissionsEgress'].apply(formatters.format_rules)
        data_frames['SecurityGroups_Formatted'] = df_formatted # Usaremos esta para a aba principal

    if 'RouteTables' in data_frames and not data_frames['RouteTables'].empty:
        df = data_frames['RouteTables']
        if 'Associations' in df.columns: df['Associations'] = df['Associations'].apply(formatters.format_associations)
        if 'Routes' in df.columns: df['Routes'] = df['Routes'].apply(formatters.format_routes)
        
    # Gera o workbook em memória
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Ordem definida das abas para melhor organização
        sheet_order = [
            'Security_Analysis', 'VPCs', 'Subnets', 'SecurityGroups_Formatted', 
            'RouteTables', 'NetworkACLs', 'InternetGateways'
        ]
        
        for sheet_name in sheet_order:
            df_key = sheet_name.replace('_Formatted', '') # Acha o DataFrame original
            if df_key in data_frames and not data_frames[df_key].empty:
                # Usa o DataFrame formatado se existir, senão o original
                df_to_write = data_frames.get(sheet_name, data_frames[df_key])
                df_to_write.to_excel(writer, sheet_name=sheet_name.replace('_Formatted', ''), index=False)

    workbook = load_workbook(buffer)
    logging.info("Relatório base em memória gerado com sucesso.")
    return workbook