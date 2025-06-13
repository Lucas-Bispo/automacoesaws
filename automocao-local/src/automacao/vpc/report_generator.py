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
    data_frames['Security_Analysis'] = security_findings_df

    # Aplica formatadores de texto para melhorar a legibilidade ANTES de escrever no Excel
    # Esta etapa converte listas de dicionários em strings formatadas com quebra de linha
    for sheet_name, df in data_frames.items():
        if df.empty:
            continue
            
        logging.debug(f"Formatando texto para a aba: {sheet_name}")
        # Aplica formatadores com base no nome da coluna
        for col in df.columns:
            if 'Tags' in col:
                df[col] = df[col].apply(formatters.format_tags)
            # Adicione aqui outras chamadas de apply se tiver mais formatadores
    
    # Gera o workbook em memória
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Define a ordem final das abas para melhor organização
        sheet_order = [
            'Security_Analysis', 'VPCs', 'Subnets', 'SecurityGroups', 
            'RouteTables', 'NetworkACLs', 'InternetGateways'
            # Adicione aqui outras abas principais que seu coletor gerar
        ]
        
        # Escreve cada DataFrame na sua aba, na ordem definida
        for sheet_name in sheet_order:
            if sheet_name in data_frames and not data_frames[sheet_name].empty:
                df_to_write = data_frames[sheet_name]
                df_to_write.to_excel(writer, sheet_name=sheet_name, index=False)

    # Carrega o workbook a partir do buffer em memória para ser passado adiante
    workbook = load_workbook(buffer)
    logging.info("Relatório base em memória gerado com sucesso.")
    return workbook