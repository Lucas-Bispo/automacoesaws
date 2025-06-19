import pandas as pd  # Biblioteca para manipulação de dados tabulares (DataFrames)
import logging  # Biblioteca para registrar logs de eventos e erros

# --- CRITÉRIOS DE RISCO ---
HIGH_RISK_PORTS = {22, 3389, 3306, 5432, 1433, 27017}  # Portas críticas (SSH, RDP, bancos de dados)
ACCEPTABLE_PUBLIC_PORTS = {80, 443}  # Portas web públicas consideradas aceitáveis
ANYWHERE_CIDR = '0.0.0.0/0'  # Representa acesso aberto para qualquer IP na internet

def analyze_sgs(security_groups: list):
    """
    Analisa uma LISTA de objetos SecurityGroup e retorna:
    - um DataFrame com os riscos encontrados,
    - um dicionário mapeando o nível de risco de cada Security Group para uso em coloração.
    """
    logging.info("Analisando objetos Security Group para riscos...")  # Log do início da análise
    findings = []  # Lista para armazenar os achados de risco detalhados
    sg_risk_map = {}  # Dicionário para mapear o nível de risco final de cada Security Group

    # Itera sobre cada Security Group recebido
    for sg in security_groups:
        highest_risk_level = 0  # Inicializa o nível de risco para este SG (0=Seguro,1=Médio,2=Alto)

        # Analisa as regras de entrada (Inbound) do Security Group, acessando dados brutos
        for rule in sg.raw_rules.get('IpPermissions', []):
            # Verifica se a regra está aberta para todo o mundo (0.0.0.0/0)
            is_open_to_world = any(
                ip_range.get('CidrIp') == ANYWHERE_CIDR
                for ip_range in rule.get('IpRanges', [])
            )
            if not is_open_to_world:
                continue  # Se não estiver aberta para o mundo, ignora essa regra e vai para a próxima

            # Obtém as portas inicial e final da regra
            from_port = rule.get('FromPort')
            to_port = rule.get('ToPort')
            # Obtém o protocolo da regra, substitui '-1' por 'All' e converte para maiúsculas
            protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All')
            
            # Se a regra libera todas as portas (protocolo 'All' ou portas não especificadas)
            if protocol == 'All' or from_port is None:
                # Atualiza o nível de risco para pelo menos médio
                highest_risk_level = max(highest_risk_level, 1)
                # Adiciona um achado detalhado para essa regra de alto risco
                findings.append({
                    "Risco": "Médio",
                    "ID do Security Group": sg.id,
                    "Nome do Grupo": sg.name,
                    "Regra Problemática": f"Entrada {protocol}:TODAS de {ANYWHERE_CIDR}",
                    "Recomendação": "Acesso de todas as portas liberado para a internet. Especifique as portas necessárias."
                })
                continue  # Passa para próxima regra

            # Se portas específicas foram definidas, analisa cada porta individualmente
            for port in range(from_port, to_port + 1):
                rule_text = f"Entrada {protocol}:{port} de {ANYWHERE_CIDR}"
                # Verifica se a porta é crítica (alto risco)
                if port in HIGH_RISK_PORTS:
                    highest_risk_level = max(highest_risk_level, 2)  # Atualiza para alto risco
                    findings.append({
                        "Risco": "Alto",
                        "ID do Security Group": sg.id,
                        "Nome do Grupo": sg.name,
                        "Regra Problemática": rule_text,
                        "Recomendação": "Acesso crítico (gerenciamento/BD) exposto à internet. RESTRINJA a origem."
                    })
                # Verifica se a porta é diferente das portas públicas padrão (risco médio)
                elif port not in ACCEPTABLE_PUBLIC_PORTS:
                    highest_risk_level = max(highest_risk_level, 1)  # Atualiza para médio risco
                    findings.append({
                        "Risco": "Médio",
                        "ID do Security Group": sg.id,
                        "Nome do Grupo": sg.name,
                        "Regra Problemática": rule_text,
                        "Recomendação": "Porta não-padrão exposta à internet. Verifique a necessidade."
                    })

        # Após analisar todas as regras, mapeia o nível de risco final para o ID do Security Group
        if highest_risk_level == 2:
            sg_risk_map[sg.id] = "Alto"
        elif highest_risk_level == 1:
            sg_risk_map[sg.id] = "Médio"
        else:
            sg_risk_map[sg.id] = "Seguro"
            
    # Se nenhum risco foi encontrado, cria um DataFrame com mensagem positiva
    if not findings:
        findings_df = pd.DataFrame([{
            "Risco": "Parabéns!",
            "ID do Security Group": "Nenhum risco comum foi detectado."
        }])
    else:
        # Caso contrário, cria DataFrame com todos os achados detalhados
        findings_df = pd.DataFrame(findings)

    logging.info(f"Análise de segurança concluída. {len(findings)} riscos individuais encontrados.")
    # Retorna o DataFrame com achados e o mapa de risco para cada Security Group
    return findings_df, sg_risk_map
