import pandas as pd
import boto3
import logging
import json
import os
from collections import defaultdict
from ..utils.config import get_config

# --- FUNÇÕES AUXILIARES DE NORMALIZAÇÃO ---

def _normalize_sgs(sgs_raw_data):
    """ 'Explode' as regras de Security Groups em múltiplas linhas (uma por regra/origem). """
    logging.info("Normalizando dados de Security Groups...")
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
                
                # Combina todas as fontes de tráfego em uma única lista
                sources = []
                sources.extend([(ip.get('CidrIp'), ip.get('Description', '')) for ip in rule.get('IpRanges', [])])
                sources.extend([(ip.get('CidrIpv6'), ip.get('Description', '')) for ip in rule.get('Ipv6Ranges', [])])
                sources.extend([(group.get('GroupId'), group.get('Description', '')) for group in rule.get('UserIdGroupPairs', [])])
                
                if not sources: sources.append(('N/A', '')) # Garante que regras sem fonte ainda apareçam

                for source, desc in sources:
                    sg_rules_list.append({
                        'GroupId': sg['GroupId'], 'GroupName': sg['GroupName'], 'VpcId': sg.get('VpcId'), 
                        'Region': sg.get('Region'), 'Direction': rule_type, 'Protocol': protocol, 
                        'FromPort': from_port, 'ToPort': to_port, 'SourceDest': source, 'Description': desc
                    })
    return pd.DataFrame(sg_rules_list)

def _normalize_rts(rts_raw_data):
    """ 'Explode' as rotas de Route Tables em múltiplas linhas. """
    logging.info("Normalizando dados de Route Tables...")
    routes_list = []
    if not rts_raw_data: return pd.DataFrame()

    for rt in rts_raw_data:
        for route in rt.get('Routes', []):
            routes_list.append({
                'RouteTableId': rt['RouteTableId'], 'VpcId': rt.get('VpcId'), 'Region': rt.get('Region'),
                'Destination': route.get('DestinationCidrBlock', route.get('DestinationIpv6CidrBlock', 'N/A')),
                'Target': route.get('GatewayId', route.get('NatGatewayId', route.get('TransitGatewayId', route.get('InstanceId', 'N/A')))),
                'State': route.get('State'), 'Origin': route.get('Origin')
            })
    return pd.DataFrame(routes_list)

def _normalize_nacls(nacls_raw_data):
    """ 'Explode' as entradas de Network ACLs em múltiplas linhas. """
    logging.info("Normalizando dados de Network ACLs...")
    entries_list = []
    if not nacls_raw_data: return pd.DataFrame()

    for nacl in nacls_raw_data:
        for entry in nacl.get('Entries', []):
            if entry.get('RuleNumber') == 32767: continue # Pula a regra padrão implícita de DENY ALL
            port_range = entry.get('PortRange')
            ports = "N/A"
            if port_range:
                from_port, to_port = port_range.get('From', 'All'), port_range.get('To', '')
                ports = f"{from_port}-{to_port}" if to_port and from_port != to_port else f"{from_port}"
            entries_list.append({
                'NetworkAclId': nacl['NetworkAclId'], 'VpcId': nacl.get('VpcId'), 'IsDefault': nacl.get('IsDefault'), 'Region': nacl.get('Region'),
                'RuleNumber': entry.get('RuleNumber'), 'Direction': 'Outbound' if entry.get('Egress') else 'Inbound',
                'Action': entry.get('RuleAction'), 'Protocol': str(entry.get('Protocol', '-1')).upper().replace('-1', 'All'),
                'PortRange': ports, 'CidrBlock': entry.get('CidrBlock', entry.get('Ipv6CidrBlock', 'N/A'))
            })
    return pd.DataFrame(entries_list)


# --- FUNÇÃO PRINCIPAL DE COLETA ---

def collect_data(regions_to_scan: list):
    """Coleta e normaliza dados de rede de uma lista de regiões."""
    all_data_raw = defaultdict(list)
    for region in regions_to_scan:
        logging.info(f"Coletando dados da região: {region}...")
        try:
            client = boto3.client('ec2', region_name=region)
            # Dicionário para simplificar as chamadas de API e o nome da chave de resposta
            resources_to_fetch = {
                "Vpcs": "describe_vpcs", "Subnets": "describe_subnets", "InternetGateways": "describe_internet_gateways",
                "SecurityGroups": "describe_security_groups", "RouteTables": "describe_route_tables", "NetworkAcls": "describe_network_acls"
            }
            for key, method_name in resources_to_fetch.items():
                response = getattr(client, method_name)()
                data = response.get(key, [])
                for item in data:
                    item['Region'] = region
                all_data_raw[key.lower()].extend(data)
        except Exception as e:
            logging.warning(f"Falha ao coletar dados da região {region}: {e}")
            continue

    logging.info("Normalizando dados agregados...")
    
    df_sgs = _normalize_sgs(all_data_raw['securitygroups'])
    df_rts = _normalize_rts(all_data_raw['routetables'])
    df_nacls = _normalize_nacls(all_data_raw['networkacls'])
    
    # Cria o pacote de dados final com os DataFrames prontos
    data_pack = {
        'VPCs': pd.json_normalize(all_data_raw['vpcs']),
        'Subnets': pd.json_normalize(all_data_raw['subnets']),
        'SecurityGroups': df_sgs,
        'RouteTables': df_rts,
        'NetworkACLs': df_nacls,
        'InternetGateways': pd.json_normalize(all_data_raw['internetgateways']),
    }
    return data_pack

# --- FUNÇÃO DE ORQUESTRAÇÃO DO MÓDULO (Chamada pelo main.py) ---

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