import pandas as pd
import logging

# --- CRITÉRIOS DE RISCO ---
HIGH_RISK_PORTS = {22, 3389, 3306, 5432, 1433, 27017}
ACCEPTABLE_PUBLIC_PORTS = {80, 443}
ANYWHERE_CIDR = '0.0.0.0/0'

def analyze_sgs(sg_dataframe: pd.DataFrame):
    """
    Analisa um DataFrame bruto de Security Groups e retorna duas coisas:
    1. um DataFrame com os achados de risco (para a aba Security_Analysis).
    2. um dicionário mapeando cada SG ID ao seu nível de risco mais alto.
    """
    logging.info("Iniciando análise de segurança nos dados brutos de Security Groups...")
    findings = []
    sg_risk_map = {}

    if sg_dataframe.empty:
        logging.warning("DataFrame de Security Groups para análise está vazio.")
        # Retorna um DataFrame de 'Parabéns' e um mapa de riscos vazio
        findings_df = pd.DataFrame([{"Risco": "Parabéns!", "ID do Security Group": "Nenhum Security Group encontrado para análise."}])
        return findings_df, {}

    for _, sg_row in sg_dataframe.iterrows():
        sg_id = sg_row.get('GroupId')
        sg_name = sg_row.get('GroupName')
        highest_risk_level = 0  # 0: Seguro, 1: Médio, 2: Alto

        # --- ANÁLISE DE REGRAS DE ENTRADA (INBOUND) ---
        for rule in sg_row.get('IpPermissions', []):
            # Verifica se a regra permite tráfego de qualquer lugar do mundo
            is_open_to_world = any(ip_range.get('CidrIp') == ANYWHERE_CIDR for ip_range in rule.get('IpRanges', []))
            if not is_open_to_world:
                continue

            from_port = rule.get('FromPort')
            to_port = rule.get('ToPort')
            protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'Tudo')

            # Trata o caso de 'Todas as portas'
            if protocol == 'All' or from_port is None:
                highest_risk_level = max(highest_risk_level, 1) # Risco Médio
                findings.append({
                    "Risco": "Médio", "ID do Security Group": sg_id, "Nome do Grupo": sg_name,
                    "Regra Problemática": f"Entrada {protocol}:TODAS de {ANYWHERE_CIDR}",
                    "Recomendação": "Acesso de todas as portas liberado para a internet. Especifique as portas."
                })
                continue
            
            # "Explode" o range de portas para analisar cada uma
            for port in range(from_port, to_port + 1):
                rule_text = f"Entrada {protocol}:{port} de {ANYWHERE_CIDR}"
                # Checa por Risco ALTO
                if port in HIGH_RISK_PORTS:
                    highest_risk_level = max(highest_risk_level, 2)
                    findings.append({
                        "Risco": "Alto", "ID do Security Group": sg_id, "Nome do Grupo": sg_name,
                        "Regra Problemática": rule_text,
                        "Recomendação": "Acesso crítico (gerenciamento/BD) exposto à internet. RESTRINJA a origem."
                    })
                # Checa por Risco MÉDIO (qualquer outra porta que não seja web padrão)
                elif port not in ACCEPTABLE_PUBLIC_PORTS:
                    highest_risk_level = max(highest_risk_level, 1)
                    findings.append({
                        "Risco": "Médio", "ID do Security Group": sg_id, "Nome do Grupo": sg_name,
                        "Regra Problemática": rule_text,
                        "Recomendação": "Porta não-padrão exposta à internet. Verifique se é necessário."
                    })

        # --- ANÁLISE DE REGRAS DE SAÍDA (OUTBOUND) ---
        for rule in sg_row.get('IpPermissionsEgress', []):
            is_open_to_world = any(ip_range.get('CidrIp') == ANYWHERE_CIDR for ip_range in rule.get('IpRanges', []))
            protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All')
            if is_open_to_world and protocol == 'All':
                highest_risk_level = max(highest_risk_level, 1)
                findings.append({
                    "Risco": "Médio", "ID do Security Group": sg_id, "Nome do Grupo": sg_name,
                    "Regra Problemática": "Saída irrestrita para a internet (todas as portas)",
                    "Recomendação": "Permite acesso de saída irrestrito. Considere limitar se possível."
                })

        # Mapeia o resultado final de risco para o SG
        if highest_risk_level == 2:
            sg_risk_map[sg_id] = "Alto"
        elif highest_risk_level == 1:
            sg_risk_map[sg_id] = "Médio"
        else:
            sg_risk_map[sg_id] = "Seguro"
            
    # Cria o DataFrame final de achados
    if not findings:
        findings_df = pd.DataFrame([{"Risco": "Parabéns!", "ID do Security Group": "Nenhum risco comum foi detectado."}])
    else:
        findings_df = pd.DataFrame(findings)

    logging.info(f"Análise de segurança concluída. {len(findings)} riscos individuais encontrados.")
    return findings_df, sg_risk_map