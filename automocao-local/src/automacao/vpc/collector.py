import pandas as pd
import boto3
import logging
import json
import os
from collections import defaultdict

def collect_data(regions_to_scan: list):
    """Coleta dados de rede, mantendo um recurso por linha (formato sumarizado)."""
    all_data_raw = defaultdict(list)
    for region in regions_to_scan:
        logging.info(f"Coletando dados da região: {region}...")
        try:
            client = boto3.client('ec2', region_name=region)
            # Lista de recursos para buscar
            resources_to_fetch = {
                "VPCs": client.describe_vpcs().get('Vpcs', []),
                "Subnets": client.describe_subnets().get('Subnets', []),
                "SecurityGroups": client.describe_security_groups().get('SecurityGroups', []),
                "RouteTables": client.describe_route_tables().get('RouteTables', []),
                "NetworkACLs": client.describe_network_acls().get('NetworkAcls', []),
                "InternetGateways": client.describe_internet_gateways().get('InternetGateways', []),
            }
            # Adiciona a informação da região a cada recurso
            for key, data in resources_to_fetch.items():
                if data:
                    for item in data: item['Region'] = region
                    all_data_raw[key].extend(data)
        except Exception as e:
            logging.warning(f"Falha ao coletar dados da região {region}: {e}")
            continue
    
    # Converte listas de dicionários em DataFrames
    data_pack = {key: pd.json_normalize(value) for key, value in all_data_raw.items()}
    logging.info("Coleta de dados brutos (sumarizados) concluída.")
    return data_pack

def collect_and_save_as_json(output_path: str, regions_to_scan: list):
    """Orquestra a coleta e salvamento dos dados em um arquivo JSON."""
    data_pack_dfs = collect_data(regions_to_scan)
    # Converte DataFrames de volta para um formato serializável
    data_pack_to_save = {key: df.to_dict('records') for key, df in data_pack_dfs.items() if not df.empty}
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data_pack_to_save, f, ensure_ascii=False, indent=4, default=str)
    logging.info(f"Dados brutos consolidados salvos em JSON: {os.path.basename(output_path)}")