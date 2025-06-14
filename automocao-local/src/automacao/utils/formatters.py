def format_tags(tags_list):
    """Formata uma lista de tags em uma string de chave: valor."""
    if not isinstance(tags_list, list) or not tags_list: return ""
    return "\n".join([f"{tag.get('Key', 'N/A')}: {tag.get('Value', 'N/A')}" for tag in tags_list])

def format_rules(rules_list):
    """ Formata uma lista de regras de SG em um texto multi-linha detalhado. """
    if not isinstance(rules_list, list) or not rules_list: return "Nenhuma regra."
    formatted_text = []
    for i, rule in enumerate(rules_list, 1):
        protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All Traffic')
        from_port, to_port = rule.get('FromPort'), rule.get('ToPort')
        port_str = "All"
        if from_port is not None: port_str = f"{from_port}" if from_port == to_port else f"{from_port}-{to_port}"
        sources = [f"  Source: {ip.get('CidrIp')} (Desc: {ip.get('Description', 'N/A')})" for ip in rule.get('IpRanges', [])]
        sources += [f"  Source SG: {group.get('GroupId')}" for group in rule.get('UserIdGroupPairs', [])]
        if not sources: sources.append("  Source: N/A")
        rule_str = f"Rule {i}:\n  Protocol: {protocol}, Ports: {port_str}\n" + "\n".join(sources)
        formatted_text.append(rule_str)
    return "\n\n".join(formatted_text)