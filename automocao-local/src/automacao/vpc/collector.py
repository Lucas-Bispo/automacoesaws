import pandas as pd
import boto3
import logging
import json
from ..utils.config import get_config

# --- FUNÇÕES AUXILIARES DE NORMALIZAÇÃO ---
# Estas funções devem estar no mesmo arquivo para que a função principal as encontre.

def _normalize_sgs(sgs_raw_data):
    """ 'Explode' as regras de Security Groups em múltiplas linhas (uma por regra/origem). """
    sg_rules_list = []
    if not sgs_raw_data: return pd.DataFrame()

    for sg in sgs_raw_data:
        # Garante que mesmo SGs sem regras apareçam no resultado bruto
        if not sg.get('IpPermissions') and not sg.get('IpPermissionsEgress'):
             sg_rules_list.append({'GroupId': sg['GroupId'], 'GroupName': sg['GroupName'], 'VpcId': sg.get('VpcId'), 'Direction': 'Inbound', 'Protocol': 'N/A', 'FromPort': None, 'ToPort': None, 'SourceDest': 'Nenhuma regra definida', 'Description': sg.get('Description','')})

        for rule_type, permissions in [('Inbound', sg.get('IpPermissions', [])), ('Outbound', sg.get('IpPermissionsEgress', []))]:
            for rule in permissions:
                protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All')
                from_port, to_port = rule.get('FromPort'), rule.get('ToPort')
                sources = [(ip.get('CidrIp'), ip.get('Description', '')) for ip in rule.get('IpRanges', [])] + \
                          [(ip.get('CidrIpv6'), ip.get('Description', '')) for ip in rule.get('Ipv6Ranges', [])] + \
                          [(group.get('GroupId'), group.get('Description', '')) for group in rule.get('UserIdGroupPairs', [])]
                if not sources: sources.append(('N/A', ''))
                for source, desc in sources:
                    sg_rules_list.append({'GroupId': sg['GroupId'], 'GroupName': sg['GroupName'], 'VpcId': sg.get('VpcId'), 'Direction': rule_type, 'Protocol': protocol, 'FromPort': from_port, 'ToPort': to_port, 'SourceDest': source, 'Description': desc})
    return pd.DataFrame(sg_rules_list)

def _normalize_rts(rts_raw_data):
    """ 'Explode' as rotas de Route Tables em múltiplas linhas. """
    routes_list = []
    if not rts_raw_data: return pd.DataFrame()

    for rt in rts_raw_data:
        for route in rt.get('Routes', []):
            routes_list.append({
                'RouteTableId': rt['RouteTableId'], 'VpcId': rt.get('VpcId'),
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
                ports = f"{port_range.get('From', 'All')}-{port_range.get('To', '')}"
            entries_list.append({
                'NetworkAclId': nacl['NetworkAclId'], 'VpcId': nacl.get('VpcId'), 'IsDefault': nacl.get('IsDefault'),
                'RuleNumber': entry.get('RuleNumber'), 'Direction': 'Outbound' if entry.get('Egress') else 'Inbound',
                'Action': entry.get('RuleAction'), 'Protocol': str(entry.get('Protocol', '-1')).upper().replace('-1', 'All'),
                'PortRange': ports,
                'CidrBlock': entry.get('CidrBlock', entry.get('Ipv6CidrBlock', 'N/A'))
            })
    return pd.DataFrame(entries_list)


# --- FUNÇÃO PRINCIPAL DO MÓDULO ---

def collect_and_save_as_json(output_path: str):
    """
    Varre todas as regiões da AWS, coleta, normaliza e salva os dados brutos
    em um único arquivo JSON.
    """
    logging.info("Iniciando coleta de dados em todas as regiões da AWS...")
    
    default_ec2 = boto3.client('ec2', region_name='us-east-1')
    try:
        region_names = [region['RegionName'] for region in default_ec2.describe_regions()['Regions']]
    except Exception as e:
        logging.error(f"Não foi possível buscar as regiões da AWS: {e}. Usando 'us-east-1' como padrão.")
        region_names = ['us-east-1']

    all_data_raw = {
        "vpcs": [], "subnets": [], "igws": [], "sgs_raw": [], "rts_raw": [], "nacls_raw": []
    }

    for region in region_names:
        logging.info(f"Coletando dados da região: {region}...")
        try:
            regional_client = boto3.client('ec2', region_name=region)
            all_data_raw["vpcs"].extend(regional_client.describe_vpcs().get('Vpcs', []))
            all_data_raw["subnets"].extend(regional_client.describe_subnets().get('Subnets', []))
            all_data_raw["igws"].extend(regional_client.describe_internet_gateways().get('InternetGateways', []))
            all_data_raw["sgs_raw"].extend(regional_client.describe_security_groups().get('SecurityGroups', []))
            all_data_raw["rts_raw"].extend(regional_client.describe_route_tables().get('RouteTables', []))
            all_data_raw["nacls_raw"].extend(regional_client.describe_network_acls().get('NetworkAcls', []))
        except Exception as e:
            logging.warning(f"Falha ao coletar dados da região {region}: {e}")
            continue

    logging.info("Normalizando dados agregados...")
    df_sgs_normalized = _normalize_sgs(all_data_raw['sgs_raw'])
    df_rts_normalized = _normalize_rts(all_data_raw['rts_raw'])
    df_nacls_normalized = _normalize_nacls(all_data_raw['nacls_raw'])

    data_pack_dfs = {
        'VPCs': pd.json_normalize(all_data_raw['vpcs']),
        'Subnets': pd.json_normalize(all_data_raw['subnets']),
        'InternetGateways': pd.json_normalize(all_data_raw['igws']),
        'SecurityGroups': df_sgs_normalized,
        'RouteTables': df_rts_normalized,
        'NetworkACLs': df_nacls_normalized,
    }

    data_pack_to_save = {
        key: df.to_dict('records') for key, df in data_pack_dfs.items() if not df.empty
    }

    logging.info(f"Salvando dados brutos consolidados em JSON: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data_pack_to_save, f, ensure_ascii=False, indent=4, default=str)
        
    logging.info("Dados brutos em JSON salvos com sucesso.")