import pandas as pd
import boto3
import logging
from ..utils.config import get_config

def _normalize_sgs(sgs_raw_data):
    """ 'Explode' as regras de Security Groups em múltiplas linhas (uma por regra/origem). """
    sg_rules_list = []
    if not sgs_raw_data: return pd.DataFrame()

    for sg in sgs_raw_data:
        for rule_type, permissions in [('Inbound', sg.get('IpPermissions', [])), ('Outbound', sg.get('IpPermissionsEgress', []))]:
            if not permissions:
                sg_rules_list.append({'GroupId': sg['GroupId'], 'GroupName': sg['GroupName'], 'VpcId': sg.get('VpcId'), 'Direction': rule_type, 'Protocol': 'N/A', 'FromPort': 'N/A', 'ToPort': 'N/A', 'SourceDest': 'Nenhuma regra definida', 'Description': ''})
            else:
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

def collect_data():
    """ Coleta e normaliza todos os dados de rede para o relatório. """
    logging.info("Iniciando coleta e normalização completa de dados do serviço VPC...")
    aws_region = get_config('AWS_REGION', 'us-east-1')
    ec2 = boto3.client('ec2', region_name=aws_region)
    
    vpcs_raw = ec2.describe_vpcs().get('Vpcs', [])
    subnets_raw = ec2.describe_subnets().get('Subnets', [])
    igws_raw = ec2.describe_internet_gateways().get('InternetGateways', [])
    sgs_raw = ec2.describe_security_groups().get('SecurityGroups', [])
    rts_raw = ec2.describe_route_tables().get('RouteTables', [])
    nacls_raw = ec2.describe_network_acls().get('NetworkAcls', [])
    
    logging.info("Normalizando dados coletados...")

    df_sgs_normalized = _normalize_sgs(sgs_raw)
    df_rts_normalized = _normalize_rts(rts_raw)
    df_nacls_normalized = _normalize_nacls(nacls_raw)
    
    vpc_sg_map = df_sgs_normalized[['VpcId', 'GroupId']].dropna().drop_duplicates().rename(columns={'GroupId': 'SecurityGroupId'})
    
    subnet_rt_map = []
    for rt in rts_raw:
        for assoc in rt.get('Associations', []):
            if assoc.get('SubnetId'):
                subnet_rt_map.append({'SubnetId': assoc['SubnetId'], 'RouteTableId': rt['RouteTableId']})

    data_pack = {
        'VPCs': pd.json_normalize(vpcs_raw),
        'Subnets': pd.json_normalize(subnets_raw),
        'SecurityGroups': df_sgs_normalized,
        'RouteTables': df_rts_normalized,
        'NetworkACLs': df_nacls_normalized,
        'InternetGateways': pd.json_normalize(igws_raw),
        'MAP_VPC_x_SG': vpc_sg_map,
        'MAP_Subnet_x_RT': pd.DataFrame(subnet_rt_map)
    }
    
    logging.info("Preparação de dados normalizados concluída.")
    return data_pack