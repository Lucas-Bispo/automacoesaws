import pandas as pd
import boto3
import logging
import json
import os
from collections import defaultdict
from ..utils.config import get_config

def collect_data(regions_to_scan: list):
    """
    Coleta dados de rede de uma lista de regiões, mantendo a estrutura
    de um recurso por linha (formato sumarizado).
    """
    all_data_raw = defaultdict(list)
    session = boto3.Session()

    print("Coletando dados de rede de todas as regiões...")
    for region in regions_to_scan:
        print(f"Iniciando coleta de dados da região: {region}...")
        try:
            client = session.client('ec2', region_name=region)
            # Lista de recursos que vamos buscar
            resources_to_fetch = {
                "VPCs": client.describe_vpcs().get('Vpcs', []),
                "Subnets": client.describe_subnets().get('Subnets', []),
                "SecurityGroups": client.describe_security_groups().get('SecurityGroups', []),
                "RouteTables": client.describe_route_tables().get('RouteTables', []),
            }
            # Adiciona a informação da região a cada recurso coletado
            for key, data in resources_to_fetch.items():
                if data:
                    for item in data:
                        item['Region'] = region
                    all_data_raw[key].extend(data)
                    print(f"Adicionado {len(data)} {key} da região {region} ao pacote de dados.")
        except Exception as e:
            print(f"Erro ao coletar dados da região {region}: {e}")
            continue
    
    print("Coleta de dados brutos (sumarizados) concluída.")
    # Converte as listas de dicionários em DataFrames do Pandas
    data_pack = {key: pd.json_normalize(value) for key, value in all_data_raw.items()}
    print("Conversão de dados brutos para DataFrames do Pandas concluída.")
    return data_pack

def collect_and_save_as_json(output_path: str, regions_to_scan: list):
    """
    Orquestra a coleta, converte os DataFrames para um formato serializável
    e salva o resultado em um único arquivo JSON.
    """
    # ETAPA 1.1: Coleta os dados
    data_pack_dfs = collect_data(regions_to_scan)
    print("Coleta de dados brutos (sumarizados) concluída.")
    
    # ETAPA 1.2: Prepara os dados para salvar em JSON
    data_pack_to_save = {
        key: df.to_dict('records') for key, df in data_pack_dfs.items() if not df.empty
    }
    print("Preparo dos dados para salvar em JSON concluído.")
    
    # ETAPA 1.3: Salva o arquivo JSON
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data_pack_to_save, f, ensure_ascii=False, indent=4, default=str)
    print(f"Dados brutos consolidados salvos em JSON: {os.path.basename(output_path)}")
    
    # Retorna os DataFrames para a Etapa de Análise que acontece em memória no main.py
    print("Retornando DataFrames para a Etapa de Análise...")
    return data_pack_dfs

# limpar aquivos da memoria do json