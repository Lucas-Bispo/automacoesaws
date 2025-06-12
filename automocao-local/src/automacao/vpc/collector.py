import pandas as pd
import boto3
import logging
import json
import os
from collections import defaultdict
from ..utils.config import get_config

def _normalize_sgs(sgs_raw_data):
    """ 'Explode' as regras de Security Groups em múltiplas linhas. """
    sg_rules_list = []
    if not sgs_raw_data: return pd.DataFrame()
    for sg in sgs_raw_data:
        if not sg.get('IpPermissions') and not sg.get('IpPermissionsEgress'):
             sg_rules_list.append({'GroupId': sg['GroupId'], 'GroupName': sg['GroupName'], 'VpcId': sg.get('VpcId'), 'Region': sg.get('Region'), 'Direction': 'Inbound', 'Protocol': 'N/A', 'FromPort': None, 'ToPort': None, 'SourceDest': 'Nenhuma regra definida', 'Description': sg.get('Description','')})
        for rule_type, permissions in [('Inbound', sg.get('IpPermissions', [])), ('Outbound', sg.get('IpPermissionsEgress', []))]:
            for rule in permissions:
                protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All')
                from_port, to_port = rule.get('FromPort'), rule.get('ToPort')
                sources = [(ip.get('CidrIp'), ip.get('Description', '')) for ip in rule.get('IpRanges', [])] + \
                          [(ip.get('CidrIpv6'), ip.get('Description', '')) for ip in rule.get('Ipv6Ranges', [])] + \
                          [(group.get('GroupId'), group.get('Description', '')) for group in rule.get('UserIdGroupPairs', [])]
                if not sources: sources.append(('N/A', ''))
                for source, desc in sources:
                    sg_rules_list.append({'GroupId': sg['GroupId'], 'GroupName': sg['GroupName'], 'VpcId': sg.get('VpcId'), 'Region': sg.get('Region'), 'Direction': rule_type, 'Protocol': protocol, 'FromPort': from_port, 'ToPort': to_port, 'SourceDest': source, 'Description': desc})
    return pd.DataFrame(sg_rules_list)

def _normalize_rts(rts_raw_data):
    """ 'Explode' as rotas de Route Tables em múltiplas linhas. """
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
    entries_list = []
    if not nacls_raw_data: return pd.DataFrame()
    for nacl in nacls_raw_data:
        for entry in nacl.get('Entries', []):
            if entry.get('RuleNumber') == 32767: continue
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

def collect_data(regions_to_scan: list):
    """Coleta e normaliza dados de rede de uma lista de regiões."""
    all_data_raw = defaultdict(list)
    for region in regions_to_scan:
        logging.info(f"Coletando dados da região: {region}...")
        try:
            regional_client = boto3.client('ec2', region_name=region)
            # Dicionário para simplificar as chamadas de API
            resources_to_fetch = {
                "vpcs": "describe_vpcs", "subnets": "describe_subnets", "igws": "describe_internet_gateways",
                "sgs_raw": "describe_security_groups", "rts_raw": "describe_route_tables", "nacls_raw": "describe_network_acls"
            }
            for key, method_name in resources_to_fetch.items():
                # A chave de resposta da API geralmente é o nome do recurso no plural com a primeira letra maiúscula
                # Ex: describe_vpcs -> 'Vpcs'
                response_key = method_name.split('_')[-1].capitalize()
                response = getattr(regional_client, method_name)()
                data = response.get(response_key, [])
                for item in data:
                    item['Region'] = region
                all_data_raw[key].extend(data)
        except Exception as e:
            logging.warning(f"Falha ao coletar dados da região {region}: {e}")
            continue

    logging.info("Normalizando dados agregados...")
    df_sgs = _normalize_sgs(all_data_raw['sgs_raw'])
    df_rts = _normalize_rts(all_data_raw['rts_raw'])
    df_nacls = _normalize_nacls(all_data_raw['nacls_raw'])
    
    data_pack = {
        'VPCs': pd.json_normalize(all_data_raw['vpcs']),
        'Subnets': pd.json_normalize(all_data_raw['subnets']),
        'SecurityGroups': df_sgs,
        'RouteTables': df_rts,
        'NetworkACLs': df_nacls,
        'InternetGateways': pd.json_normalize(all_data_raw['igws']),
    }
    return data_pack

def collect_and_save_as_json(output_path: str, regions_to_scan: list):
    """Orquestra a coleta e salvamento dos dados em um arquivo JSON."""
    try:
        data_pack_dfs = collect_data(regions_to_scan)
        data_pack_to_save = {key: df.to_dict('records') for key, df in data_pack_dfs.items() if not df.empty}
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_pack_to_save, f, ensure_ascii=False, indent=4, default=str)
        logging.info(f"Dados brutos consolidados salvos em JSON: {output_path}")
    except Exception as e:
        logging.error(f"Falha na etapa de coleta e escrita do JSON: {e}", exc_info=True)
        raise