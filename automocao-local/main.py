import logging
import os
import re
from datetime import datetime
import boto3
from src.automacao.utils.logger import setup_logging
from src.automacao.utils.config import load_environment
from src.automacao.utils.credentials import validate_aws_credentials
from src.automacao.vpc.factory import VPCReport

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS = {"1": {"name": "VPC e Recursos Associados", "factory": VPCReport, "output_dir_name": "vpc"}}

def display_menu():
    # ... (código completo da função display_menu) ...

def get_next_run_number(output_dir: str, report_prefix: str) -> int:
    # ... (código completo da função get_next_run_number) ...

def find_active_vpc_regions(session):
    # ... (código completo da função find_active_vpc_regions) ...

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
            output_dir = os.path.join(PROJECT_ROOT, "output", report_config["output_dir_name"])
            run_number = get_next_run_number(output_dir, f"RELATORIO_FINAL_{report_config['output_dir_name'].upper()}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path_final = os.path.join(output_dir, f"RELATORIO_FINAL_{report_config['output_dir_name'].upper()}_{run_number}_{timestamp}.xlsx")

            logging.info(f"Gerando Relatório: '{report_config['name']}' (Execução #{run_number})")
            try:
                active_regions = find_active_vpc_regions(boto3.Session())
                if not active_regions: logging.info("Nenhuma região ativa para escanear."); break
                
                report_factory = report_config["factory"](regions_to_scan=active_regions)
                report_factory.collect_data().analyze_security().generate_report(output_path=path_final)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {path_final}")
            except Exception as e:
                logging.critical(f"A automação foi interrompida: {e}", exc_info=True)
            break
        else: print("\nOpção inválida!")

if __name__ == "__main__": main()