import pandas as pd
import logging
from openpyxl.styles import PatternFill, Font

# --- CRITÉRIOS DE RISCO (Permanecem os mesmos) ---
HIGH_RISK_PORTS = {22, 3389, 3306, 5432, 1433, 27017}
ACCEPTABLE_PUBLIC_PORTS = {80, 443}
ANYWHERE_CIDR = '0.0.0.0/0'

# --- CORES E FONTES (Permanecem as mesmas) ---
RED_FILL = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
YELLOW_FILL = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
RED_FONT = Font(color="9C0006", bold=True)
YELLOW_FONT = Font(color="9C6500", bold=True)


def analyze_sgs_for_risks(sg_dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe um DataFrame JÁ NORMALIZADO de regras de Security Groups e retorna
    um DataFrame com a análise de risco.
    """
    logging.info("Iniciando análise de segurança na tabela de regras normalizada...")
    findings = []

    if sg_dataframe.empty:
        logging.warning("DataFrame de Security Groups está vazio. Nenhum risco a analisar.")
        return pd.DataFrame()

    # Itera por cada linha (cada regra individual) do DataFrame
    for index, rule_row in sg_dataframe.iterrows():
        direction = rule_row.get('Direction')
        source_dest = rule_row.get('SourceDest')
        port = rule_row.get('FromPort') # FromPort e ToPort são iguais na tabela normalizada
        
        # --- LÓGICA DE ANÁLISE APLICADA A CADA REGRA ---

        # 1. Análise de Regras de ENTRADA
        if direction == 'Inbound' and source_dest == ANYWHERE_CIDR:
            # Checa por Risco ALTO
            if port in HIGH_RISK_PORTS:
                finding = {
                    "Risco": "Alto",
                    "ID do Security Group": rule_row.get('GroupId'),
                    "Nome do Grupo": rule_row.get('GroupName'),
                    "Regra": f"Entrada {rule_row.get('Protocol')}:{port} de {source_dest}",
                    "Recomendação": "Acesso crítico (gerenciamento/BD) exposto à internet. RESTRINJA a origem."
                }
                findings.append(finding)
            # Checa por Risco MÉDIO (qualquer outra porta não-padrão)
            elif port is not None and port not in ACCEPTABLE_PUBLIC_PORTS:
                finding = {
                    "Risco": "Médio",
                    "ID do Security Group": rule_row.get('GroupId'),
                    "Nome do Grupo": rule_row.get('GroupName'),
                    "Regra": f"Entrada {rule_row.get('Protocol')}:{port} de {source_dest}",
                    "Recomendação": "Porta não-padrão exposta à internet. Verifique se é necessário e restrinja a origem."
                }
                findings.append(finding)

        # 2. Análise de Regras de SAÍDA
        elif direction == 'Outbound' and source_dest == ANYWHERE_CIDR and rule_row.get('Protocol') == 'All':
            finding = {
                "Risco": "Médio",
                "ID do Security Group": rule_row.get('GroupId'),
                "Nome do Grupo": rule_row.get('GroupName'),
                "Regra": "Saída irrestrita para a internet (todas as portas)",
                "Recomendação": "Permite que recursos internos acessem qualquer endereço. Considere limitar se não for necessário."
            }
            findings.append(finding)

    logging.info(f"Análise de regras concluída. {len(findings)} riscos individuais encontrados.")
    
    if not findings:
        # Mensagem para quando nenhum risco é encontrado
        return pd.DataFrame([{"Risco": "Parabéns!", "ID do Security Group": "Nenhum risco comum foi detectado.", "Nome do Grupo": "", "Regra": "", "Recomendação": ""}])
        
    return pd.DataFrame(findings)

def color_security_sheet(workbook):
    """Aplica cores na aba de análise de segurança já existente."""
    if 'Security_Analysis' not in workbook.sheetnames:
        return workbook

    sheet = workbook['Security_Analysis']
    try:
        # Encontra a coluna de Risco para aplicar a cor
        risk_col_idx = [cell.value for cell in sheet[1]].index('Risco') + 1
        for row_cells in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
            risk_cell = row_cells[risk_col_idx - 1]
            if risk_cell.value == 'Alto':
                for cell in row_cells: cell.fill = RED_FILL
                risk_cell.font = RED_FONT
            elif risk_cell.value == 'Médio':
                for cell in row_cells: cell.fill = YELLOW_FILL
                risk_cell.font = YELLOW_FONT
    except (ValueError, IndexError):
        logging.warning("Não foi possível aplicar cores na aba de Análise de Segurança.")
    
    return workbook