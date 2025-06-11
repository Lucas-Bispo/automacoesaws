import logging
import os  # <-- A LINHA QUE FALTAVA
from openpyxl import load_workbook
from openpyxl.styles import Alignment, PatternFill, Font
from openpyxl.utils import get_column_letter

# (O resto do arquivo, com o LINKING_CONFIG e as definições de cores, permanece o mesmo)
# ...

def apply_final_formatting(input_path: str, output_path: str):
    """Lê um relatório, aplica toda a formatação final e salva o resultado."""
    logging.info(f"Aplicando formatação final em: {os.path.basename(input_path)}")
    try:
        workbook = load_workbook(input_path)
        
        # --- ETAPA 1: CRIAÇÃO DOS MAPAS DE IDS ---
        id_maps = {sheet.title: {str(cell.value): cell.row for cell in sheet['A'] if cell.value is not None} for sheet in workbook if sheet.max_row > 1}

        # --- ETAPA 2: APLICAÇÃO DOS HYPERLINKS ---
        for source_sheet_name, column_mappings in LINKING_CONFIG.items():
            if source_sheet_name in workbook.sheetnames:
                # (A lógica de hyperlinks que já temos vai aqui)
                # ...

        # --- ETAPA 3: COLORAÇÃO DA ABA DE SEGURANÇA ---
        if 'Security_Analysis' in workbook.sheetnames:
            # (A lógica de coloração que já temos vai aqui)
            # ...

        # --- ETAPA 4: LAYOUT GERAL ---
        for sheet in workbook:
            # (A lógica de ajuste de colunas e layout que já temos vai aqui)
            # ...

        workbook.save(output_path)
        logging.info(f"Relatório final formatado salvo em: {output_path}")

    except FileNotFoundError:
        logging.error(f"Arquivo de entrada para formatação não encontrado: {input_path}")
        raise
    except Exception as e:
        logging.error(f"Erro durante a formatação final: {e}", exc_info=True)
        raise

# (O código completo para as funções e loops omitidos acima é o mesmo da nossa última versão funcional)