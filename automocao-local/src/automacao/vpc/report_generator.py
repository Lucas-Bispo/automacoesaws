import pandas as pd
import logging
import json
import os
from ..utils import formatters

def create_report_from_json(input_json_path: str, output_excel_path: str):
    """
    Lê os dados brutos de um arquivo JSON, aplica formatação de texto para criar
    células de resumo e gera a planilha Excel base.
    """
    logging.info(f"Lendo dados do JSON: {os.path.basename(input_json_path)}")
    try:
        # Abre o arquivo JSON de entrada e carrega os dados
        with open(input_json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        # Se o arquivo de entrada não for encontrado, lança um erro
        logging.error(f"Arquivo de entrada JSON não encontrado: {input_json_path}")
        raise

    # Converte os dados carregados do JSON de volta para DataFrames do Pandas
    data_frames = {key: pd.DataFrame(value) for key, value in raw_data.items()}

    logging.info("Formatando texto das células para o relatório...")

    # Aplica os formatadores específicos para cada DataFrame e coluna
    if 'SecurityGroups' in data_frames and not data_frames['SecurityGroups'].empty:
        df_sg = data_frames['SecurityGroups']

        # Cria uma cópia para aplicar a formatação, mantendo o DF original para outras análises
        df_sg_formatted = df_sg.copy()

        # Renomeia as colunas de regras para nomes mais amigáveis
        df_sg_formatted.rename(columns={'IpPermissions': 'Inbound Rules', 'IpPermissionsEgress': 'Outbound Rules'}, inplace=True, errors='ignore')

        # Aplica a função de formatação para criar o texto sumarizado
        if 'Inbound Rules' in df_sg_formatted.columns:
            df_sg_formatted['Inbound Rules'] = df_sg_formatted['Inbound Rules'].apply(formatters.format_rules)
        if 'Outbound Rules' in df_sg_formatted.columns:
            df_sg_formatted['Outbound Rules'] = df_sg_formatted['Outbound Rules'].apply(formatters.format_rules)

        # Substitui o DataFrame no pacote com a versão formatada para escrita
        data_frames['SecurityGroups'] = df_sg_formatted

    # (Adicione aqui a formatação para outras abas, como RouteTables, se necessário)
    if 'RouteTables' in data_frames and not data_frames['RouteTables'].empty:
        df_rt = data_frames['RouteTables']

        # Formata as associações de rotas
        if 'Associations' in df_rt.columns:
            df_rt['Associations'] = df_rt['Associations'].apply(formatters.format_associations)

        # Formata as rotas propriamente ditas
        if 'Routes' in df_rt.columns:
            df_rt['Routes'] = df_rt['Routes'].apply(formatters.format_routes)

    # Garante que o diretório de saída exista
    os.makedirs(os.path.dirname(output_excel_path), exist_ok=True)

    # Escreve os DataFrames formatados no arquivo Excel de saída
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        # Define a ordem final das abas no relatório
        sheet_order = ['VPCs', 'Subnets', 'SecurityGroups', 'RouteTables', 'NetworkACLs', 'InternetGateways']
        for sheet_name in sheet_order:
            if sheet_name in data_frames and not data_frames[sheet_name].empty:
                data_frames[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)

    logging.info(f"Relatório Excel base gerado: {os.path.basename(output_excel_path)}")
