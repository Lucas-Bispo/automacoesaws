# Arquivo: src/automacao/utils/formatters.py

def format_tags(tags_list):
    """Formata uma lista de tags em uma string de chave: valor."""
    if not isinstance(tags_list, list) or not tags_list:
        return ""
    return "\n".join([f"{tag.get('Key', 'N/A')}: {tag.get('Value', 'N/A')}" for tag in tags_list])

def format_rules(rules_list):
    """ 
    Formata uma lista de regras de SG em um texto multi-linha detalhado,
    exatamente como no seu exemplo de imagem.
    """
    if not isinstance(rules_list, list) or not rules_list:
        return "Nenhuma regra."

    formatted_text = []
    for i, rule in enumerate(rules_list, 1):
        # Formata o protocolo
        protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All Traffic')
        
        # Formata as portas
        from_port, to_port = rule.get('FromPort'), rule.get('ToPort')
        port_str = "All"
        if from_port is not None:
            port_str = f"{from_port}" if from_port == to_port else f"{from_port}-{to_port}"
        
        # Formata as fontes (IPs, outros SGs, etc.)
        sources = []
        for ip in rule.get('IpRanges', []):
            sources.append(f"  Source: {ip.get('CidrIp')} (Description: {ip.get('Description', 'N/A')})")
        for group in rule.get('UserIdGroupPairs', []):
            sources.append(f"  Source SG: {group.get('GroupId')} (Description: {group.get('Description', 'N/A')})")
        
        if not sources:
            sources.append("  Source: N/A")

        # Monta a string final para esta regra específica
        rule_str = f"Rule {i}:\n  Protocol: {protocol}, Ports: {port_str}\n" + "\n".join(sources)
        formatted_text.append(rule_str)

    # Junta todas as regras formatadas com um espaço extra entre elas
    return "\n\n".join(formatted_text)