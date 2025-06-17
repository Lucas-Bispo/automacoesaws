import pandas as pd
import logging

# --- CRITÉRIOS DE RISCO ---
HIGH_RISK_PORTS = {22, 3389, 3306, 5432, 1433, 27017}
ACCEPTABLE_PUBLIC_PORTS = {80, 443}
ANYWHERE_CIDR = '0.0.0.0/0'

def analyze_sgs(security_groups: list):
    """
    Analisa uma LISTA de objetos SecurityGroup e retorna um DataFrame de riscos
    e um mapa de risco por SG para coloração.
    """
    logging.info("Analisando objetos Security Group para riscos...")
    findings = []
    sg_risk_map = {}

    for sg in security_groups:
        highest_risk_level = 0  # 0: Seguro, 1: Médio, 2: Alto

        # Analisa Regras de ENTRADA (Inbound) a partir dos dados brutos do objeto
        for rule in sg.raw_rules.get('IpPermissions', []):
            is_open_to_world = any(ip_range.get('CidrIp') == ANYWHERE_CIDR for ip_range in rule.get('IpRanges', []))
            if not is_open_to_world:
                continue

            from_port = rule.get('FromPort')
            to_port = rule.get('ToPort')
            protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All')
            
            # Se for 'Todas as portas', classifica como risco médio
            if protocol == 'All' or from_port is None:
                highest_risk_level = max(highest_risk_level, 1)
                findings.append({
                    "Risco": "Médio",
                    "ID do Security Group": sg.id,
                    "Nome do Grupo": sg.name,
                    "Regra Problemática": f"Entrada {protocol}:TODAS de {ANYWHERE_CIDR}",
                    "Recomendação": "Acesso de todas as portas liberado para a internet. Especifique as portas necessárias."
                })
                continue
            
            # "Explode" o range de portas para analisar cada uma individualmente
            for port in range(from_port, to_port + 1):
                rule_text = f"Entrada {protocol}:{port} de {ANYWHERE_CIDR}"
                # Checa por Risco ALTO
                if port in HIGH_RISK_PORTS:
                    highest_risk_level = max(highest_risk_level, 2)
                    findings.append({
                        "Risco": "Alto", "ID do Security Group": sg.id,
                        "Nome do Grupo": sg.name, "Regra Problemática": rule_text,
                        "Recomendação": "Acesso crítico (gerenciamento/BD) exposto à internet. RESTRINJA a origem."
                    })
                # Checa por Risco MÉDIO (qualquer outra porta que não seja web padrão)
                elif port not in ACCEPTABLE_PUBLIC_PORTS:
                    highest_risk_level = max(highest_risk_level, 1)
                    findings.append({
                        "Risco": "Médio", "ID do Security Group": sg.id,
                        "Nome do Grupo": sg.name, "Regra Problemática": rule_text,
                        "Recomendação": "Porta não-padrão exposta à internet. Verifique a necessidade."
                    })

        # Mapeia o resultado final de risco para o SG ID
        if highest_risk_level == 2:
            sg_risk_map[sg.id] = "Alto"
        elif highest_risk_level == 1:
            sg_risk_map[sg.id] = "Médio"
        else:
            sg_risk_map[sg.id] = "Seguro"
            
    # Cria o DataFrame final de achados
    if not findings:
        findings_df = pd.DataFrame([{"Risco": "Parabéns!", "ID do Security Group": "Nenhum risco comum foi detectado."}])
    else:
        findings_df = pd.DataFrame(findings)

    logging.info(f"Análise de segurança concluída. {len(findings)} riscos individuais encontrados.")
    return findings_df, sg_risk_map