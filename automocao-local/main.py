import logging
import os
import re # Biblioteca para expressões regulares, para encontrar o número no nome do arquivo
import importlib
import pandas as pd
import time
from datetime import datetime
from src.automacao.utils.logger import setup_logging
from src.automacao.utils.config import load_environment
from src.automacao.utils.credentials import validate_aws_credentials

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS = {
    "1": {"name": "VPC e Recursos Associados", "module": "vpc"},
    "2": {"name": "Instâncias EC2", "module": "ec2"},
    "3": {"name": "IAM (Usuários e Grupos)", "module": "iam"}
}

def display_menu():
    # ... (código do menu não muda) ...
    print("\n+-------------------------------------------------------------+")
    print("|                MENU DE RELATÓRIOS AWS                     |")
    print("+-------------------------------------------------------------+")
    for key, value in REPORTS.items():
        print(f"  [{key}] - {value['name']}")
    print("  [q] - Sair")
    print("+-------------------------------------------------------------+")

def get_next_run_number(output_dir: str, report_prefix: str) -> int:
    """
    Escaneia um diretório para encontrar o maior número de execução
    e retorna o próximo número sequencial.
    """
    os.makedirs(output_dir, exist_ok=True)
    max_run_num = 0
    # Padrão para encontrar o número de execução, ex: RELATORIO_FINAL_VPC_1_...
    pattern = re.compile(f"^{report_prefix}_(\\d+)_.*")
    
    for filename in os.listdir(output_dir):
        match = pattern.match(filename)
        if match:
            run_num = int(match.group(1))
            if run_num > max_run_num:
                max_run_num = run_num
    
    return max_run_num + 1

def main():
    setup_logging()
    load_environment()
    if not validate_aws_credentials(): return

    while True:
        display_menu()
        choice = input("Por favor, escolha uma opção e pressione Enter: ").strip()

        if choice.lower() == 'q': break

        if choice in REPORTS:
            report_config = REPORTS[choice]
            module_name = report_config["module"]
            
            # --- LÓGICA DE NOMENCLATURA DE ARQUIVOS ATUALIZADA ---
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(PROJECT_ROOT, "output", module_name)
            
            # Determina o próximo número de execução
            run_number = get_next_run_number(output_dir, f"RELATORIO_FINAL_{module_name.upper()}")
            
            # Cria os nomes de arquivo com o número e o timestamp
            base_filename = f"{module_name}_{run_number}_{timestamp}"
            path_raw_json = os.path.join(output_dir, f"dados_brutos_{base_filename}.json")
            path_analyzed = os.path.join(output_dir, f"relatorio_analisado_{base_filename}.xlsx")
            path_final = os.path.join(output_dir, f"RELATORIO_FINAL_{module_name.upper()}_{run_number}_{timestamp}.xlsx")

            logging.info(f"Gerando Relatório: '{report_config['name']}' (Execução #{run_number})")
            try:
                # O resto do pipeline funciona como antes, apenas usando os novos nomes de arquivo
                
                # ETAPA 1: COLETA E ESCRITA EM JSON
                from src.automacao.vpc import collector as vpc_collector # Exemplo para VPC
                logging.info(f"ETAPA 1: Coletando dados e salvando em '{os.path.basename(path_raw_json)}'")
                vpc_collector.collect_and_save_as_json(output_path=path_raw_json)
                
                # ETAPA 2: GERAÇÃO DA PLANILHA EXCEL BASE
                from src.automacao.vpc import report_generator as vpc_report_generator
                logging.info(f"ETAPA 2: Gerando planilha Excel base em '{os.path.basename(path_analyzed)}'")
                vpc_report_generator.create_report_from_json(input_json_path=path_raw_json, output_excel_path=path_analyzed)
                time.sleep(1)

                # ETAPA 3: FORMATAÇÃO FINAL (Análise de Segurança está implícita na geração)
                from src.automacao.final_formatter import apply_final_formatting
                logging.info(f"ETAPA 3: Aplicando formatação final e salvando em '{os.path.basename(path_final)}'")
                apply_final_formatting(input_path=path_analyzed, output_path=path_final)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {path_final}")

            except Exception as e:
                logging.critical(f"A automação foi interrompida por um erro: {e}", exc_info=True)
            
            break
        else:
            print("\nOpção inválida!")

if __name__ == "__main__":
    main()