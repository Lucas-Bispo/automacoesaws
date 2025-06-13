import pandas as pd
import logging
from openpyxl.styles import PatternFill, Font

# --- CRITÉRIOS DE RISCO ---
HIGH_RISK_PORTS = {22, 3389, 3306, 5432, 1433, 27017}
ACCEPTABLE_PUBLIC_PORTS = {80, 443}
ANYWHERE_CIDR = '0.0.0.0/0'

def analyze_sgs(sg_dataframe: pd.DataFrame):
    """
    Analisa um DataFrame sumarizado de SGs e retorna um DataFrame de riscos
    e um mapa de risco por SG para coloração.
    """
    logging.info("Iniciando análise de segurança nos dados brutos de Security Groups...")
    findings = []
    sg_risk_map = {}

    # Bloco de verificação para o caso de nenhum SG ser encontrado
    if sg_dataframe.empty:
        logging.warning("DataFrame de Security Groups para análise está vazio.")
        findings_df = pd.DataFrame([{"Risco": "Info", "ID do Security Group": "Nenhum Security Group encontrado para análise."}])
        return findings_df, {}

    # Itera por cada SG (cada linha do DataFrame)
    for _, sg_row in sg_dataframe.iterrows():
        sg_id = sg_row.get('GroupId')
        if not sg_id:
            continue
        
        highest_risk_level = 0  # 0: Seguro, 1: Médio, 2: Alto

        # Analisa Regras de ENTRADA (Inbound)
        for rule in sg_row.get('IpPermissions', []):
            is_open_to_world = any(ip_range.get('CidrIp') == ANYWHERE_CIDR for ip_range in rule.get('IpRanges', []))
            if not is_open_to_world:
                continue

            from_port = rule.get('FromPort')
            to_port = rule.get('ToPort')
            protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'Tudo')
            
            # Se for 'Todas as portas', é risco médio
            if protocol == 'All' or from_port is None:
                highest_risk_level = max(highest_risk_level, 1)
                findings.append({
                    "Risco": "Médio", "ID do Security Group": sg_id, "Nome do Grupo": sg_row.get('GroupName'),
                    "Regra Problemática": f"Entrada {protocol}:TODAS de {ANYWHERE_CIDR}",
                    "Recomendação": "Acesso de todas as portas liberado para a internet. Especifique as portas."
                })
                continue
            
            # "Explode" o range de portas para analisar cada uma
            for port in range(from_port, to_port + 1):
                rule_text = f"Entrada {protocol}:{port} de {ANYWHERE_CIDR}"
                if port in HIGH_RISK_PORTS:
                    highest_risk_level = max(highest_risk_level, 2)
                    findings.append({
                        "Risco": "Alto", "ID do Security Group": sg_id, "Nome do Grupo": sg_row.get('GroupName'),
                        "Regra Problemática": rule_text,
                        "Recomendação": "Acesso crítico (gerenciamento/BD) exposto à internet. RESTRINJA a origem."
                    })
                elif port not in ACCEPTABLE_PUBLIC_PORTS:
                    highest_risk_level = max(highest_risk_level, 1)
                    findings.append({
                        "Risco": "Médio", "ID do Security Group": sg_id, "Nome do Grupo": sg_row.get('GroupName'),
                        "Regra Problemática": rule_text,
                        "Recomendação": "Porta não-padrão exposta à internet. Verifique a necessidade."
                    })

        # Analisa Regras de SAÍDA (Outbound)
        for rule in sg_row.get('IpPermissionsEgress', []):
            is_open_to_world = any(ip_range.get('CidrIp') == ANYWHERE_CIDR for ip_range in rule.get('IpRanges', []))
            protocol = str(rule.get('IpProtocol', '-1')).upper().replace('-1', 'All')
            if is_open_to_world and protocol == 'All':
                highest_risk_level = max(highest_risk_level, 1)
                findings.append({
                    "Risco": "Médio", "ID do Security Group": sg_id, "Nome do Grupo": sg_row.get('GroupName'),
                    "Regra Problemática": "Saída irrestrita para a internet",
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