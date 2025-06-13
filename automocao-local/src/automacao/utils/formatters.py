# --- FUNÇÕES DE FORMATAÇÃO DE TEXTO ---

def format_tags(tags_list):
    """Formata uma lista de tags em uma string de chave: valor."""
    if not isinstance(tags_list, list) or not tags_list:
        return "N/A"
    return "\n".join([f"{tag.get('Key', 'N/A')}: {tag.get('Value', 'N/A')}" for tag in tags_list])

def format_rules(rules_list):
    """Formata as regras de um Security Group em texto legível."""
    if not isinstance(rules_list, list) or not rules_list:
        return "Nenhuma regra definida."
    
    formatted = []
    for i, rule in enumerate(rules_list, 1):
        protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All Traffic')
        from_port, to_port = rule.get('FromPort'), rule.get('ToPort')
        
        port_str = "All"
        if from_port is not None:
            port_str = f"{from_port}" if from_port == to_port else f"{from_port}-{to_port}"
        
        sources = [f"  Source: {ip.get('CidrIp')} (Desc: {ip.get('Description', 'N/A')})" for ip in rule.get('IpRanges', [])]
        sources += [f"  Source: {group.get('GroupId')} (Desc: {group.get('Description', 'N/A')})" for group in rule.get('UserIdGroupPairs', [])]
        
        if not sources:
            sources.append("  Source: N/A")

        rule_str = f"Rule {i}:\n  Protocol: {protocol}, Ports: {port_str}\n" + "\n".join(sources)
        formatted.append(rule_str)

    return "\n\n".join(formatted)

def format_associations(assoc_list):
    """Formata as associações de uma Route Table ou NACL."""
    if not isinstance(assoc_list, list) or not assoc_list:
        return "Nenhuma"
    # Associações de Route Table
    if 'SubnetId' in assoc_list[0]:
        return "\n".join([f"Subnet: {a.get('SubnetId', 'N/A')} (Principal: {a.get('Main', False)})" for a in assoc_list])
    return "Formato de associação desconhecido"

def format_routes(routes_list):
    """Formata as rotas de uma Route Table."""
    if not isinstance(routes_list, list) or not routes_list:
        return "Nenhuma"
    return "\n".join([f"Dest: {r.get('DestinationCidrBlock', r.get('DestinationIpv6CidrBlock', 'N/A'))} -> Target: {r.get('GatewayId', r.get('NatGatewayId', 'N/A'))}" for r in routes_list])

def format_nacl_entries(entries_list):
    """Formata as regras de uma Network ACL."""
    if not isinstance(entries_list, list) or not entries_list:
        return "Nenhuma"
    formatted = []
    for entry in entries_list:
        if entry.get('RuleNumber') == 32767: continue
        action = "ALLOW" if entry.get('RuleAction') == 'allow' else "DENY"
        protocol = str(entry.get('Protocol', '-1')).upper().replace('-1', 'All')
        ports = "N/A"
        if entry.get('PortRange'):
            ports = f"{entry['PortRange'].get('From', 'All')}-{entry['PortRange'].get('To', '')}"
        cidr = entry.get('CidrBlock', 'N/A')
        direction = "Saída" if entry.get('Egress') else "Entrada"
        formatted.append(f"#{entry.get('RuleNumber')} {direction} | {action} {protocol} | {ports} | {cidr}")
    return "\n".join(sorted(formatted))

def format_igw_attachments(attachments_list):
    """Formata os anexos de um Internet Gateway."""
    if not isinstance(attachments_list, list) or not attachments_list:
        return "Nenhum"
    return "\n".join([f"VPC: {att.get('VpcId')} (Estado: {att.get('State')})" for att in attachments_list])