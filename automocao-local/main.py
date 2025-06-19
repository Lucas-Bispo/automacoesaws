import logging
import os
import re
import importlib
import boto3
from datetime import datetime

# Importa as funções de utilidade e as "Fábricas" de Relatório
from src.automacao.utils.logger import setup_logging
from src.automacao.utils.config import load_environment
from src.automacao.utils.credentials import validate_aws_credentials
from src.automacao.vpc.factory import VPCReport
from src.automacao.iam.factory import IAMReport

# --- CONSTANTES GLOBAIS ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- DICIONÁRIO DE RELATÓRIOS ---
# Mapeia a escolha do usuário para a fábrica correta e suas configurações
REPORTS = {
    "1": {
        "name": "VPC e Recursos Associados", 
        "factory": VPCReport, 
        "scope": "regional",
        "output_dir_name": "vpc",
        "output_prefix": "RELATORIO_VPC"
    },
    "2": {
        "name": "Análise de Segurança do IAM", 
        "factory": IAMReport,
        "scope": "global",
        "output_dir_name": "iam",
        "output_prefix": "RELATORIO_IAM"
    },
}

# --- FUNÇÕES DE AJUDA ---

def display_menu():
    """Mostra o menu de opções para o usuário."""
    print("\n+-------------------------------------------------------------+")
    print("|                MENU DE RELATÓRIOS AWS                     |")
    print("+-------------------------------------------------------------+")
    for key, value in REPORTS.items():
        print(f"  [{key}] - {value['name']}")
    print("  [q] - Sair")
    print("+-------------------------------------------------------------+")

def get_next_run_number(output_dir: str, report_prefix: str) -> int:
    """Escaneia um diretório e retorna o próximo número de execução sequencial."""
    os.makedirs(output_dir, exist_ok=True)
    max_run_num = 0
    pattern = re.compile(f"^{report_prefix}_(\\d+)_.*")
    for filename in os.listdir(output_dir):
        match = pattern.match(filename)
        if match:
            run_num = int(match.group(1))
            if run_num > max_run_num:
                max_run_num = run_num
    return max_run_num + 1

def find_active_vpc_regions(session):
    """Varre todas as regiões para encontrar aquelas que têm VPCs em uso."""
    logging.info("Iniciando varredura em todas as regiões para encontrar VPCs ativas...")
    active_regions = []
    try:
        ec2_global = session.client('ec2', region_name='us-east-1')
        all_regions = [region['RegionName'] for region in ec2_global.describe_regions(AllRegions=False)['Regions']]
        
        for region_name in all_regions:
            logging.info(f"Sondando região: {region_name}...")
            try:
                ec2_regional = session.client('ec2', region_name=region_name)
                custom_vpcs = ec2_regional.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['false']}]).get('Vpcs', [])
                if custom_vpcs:
                    logging.info(f"-> Região ATIVA encontrada (VPC customizada): {region_name}")
                    active_regions.append(region_name)
            except Exception as e:
                logging.warning(f"Não foi possível sondar a região {region_name}. Erro: {e}.")
    except Exception as e:
        logging.error(f"Não foi possível buscar a lista de regiões da AWS: {e}.")
        
    logging.info(f"Análise concluída. Regiões com VPCs em uso: {active_regions}")
    return active_regions

# --- FUNÇÃO PRINCIPAL (O ORQUESTRADOR) ---

def main():
    setup_logging()
    load_environment()
    if not validate_aws_credentials(): return

    while True:
        display_menu()
        choice = input("Por favor, escolha uma opção e pressione Enter: ").strip()

        if choice.lower() == 'q':
            logging.info("Encerrando o programa."); break
        
        if choice in REPORTS:
            report_config = REPORTS[choice]
            
            output_dir = os.path.join(PROJECT_ROOT, "output", report_config["output_dir_name"])
            run_number = get_next_run_number(output_dir, report_config["output_prefix"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path_final = os.path.join(output_dir, f"{report_config['output_prefix']}_{run_number}_{timestamp}.xlsx")

            logging.info(f"Gerando Relatório: '{report_config['name']}' (Execução #{run_number})")
            
            try:
                report_factory = None
                
                # Lógica para serviços REGIONAIS
                if report_config.get("scope") == "regional":
                    active_regions = find_active_vpc_regions(boto3.Session())
                    if not active_regions:
                        logging.warning("Nenhuma região ativa para escanear. Encerrando execução.")
                        break
                    report_factory = report_config["factory"](regions_to_scan=active_regions)
                
                # Lógica para serviços GLOBAIS
                else:
                    report_factory = report_config["factory"]()
                
                # Executa o pipeline em memória e gera o relatório final
                report_factory.collect_data().analyze_security().generate_report(output_path=path_final)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {path_final}")
            except Exception as e:
                logging.critical(f"A automação foi interrompida por um erro: {e}", exc_info=True)
            
            break
        else:
            print("\nOpção inválida!")

if __name__ == "__main__":
    main()