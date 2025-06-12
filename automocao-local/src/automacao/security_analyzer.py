import logging
import os  # <-- A LINHA QUE FALTAVA
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font

# --- CRITÉRIOS DE RISCO ---
HIGH_RISK_PORTS = {22, 3389, 3306, 5432, 1433, 27017}
ACCEPTABLE_PUBLIC_PORTS = {80, 443}
ANYWHERE_CIDR = '0.0.0.0/0'

# --- CORES E FONTES ---
RED_FILL = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
YELLOW_FILL = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
RED_FONT = Font(color="9C0006", bold=True)
YELLOW_FONT = Font(color="9C6500", bold=True)


def analyze_sgs_for_risks(sg_dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe um DataFrame JÁ NORMALIZADO de regras de Security Groups e retorna
    um DataFrame com a análise de risco granular.
    """
    logging.info("Iniciando análise de segurança granular (porta a porta)...")
    findings = []

    if sg_dataframe.empty:
        logging.warning("DataFrame de Security Groups está vazio. Nenhum risco a analisar.")
        return pd.DataFrame()

    for index, rule_row in sg_dataframe.iterrows():
        direction = rule_row.get('Direction')
        source_dest = rule_row.get('SourceDest')
        port = rule_row.get('FromPort')
        protocol = rule_row.get('Protocol')

        # Análise de Regras de ENTRADA
        if direction == 'Inbound' and source_dest == ANYWHERE_CIDR:
            # Risco ALTO
            if port in HIGH_RISK_PORTS:
                findings.append({
                    "Risco": "Alto", "ID do Security Group": rule_row.get('GroupId'),
                    "Nome do Grupo": rule_row.get('GroupName'), "Regra": f"Entrada {protocol}:{port} de {source_dest}",
                    "Recomendação": "Acesso crítico (gerenciamento/BD) exposto à internet. RESTRINJA a origem."
                })
            # Risco MÉDIO
            elif port is not None and port not in ACCEPTABLE_PUBLIC_PORTS:
                findings.append({
                    "Risco": "Médio", "ID do Security Group": rule_row.get('GroupId'),
                    "Nome do Grupo": rule_row.get('GroupName'), "Regra": f"Entrada {protocol}:{port} de {source_dest}",
                    "Recomendação": "Porta não-padrão exposta à internet. Verifique se é necessário."
                })

        # Análise de Regras de SAÍDA
        elif direction == 'Outbound' and source_dest == ANYWHERE_CIDR and protocol == 'All':
            findings.append({
                "Risco": "Médio", "ID do Security Group": rule_row.get('GroupId'),
                "Nome do Grupo": rule_row.get('GroupName'), "Regra": "Saída irrestrita para a internet (todas as portas)",
                "Recomendação": "Permite acesso irrestrito de saída. Considere limitar se não for necessário."
            })

    logging.info(f"Análise granular concluída. {len(findings)} riscos individuais encontrados.")
    if not findings:
        return pd.DataFrame([{"Risco": "Parabéns!", "ID do Security Group": "Nenhum risco comum foi detectado.", "Nome do Grupo": "", "Regra": "", "Recomendação": ""}])
        
    return pd.DataFrame(findings)


def analyze_security_report(input_path: str, output_path: str):
    """Lê um relatório bruto, adiciona a aba de análise e salva em um novo arquivo."""
    logging.info(f"Analisando segurança do arquivo: {os.path.basename(input_path)}")
    try:
        # Abordagem robusta: lê todas as abas, adiciona a nova e salva tudo.
        with pd.ExcelFile(input_path) as xls:
            all_sheets = {sheet_name: pd.read_excel(xls, sheet_name=sheet_name) for sheet_name in xls.sheet_names}
        
        sg_df = all_sheets.get('SecurityGroups', pd.DataFrame())
        findings_df = analyze_sgs_for_risks(sg_dataframe=sg_df)
        
        # Adiciona a nova aba de análise ao dicionário de planilhas
        all_sheets['Security_Analysis'] = findings_df

        # Salva tudo no arquivo de saída
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Escreve a aba de análise primeiro
            all_sheets['Security_Analysis'].to_excel(writer, sheet_name='Security_Analysis', index=False)
            for sheet_name, df in all_sheets.items():
                if sheet_name != 'Security_Analysis':
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

        logging.info(f"Relatório analisado salvo em: {output_path}")

    except FileNotFoundError:
        logging.error(f"Arquivo de entrada para análise não encontrado: {input_path}")
        raise
    except Exception as e:
        logging.error(f"Erro inesperado durante a análise de segurança: {e}", exc_info=True)
        raise