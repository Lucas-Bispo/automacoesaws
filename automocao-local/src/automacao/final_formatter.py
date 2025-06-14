import logging
from openpyxl import load_workbook
from openpyxl.styles import Alignment, PatternFill, Font
from openpyxl.utils import get_column_letter

# --- MAPA DE LINKS FINAL ---
# Define como as abas devem se conectar umas com as outras
LINKING_CONFIG = {
    # Na aba 'Subnets', a coluna 'VpcId' deve linkar para a aba 'VPCs'
    'Subnets': {
        'VpcId': 'VPCs',
    },
    'SecurityGroups': {
        'VpcId': 'VPCs',
    },
    'RouteTables': {
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
    Recebe um objeto de workbook e o mapa de riscos, e aplica toda a formatação final.
    Retorna o workbook modificado, pronto para ser salvo.
    """
    logging.info("Aplicando formatação final completa (cores, links, layout)...")
    
    # ETAPA 1: CRIAÇÃO DOS MAPAS DE IDS PARA OS LINKS
    id_maps = {sheet.title: {str(cell.value): cell.row for cell in sheet['A'] if cell.value is not None} for sheet in workbook if sheet.max_row > 1}

    # ETAPA 2: APLICAÇÃO DOS HYPERLINKS
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
                                # Para células com múltiplos IDs (ex: "sg-1, sg-2"), linka apenas o primeiro
                                link_id = cell.value.split(',')[0].strip()
                                if link_id in target_map:
                                    target_row = target_map[link_id]
                                    link_location = f"#'{target_sheet_name}'!A{target_row}"
                                    cell.value = f'=HYPERLINK("{link_location}", "{cell.value}")'
                                    cell.style = "Hyperlink"
            except (ValueError, IndexError):
                 logging.warning(f"Não foi possível processar links para a aba '{source_sheet_name}'.")

    # ETAPA 3: COLORAÇÃO DAS ABAS
    # Colore as linhas da aba SecurityGroups com base no mapa de risco
    if 'SecurityGroups' in workbook.sheetnames and sg_risk_map:
        sheet = workbook['SecurityGroups']
        try:
            headers = [c.value for c in sheet[1]]
            sg_id_col_idx = headers.index('GroupId') + 1
            for row_cells in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
                sg_id = str(row_cells[sg_id_col_idx - 1].value)
                risk_level = sg_risk_map.get(sg_id, "Seguro")
                
                fill_style = {"Alto": RED_FILL, "Médio": YELLOW_FILL, "Seguro": GREEN_FILL}.get(risk_level)
                
                if fill_style:
                    for cell in row_cells:
                        cell.fill = fill_style
        except ValueError:
            logging.warning("Coluna 'GroupId' não encontrada para colorir linhas.")
            
    # Colore a aba de Análise de Segurança
    if 'Security_Analysis' in workbook.sheetnames:
        sheet = workbook['Security_Analysis']
        try:
            headers = [cell.value for cell in sheet[1]]
            risk_col_idx = headers.index('Risco') + 1
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

    # ETAPA 4: LAYOUT GERAL
    for sheet in workbook:
        for col in sheet.columns:
            max_length = 0
            column_letter = get_column_letter(col[0].column)
            for cell in col:
                cell.alignment = Alignment(wrap_text=True, vertical='top', horizontal='left')
                if cell.value:
                    cell_max_line = max(len(line) for line in str(cell.value).split('\n')) if str(cell.value) else 0
                    if cell_max_line > max_length: max_length = cell_max_line
            if max_length < 20: max_length = 20
            adjusted_width = (max_length + 2) * 1.1
            sheet.column_dimensions[column_letter].width = min(adjusted_width, 80)

    logging.info("Formatação final aplicada com sucesso.")
    return workbook