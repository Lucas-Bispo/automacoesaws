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
            resources_to_fetch = {
                "VPCs": client.describe_vpcs().get('Vpcs', []),
                "Subnets": client.describe_subnets().get('Subnets', []),
                "SecurityGroups": client.describe_security_groups().get('SecurityGroups', []),
                "RouteTables": client.describe_route_tables().get('RouteTables', []),
            }
            for key, data in resources_to_fetch.items():
                if data:
                    for item in data:
                        item['Region'] = region
                    all_data_raw[key].extend(data)
        except Exception as e:
            logging.warning(f"Falha ao coletar dados da região {region}: {e}")
    return {key: pd.json_normalize(value) for key, value in all_data_raw.items()}

def collect_and_save_as_json(output_path: str, regions_to_scan: list):
    """Orquestra a coleta, converte para um formato serializável e salva em JSON."""
    data_pack_dfs = collect_data(regions_to_scan)
    data_pack_to_save = {key: df.to_dict('records') for key, df in data_pack_dfs.items() if not df.empty}
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data_pack_to_save, f, ensure_ascii=False, indent=4, default=str)
    logging.info(f"Dados brutos salvos em JSON: {os.path.basename(output_path)}")