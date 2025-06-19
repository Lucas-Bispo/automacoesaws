# Arquivo: src/automacao/utils/formatters.py

def format_tags(tags_list):
    """
    Formata uma lista de tags da AWS (chave: valor) em uma única string multi-linha,
    onde cada tag aparece em uma nova linha.
    """
    # Verifica se a entrada é realmente uma lista e se não está vazia.
    # Se não for uma lista ou estiver vazia, retorna uma string vazia.
    if not isinstance(tags_list, list) or not tags_list:
        return ""
    
    # Usa uma list comprehension para iterar sobre cada dicionário de tag na tags_list.
    # Para cada tag, ele pega o valor da chave 'Key' e 'Value' (usando 'N/A' como fallback se a chave não existir).
    # Em seguida, junta todas essas strings formatadas com uma quebra de linha ('\n') entre elas.
    return "\n".join([f"{tag.get('Key', 'N/A')}: {tag.get('Value', 'N/A')}" for tag in tags_list])

def format_rules(rules_list):
    """ 
    Formata uma lista de regras de Security Group (Inbound ou Outbound) em um texto multi-linha detalhado,
    pronto para ser exibido em uma célula de planilha, mostrando protocolo, portas e fontes/destinos.
    """
    # Verifica se a entrada é realmente uma lista e se não está vazia.
    # Se não for uma lista ou estiver vazia, significa que não há regras, então retorna uma mensagem padrão.
    if not isinstance(rules_list, list) or not rules_list:
        return "Nenhuma regra."

    formatted_text = [] # Lista para armazenar as strings formatadas de cada regra individualmente
    
    # Itera sobre cada 'rule' (dicionário) na rules_list, começando a contagem de 'i' em 1.
    for i, rule in enumerate(rules_list, 1):
        # Formata o protocolo:
        # Pega o valor de 'IpProtocol'. Se for '-1', significa 'All Traffic'.
        # Converte para string, coloca em maiúsculas e substitui '-1' por 'All Traffic'.
        protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All Traffic')
        
        # Formata as portas:
        # Pega os valores de 'FromPort' (porta inicial) e 'ToPort' (porta final).
        from_port, to_port = rule.get('FromPort'), rule.get('ToPort')
        port_str = "All" # Valor padrão para portas (se não especificado ou se FromPort/ToPort forem None)
        
        # Se 'FromPort' não for None (indicando que portas foram especificadas)
        if from_port is not None:
            # Se a porta inicial for igual à porta final, mostra apenas uma porta (ex: "80")
            if from_port == to_port:
                port_str = f"{from_port}"
            # Caso contrário, mostra um intervalo de portas (ex: "22-80")
            else:
                port_str = f"{from_port}-{to_port}"
        
        # Formata as fontes (para regras de entrada) ou destinos (para regras de saída):
        # Pode ser um IP (CidrIp) ou outro Security Group (UserIdGroupPairs).
        sources = [] # Lista para armazenar as descrições das fontes/destinos desta regra
        
        # Itera sobre os blocos IP (CIDRs) definidos na regra.
        for ip in rule.get('IpRanges', []):
            # Adiciona uma string formatada para cada IP de origem, incluindo sua descrição (se houver).
            sources.append(f"  Source: {ip.get('CidrIp')} (Description: {ip.get('Description', 'N/A')})")
        
        # Itera sobre os pares de ID de usuário/grupo (referência a outros Security Groups).
        for group in rule.get('UserIdGroupPairs', []):
            # Adiciona uma string formatada para cada Security Group de origem, incluindo sua descrição.
            sources.append(f"  Source SG: {group.get('GroupId')} (Description: {group.get('Description', 'N/A')})")
        
        # Se nenhuma fonte (IP ou SG) foi encontrada para esta regra, adiciona uma entrada "N/A".
        if not sources:
            sources.append("  Source: N/A")

        # Monta a string final para esta regra específica.
        # Inclui o número da regra, protocolo, portas, e as fontes/destinos formatados,
        # cada um em uma nova linha.
        rule_str = f"Rule {i}:\n  Protocol: {protocol}, Ports: {port_str}\n" + "\n".join(sources)
        
        # Adiciona a string formatada desta regra à lista de todas as regras.
        formatted_text.append(rule_str)

    # Junta todas as strings de regras formatadas com duas quebras de linha ('\n\n') entre elas.
    # Isso cria um espaço visual entre as descrições de regras diferentes na célula da planilha.
    return "\n\n".join(formatted_text)
