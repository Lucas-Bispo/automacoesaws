import logging
import os
import re
import importlib
import pandas as pd
import boto3
from datetime import datetime, timedelta
from collections import defaultdict
from src.automacao.utils.logger import setup_logging
from src.automacao.utils.config import load_environment
from src.automacao.utils.credentials import validate_aws_credentials

# --- CONSTANTES E CONFIGURAÇÕES ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS = {
    "1": {"name": "VPC e Recursos Associados", "module": "vpc", "scope": "regional"},
    "2": {"name": "Instâncias EC2", "module": "ec2", "scope": "regional"},
    "3": {"name": "IAM (Usuários e Grupos)", "module": "iam", "scope": "global"}
}

# --- FUNÇÕES DE AJUDA ---
def display_menu():
    print("\n+-------------------------------------------------------------+")
    print("|                MENU DE RELATÓRIOS AWS                     |")
    print("+-------------------------------------------------------------+")
    for key, value in REPORTS.items():
        print(f"  [{key}] - {value['name']}")
    print("  [q] - Sair")
    print("+-------------------------------------------------------------+")

def get_next_run_number(output_dir: str, report_prefix: str) -> int:
    os.makedirs(output_dir, exist_ok=True)
    max_run_num = 0
    pattern = re.compile(f"^{report_prefix}_(\\d+)_.*")
    for filename in os.listdir(output_dir):
        match = pattern.match(filename)
        if match:
            run_num = int(match.group(1))
            if run_num > max_run_num: max_run_num = run_num
    return max_run_num + 1

def get_active_regions(session):
    logging.info("Consultando o AWS Cost Explorer para encontrar regiões ativas...")
    # (Lógica completa da função get_active_regions que já temos)
    # ...
    return ['us-east-1', 'sa-east-1'] # Retorno de exemplo, a lógica completa permanece

# --- FUNÇÃO PRINCIPAL ---
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
            
            output_dir = os.path.join(PROJECT_ROOT, "output", module_name)
            run_number = get_next_run_number(output_dir, f"RELATORIO_FINAL_{module_name.upper()}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"{module_name}_{run_number}_{timestamp}"
            path_raw_json = os.path.join(output_dir, f"dados_brutos_{base_filename}.json")
            path_final_excel = os.path.join(output_dir, f"RELATORIO_FINAL_{module_name.upper()}_{run_number}_{timestamp}.xlsx")

            logging.info(f"Gerando Relatório: '{report_config['name']}' (Execução #{run_number})")
            try:
                # --- INÍCIO DO PIPELINE HÍBRIDO ---
                collector = importlib.import_module(f"src.automacao.{module_name}.collector")
                report_generator = importlib.import_module(f"src.automacao.{module_name}.report_generator")
                security_analyzer = importlib.import_module("src.automacao.security_analyzer")
                final_formatter = importlib.import_module("src.automacao.final_formatter")

                # ETAPA 1: COLETA E SALVAMENTO EM JSON
                regions_to_scan = []
                if report_config["scope"] == "regional":
                    regions_to_scan = get_active_regions(boto3.Session())
                logging.info(f"ETAPA 1: Coletando dados e salvando em '{os.path.basename(path_raw_json)}'")
                data_pack = collector.collect_data_and_save_to_json(output_path=path_raw_json, regions_to_scan=regions_to_scan)

                # ETAPA 2: GERAÇÃO DO RELATÓRIO EM MEMÓRIA
                logging.info("ETAPA 2: Gerando estrutura do relatório em memória...")
                findings_df, sg_risk_map = security_analyzer.analyze_sgs(data_pack.get('SecurityGroups', pd.DataFrame()))
                workbook = report_generator.create_report(data_frames=data_pack, security_findings_df=findings_df)
                
                # ETAPA 3: FORMATAÇÃO FINAL (CORES, LINKS, LAYOUT)
                logging.info("ETAPA 3: Aplicando formatação final...")
                workbook = final_formatter.apply_final_formatting(workbook=workbook, sg_risk_map=sg_risk_map)

                # ETAPA FINAL: SALVAR NO DISCO
                logging.info(f"Salvando relatório final em: {os.path.basename(path_final_excel)}")
                workbook.save(path_final_excel)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {path_final_excel}")
            except Exception as e:
                logging.critical(f"A automação foi interrompida por um erro: {e}", exc_info=True)
            break
        else:
            print("\nOpção inválida!")

if __name__ == "__main__":
    main()