import pandas as pd
import boto3
import logging
import json
import os
from collections import defaultdict
from ..utils.config import get_config

# --- FUNÇÕES AUXILIARES DE NORMALIZAÇÃO ---

def _normalize_sgs(sgs_raw_data):
    """ 'Explode' as regras de Security Groups em múltiplas linhas. """
    sg_rules_list = []
    if not sgs_raw_data:
        return pd.DataFrame()
    for sg in sgs_raw_data:
        # Garante que SGs sem regras ainda apareçam no resultado para análise
        if not sg.get('IpPermissions') and not sg.get('IpPermissionsEgress'):
             sg_rules_list.append({
                 'GroupId': sg.get('GroupId'), 'GroupName': sg.get('GroupName'), 'VpcId': sg.get('VpcId'), 
                 'Region': sg.get('Region'), 'Direction': 'Inbound', 'Protocol': 'N/A', 'FromPort': None, 
                 'ToPort': None, 'SourceDest': 'Nenhuma regra definida', 'Description': sg.get('Description','')
                })
             continue
        # Processa regras de entrada e saída
        for rule_type, permissions in [('Inbound', sg.get('IpPermissions', [])), ('Outbound', sg.get('IpPermissionsEgress', []))]:
            for rule in permissions:
                protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All')
                from_port, to_port = rule.get('FromPort'), rule.get('ToPort')
                sources = [(ip.get('CidrIp'), ip.get('Description', '')) for ip in rule.get('IpRanges', [])] + \
                          [(ip.get('CidrIpv6'), ip.get('Description', '')) for ip in rule.get('Ipv6Ranges', [])] + \
                          [(group.get('GroupId'), group.get('Description', '')) for group in rule.get('UserIdGroupPairs', [])]
                if not sources: sources.append(('N/A', ''))
                for source, desc in sources:
                    sg_rules_list.append({
                        'GroupId': sg['GroupId'], 'GroupName': sg['GroupName'], 'VpcId': sg.get('VpcId'), 
                        'Region': sg.get('Region'), 'Direction': rule_type, 'Protocol': protocol, 
                        'FromPort': from_port, 'ToPort': to_port, 'SourceDest': source, 'Description': desc
                    })
    return pd.DataFrame(sg_rules_list)

# Adicione aqui as outras funções de normalização, como _normalize_rts e _normalize_nacls, se necessário.

# --- FUNÇÃO DE COLETA ---

def collect_data(regions_to_scan: list):
    """Coleta e normaliza dados de rede de uma lista de regiões."""
    all_data_raw = defaultdict(list)
    for region in regions_to_scan:
        logging.info(f"Coletando dados da região: {region}...")
        try:
            client = boto3.client('ec2', region_name=region)
            resources_to_fetch = {
                "Vpcs": client.describe_vpcs().get('Vpcs', []),
                "Subnets": client.describe_subnets().get('Subnets', []),
                "SecurityGroups": client.describe_security_groups().get('SecurityGroups', [])
                # Adicione outras chamadas aqui (describe_route_tables, etc.)
            }
            for key, data in resources_to_fetch.items():
                for item in data:
                    item['Region'] = region
                all_data_raw[key].extend(data)
        except Exception as e:
            logging.warning(f"Falha ao coletar dados da região {region}: {e}")
            continue

    logging.info("Normalizando dados agregados...")
    
    # Usa a função de normalização
    df_sgs_normalized = _normalize_sgs(all_data_raw['SecurityGroups'])
    
    data_pack = {
        'VPCs': pd.json_normalize(all_data_raw['Vpcs']),
        'Subnets': pd.json_normalize(all_data_raw['Subnets']),
        'SecurityGroups': df_sgs_normalized,
        # Adicione outros DataFrames aqui
    }
    return data_pack

# --- FUNÇÃO PRINCIPAL DO MÓDULO (Chamada pelo main.py) ---

def collect_and_save_as_json(output_path: str, regions_to_scan: list):
    """Orquestra a coleta, normalização e salvamento dos dados em um arquivo JSON."""
    try:
        data_pack_dfs = collect_data(regions_to_scan)
        
        # Converte DataFrames para um formato que o JSON entende
        data_pack_to_save = {
            key: df.to_dict('records') for key, df in data_pack_dfs.items() if not df.empty
        }
        
        # Cria o diretório de saída se ele não existir
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Salva o arquivo JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_pack_to_save, f, ensure_ascii=False, indent=4, default=str)
            
        logging.info(f"Dados brutos consolidados salvos em JSON: {os.path.basename(output_path)}")
        
        # Retorna os DataFrames para as próximas etapas em memória no main.py
        return data_pack_dfs
    except Exception as e:
        logging.error(f"Falha na etapa de coleta e escrita do JSON: {e}", exc_info=True)
        raise