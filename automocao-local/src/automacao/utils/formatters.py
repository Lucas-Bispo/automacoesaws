# Este arquivo centraliza todas as funções que transformam dados complexos em texto legível.

def format_tags(tags_list):
    """Formata uma lista de tags em uma string de chave: valor."""
    if not isinstance(tags_list, list): return ""
    return "\n".join([f"{tag.get('Key', 'N/A')}: {tag.get('Value', 'N/A')}" for tag in tags_list])

def format_rules(rules_list):
    """Formata as regras de um Security Group."""
    if not isinstance(rules_list, list): return "N/A"
    if not rules_list: return "Nenhuma regra definida."
    
    formatted = []
    for rule in rules_list:
        protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'Tudo')
        from_port = rule.get('FromPort')
        to_port = rule.get('ToPort')
        
        port_str = f"Porta {from_port}" if from_port == to_port else f"Portas {from_port}-{to_port}"
        if from_port is None:
            port_str = "Todas" if protocol == "Tudo" else "N/A"
            
        sources = [r.get('CidrIp', '') for r in rule.get('IpRanges', [])] + \
                  [f"SG: {r.get('GroupId', '')}" for r in rule.get('UserIdGroupPairs', [])]
        source_str = ", ".join(filter(None, sources)) or "N/A"
        formatted.append(f"• {protocol} | {port_str} | De/Para: {source_str}")
    return "\n".join(formatted)

def format_associations(assoc_list):
    """Formata as associações de uma Route Table ou NACL."""
    if not isinstance(assoc_list, list): return ""
    # Checa se é uma associação de Route Table (tem SubnetId)
    if assoc_list and 'SubnetId' in assoc_list[0]:
        return "\n".join([f"Subnet: {a.get('SubnetId', 'N/A')} (Principal: {a.get('Main', False)})" for a in assoc_list])
    # Checa se é uma associação de NACL (tem NetworkAclAssociationId)
    elif assoc_list and 'NetworkAclAssociationId' in assoc_list[0]:
         return "\n".join([f"Subnet: {a.get('SubnetId', 'N/A')}" for a in assoc_list])
    return ""


def format_routes(routes_list):
    """Formata as rotas de uma Route Table."""
    if not isinstance(routes_list, list): return ""
    return "\n".join([f"Dest: {r.get('DestinationCidrBlock', r.get('DestinationIpv6CidrBlock', 'N/A'))} -> {r.get('GatewayId', r.get('TransitGatewayId', 'N/A'))}" for r in routes_list])

def format_nacl_entries(entries_list):
    """Formata as regras de uma Network ACL."""
    if not isinstance(entries_list, list): return ""
    formatted = []
    for entry in entries_list:
        action = "ALLOW" if entry.get('RuleAction') == 'allow' else "DENY"
        protocol = str(entry.get('Protocol', '-1')).upper().replace('-1', 'All')
        port_range = entry.get('PortRange')
        ports = "N/A"
        if port_range:
            ports = f"Porta {port_range.get('From')}" if port_range.get('From') == port_range.get('To') else f"Portas {port_range.get('From', 'All')}-{port_range.get('To', '')}"
        cidr = entry.get('CidrBlock', 'N/A')
        egress = "Saída" if entry.get('Egress') else "Entrada"
        formatted.append(f"#{entry.get('RuleNumber')} {egress} | {action} {protocol} | {ports} | De/Para: {cidr}")
    return "\n".join(sorted(formatted))

def format_igw_attachments(attachments_list):
    """Formata os anexos de um Internet Gateway."""
    if not isinstance(attachments_list, list): return ""
    return "\n".join([f"VPC: {att.get('VpcId')} (Estado: {att.get('State')})" for att in attachments_list])