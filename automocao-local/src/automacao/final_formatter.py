import logging
from openpyxl import load_workbook
from openpyxl.styles import Alignment, PatternFill, Font
from openpyxl.utils import get_column_letter

# --- MAPA DE LINKS DEFINITIVO E COMPLETO ---
# 'Aba Origem': {'Coluna com o ID a ser linkada': 'Aba de Destino'}
LINKING_CONFIG = {
    'Subnets': {
        'VpcId': 'VPCs',
        'AssociatedRouteTable': 'RouteTables',
        'AssociatedNetworkACL': 'NetworkACLs'
    },
    'SecurityGroups': {
        'VpcId': 'VPCs',
        'SourceDest': 'SecurityGroups' # Para regras que apontam para outro SG
    },
    'RouteTables': {
        'VpcId': 'VPCs',
        'Target': 'InternetGateways' # Linka rotas para o IGW, por exemplo
    },
    'NetworkACLs': {
        'VpcId': 'VPCs',
    },
    'Security_Analysis': {
        'ID do Security Group': 'SecurityGroups'
    }
}

# --- CORES E FONTES PARA ANÁLISE E FORMATAÇÃO ---
RED_FILL = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
YELLOW_FILL = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
GREEN_FILL = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
RED_FONT = Font(color="9C0006", bold=True)
YELLOW_FONT = Font(color="9C6500", bold=True)
GREEN_FONT = Font(color="006100", bold=True)


def apply_final_formatting(workbook, sg_risk_map: dict):
    """
    Recebe um objeto de workbook e o mapa de riscos, e aplica toda a formatação final:
    cores, hyperlinks, alinhamento e ajuste de colunas.
    """
    logging.info("Aplicando formatação final completa (cores, links globais, layout)...")
    
    # --- ETAPA 1: CRIAÇÃO DOS MAPAS DE IDS PARA OS LINKS ---
    id_maps = {}
    for sheet in workbook:
        # A convenção é que a primeira coluna (A) de cada aba contém o ID principal do recurso
        if sheet.max_row > 1:
            id_maps[sheet.title] = {str(cell.value): cell.row for cell in sheet['A'] if cell.value is not None}

    # --- ETAPA 2: APLICAÇÃO DOS HYPERLINKS ---
    for source_sheet_name, column_mappings in LINKING_CONFIG.items():
        if source_sheet_name in workbook.sheetnames:
            sheet = workbook[source_sheet_name]
            try:
                headers = [cell.value for cell in sheet[1]]
                for source_col_name, target_sheet_name in column_mappings.items():
                    if source_col_name in headers and target_sheet_name in id_maps:
                        col_idx = headers.index(source_col_name) + 1
                        target_map = id_maps[target_sheet_name]
                        
                        for row_num in range(2, sheet.max_row + 1):
                            cell = sheet.cell(row=row_num, column=col_idx)
                            if cell.value and isinstance(cell.value, str):
                                link_id = cell.value.strip()
                                if link_id in target_map:
                                    target_row = target_map[link_id]
                                    link_location = f"#'{target_sheet_name}'!A{target_row}"
                                    cell.value = f'=HYPERLINK("{link_location}", "{cell.value}")'
                                    cell.style = "Hyperlink"
            except (ValueError, IndexError):
                 logging.warning(f"Não foi possível processar links para a aba '{source_sheet_name}'.")

    # --- ETAPA 3: COLORAÇÃO DAS ABAS (SecurityGroups e Security_Analysis) ---
    if 'Security_Analysis' in workbook.sheetnames:
        sheet = workbook['Security_Analysis']
        try:
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
            logging.warning("Não foi possível formatar cores na aba de Análise de Segurança.")

    if 'SecurityGroups' in workbook.sheetnames and sg_risk_map:
        sheet = workbook['SecurityGroups']
        try:
            sg_id_col_idx = [c.value for c in sheet[1]].index('GroupId') + 1
            for row_cells in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
                sg_id = str(row_cells[sg_id_col_idx - 1].value)
                risk_level = sg_risk_map.get(sg_id, "Seguro")
                
                fill_style = None
                if risk_level == 'Alto': fill_style = RED_FILL
                elif risk_level == 'Médio': fill_style = YELLOW_FILL
                elif risk_level == 'Seguro': fill_style = GREEN_FILL
                
                if fill_style:
                    for cell in row_cells:
                        cell.fill = fill_style
        except ValueError:
            logging.warning("Coluna 'GroupId' não encontrada na aba SecurityGroups para colorir.")

    # --- ETAPA 4: LAYOUT GERAL (AJUSTE DE COLUNAS E ALINHAMENTO) ---
    for sheet in workbook:
        for col in sheet.columns:
            max_length = 0
            column_letter = get_column_letter(col[0].column)
            for cell in col:
                cell.alignment = Alignment(wrap_text=True, vertical='top', horizontal='left')
                if cell.value and "HYPERLINK" not in str(cell.value):
                    cell_max_line = max(len(line) for line in str(cell.value).split('\n'))
                    if cell_max_line > max_length: max_length = cell_max_line
            if max_length < 15: max_length = 15
            adjusted_width = (max_length + 2) * 1.1
            sheet.column_dimensions[column_letter].width = min(adjusted_width, 80)

    logging.info("Formatação final aplicada com sucesso.")
    return workbook