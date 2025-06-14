import logging
from openpyxl import load_workbook
from openpyxl.styles import Alignment, PatternFill, Font
from openpyxl.utils import get_column_letter

LINKING_CONFIG = {
    'Subnets': {'VpcId': 'VPCs'}, 'SecurityGroups': {'VpcId': 'VPCs'},
    'RouteTables': {'VpcId': 'VPCs'}, 'Security_Analysis': {'ID do Security Group': 'SecurityGroups'}
}
RED_FILL = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
YELLOW_FILL = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
GREEN_FILL = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')

def apply_final_formatting(workbook, sg_risk_map: dict):
    logging.info("Aplicando formatação final completa...")
    
    id_maps = {sheet.title: {str(cell.value): cell.row for cell in sheet['A'] if cell.value is not None} for sheet in workbook}

    # Aplica Hyperlinks
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
                            if cell.value and isinstance(cell.value, str) and cell.value in target_map:
                                cell.hyperlink = f"#'{target_sheet_name}'!A{target_map[cell.value]}"; cell.style = "Hyperlink"
            except (ValueError, IndexError):
                 logging.warning(f"Não foi possível processar links para a aba '{source_sheet_name}'.")

    # Colore linhas na aba SecurityGroups
    if 'SecurityGroups' in workbook.sheetnames and sg_risk_map:
        sheet = workbook['SecurityGroups']
        try:
            sg_id_col_idx = [c.value for c in sheet[1]].index('GroupId') + 1
            for row_cells in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
                sg_id = str(row_cells[sg_id_col_idx - 1].value)
                risk_level = sg_risk_map.get(sg_id, "Seguro")
                fill_style = {"Alto": RED_FILL, "Médio": YELLOW_FILL, "Seguro": GREEN_FILL}.get(risk_level)
                if fill_style:
                    for cell in row_cells: cell.fill = fill_style
        except ValueError:
            logging.warning("Coluna 'GroupId' não encontrada para colorir linhas.")

    # Ajusta Layout Geral
    for sheet in workbook:
        for col in sheet.columns:
            max_length = 0; column_letter = get_column_letter(col[0].column)
            for cell in col:
                cell.alignment = Alignment(wrap_text=True, vertical='top', horizontal='left')
                if cell.value:
                    max_length = max(max_length, max(len(line) for line in str(cell.value).split('\n')))
            sheet.column_dimensions[column_letter].width = min((max_length + 2) * 1.2, 70)

    logging.info("Formatação final aplicada.")
    return workbook