import pandas as pd
import boto3
import logging
from collections import defaultdict
from ..utils.config import get_config

def collect_data(regions_to_scan: list):
    """
    Coleta os dados de rede de uma lista de regiões, mantendo a estrutura
    de um recurso por linha.
    """
    all_data_raw = defaultdict(list)
    logging.info(f"Iniciando coleta em {len(regions_to_scan)} regiões...")

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
            for key, data in resources_to_fetch.items():
                for item in data:
                    item['Region'] = region
                all_data_raw[key].extend(data)
        except Exception as e:
            logging.warning(f"Falha ao coletar dados da região {region}: {e}")
            continue

    data_pack = {key: pd.json_normalize(value) for key, value in all_data_raw.items()}
    logging.info("Coleta de dados brutos (sumarizados) concluída.")
    return data_pack