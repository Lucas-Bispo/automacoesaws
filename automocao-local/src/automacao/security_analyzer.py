import pandas as pd
import logging

# --- CRITÉRIOS DE RISCO ---
HIGH_RISK_PORTS = {22, 3389, 3306, 5432, 1433, 27017}
ACCEPTABLE_PUBLIC_PORTS = {80, 443}
ANYWHERE_CIDR = '0.0.0.0/0'

def analyze_sgs(sg_dataframe: pd.DataFrame):
    """
    Analisa um DataFrame SUMARIZADO de SGs (1 linha por grupo) e retorna
    um DataFrame de riscos e um mapa de risco por SG para coloração de linhas.
    """
    logging.info("Analisando dados sumarizados de Security Groups...")
    findings = []
    sg_risk_map = {}

    if sg_dataframe.empty:
        logging.warning("DataFrame de Security Groups para análise está vazio.")
        return pd.DataFrame([{"Risco": "Info", "ID do SG": "Nenhum SG encontrado."}]), {}

    for _, sg_row in sg_dataframe.iterrows():
        sg_id = sg_row.get('GroupId')
        if not sg_id: continue
        
        highest_risk_level = 0  # 0: Seguro, 1: Médio, 2: Alto

        # Analisa Regras de ENTRADA (Inbound) a partir dos dados brutos
        for rule in sg_row.get('IpPermissions', []):
            is_open_to_world = any(ip.get('CidrIp') == ANYWHERE_CIDR for ip in rule.get('IpRanges', []))
            if not is_open_to_world: continue

            from_port, to_port = rule.get('FromPort'), rule.get('ToPort')
            protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'Tudo')
            
            if from_port is not None and to_port is not None:
                for port in range(from_port, to_port + 1):
                    rule_text = f"Entrada {protocol}:{port} de {ANYWHERE_CIDR}"
                    if port in HIGH_RISK_PORTS:
                        highest_risk_level = max(highest_risk_level, 2)
                        findings.append({"Risco": "Alto", "ID do Security Group": sg_id, "Nome do Grupo": sg_row.get('GroupName'), "Regra Problemática": rule_text, "Recomendação": "Acesso crítico exposto. RESTRINJA a origem."})
                    elif port not in ACCEPTABLE_PUBLIC_PORTS:
                        highest_risk_level = max(highest_risk_level, 1)
                        findings.append({"Risco": "Médio", "ID do Security Group": sg_id, "Nome do Grupo": sg_row.get('GroupName'), "Regra Problemática": rule_text, "Recomendação": "Porta não-padrão exposta. Verifique a necessidade."})
        
        # Mapeia o resultado final de risco para o SG
        if highest_risk_level == 2: sg_risk_map[sg_id] = "Alto"
        elif highest_risk_level == 1: sg_risk_map[sg_id] = "Médio"
        else: sg_risk_map[sg_id] = "Seguro"
            
    findings_df = pd.DataFrame(findings) if findings else pd.DataFrame([{"Risco": "Parabéns!", "ID do Security Group": "Nenhum risco comum detectado."}])
    logging.info(f"Análise de segurança concluída. {len(findings)} riscos individuais encontrados.")
    return findings_df, sg_risk_map