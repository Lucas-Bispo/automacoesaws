import logging
import os
import re
import importlib
import time
import boto3
from datetime import datetime

from src.automacao.utils.logger import setup_logging
from src.automacao.utils.config import load_environment
from src.automacao.utils.credentials import validate_aws_credentials

# --- CONSTANTES GLOBAIS ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS = {
    "1": {"name": "VPC e Recursos Associados", "module": "vpc", "scope": "regional"},
    # Futuramente, podemos adicionar outros relatórios aqui
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
    """
    Varre todas as regiões para encontrar aquelas que têm VPCs em uso,
    verificando por VPCs customizadas ou recursos (instâncias EC2) na VPC padrão.
    """
    logging.info("Iniciando varredura em todas as regiões para encontrar VPCs ativas...")
    ec2_global = session.client('ec2', region_name='us-east-1')
    try:
        all_regions = [region['RegionName'] for region in ec2_global.describe_regions(AllRegions=False)['Regions']]
    except Exception as e:
        logging.error(f"Não foi possível buscar a lista de regiões da AWS: {e}.")
        return []
    
    active_regions = []
    for region_name in all_regions:
        logging.info(f"Sondando região: {region_name}...")
        try:
            ec2_regional = session.client('ec2', region_name=region_name)
            vpcs = ec2_regional.describe_vpcs().get('Vpcs', [])
            
            if not vpcs:
                continue

            # Se há mais de uma VPC, ou se a única VPC não é a padrão, a região está ativa.
            if len(vpcs) > 1 or not vpcs[0].get('IsDefault', False):
                logging.info(f"-> Região ATIVA encontrada (VPC customizada): {region_name}")
                active_regions.append(region_name)
                continue
            
            # Se há apenas a VPC Padrão, verifica se há instâncias EC2 nela para confirmar o uso.
            instances = ec2_regional.describe_instances(
                Filters=[{'Name': 'vpc-id', 'Values': [vpcs[0]['VpcId']]}]
            ).get('Reservations', [])

            if instances:
                logging.info(f"-> Região ATIVA encontrada (recursos na VPC Padrão): {region_name}")
                active_regions.append(region_name)

        except Exception as e:
            logging.warning(f"Não foi possível sondar a região {region_name}. Erro: {e}. Pulando região.")
            continue
            
    if not active_regions:
        logging.warning("Nenhuma região com VPCs ativas foi encontrada com base nos critérios.")
    else:
        logging.info(f"Análise concluída. Regiões com VPCs em uso: {active_regions}")
        
    return active_regions

# --- FUNÇÃO PRINCIPAL (O ORQUESTRADOR) ---

def main():
    """Função principal que orquestra a automação interativa."""
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
            
            # --- Geração de Nomes de Arquivo para o Pipeline ---
            output_dir = os.path.join(PROJECT_ROOT, "output", module_name)
            run_number = get_next_run_number(output_dir, f"RELATORIO_FINAL_{module_name.upper()}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"{module_name}_{run_number}_{timestamp}"
            
            path_raw_json = os.path.join(output_dir, f"1_dados_brutos_{base_filename}.json")
            path_base_excel = os.path.join(output_dir, f"2_relatorio_base_{base_filename}.xlsx")
            path_analyzed = os.path.join(output_dir, f"3_relatorio_analisado_{base_filename}.xlsx")
            path_final = os.path.join(output_dir, f"RELATORIO_FINAL_{module_name.upper()}_{run_number}_{timestamp}.xlsx")

            logging.info(f"Gerando Relatório: '{report_config['name']}' (Execução #{run_number})")
            
            try:
                # --- INÍCIO DO PIPELINE SEQUENCIAL ---
                regions_to_scan = find_active_vpc_regions(boto3.Session()) if report_config["scope"] == "regional" else []
                if not regions_to_scan and report_config["scope"] == "regional":
                    logging.info("Nenhuma região ativa para escanear. Encerrando a execução."); break
                
                collector = importlib.import_module(f"src.automacao.{module_name}.collector")
                report_generator = importlib.import_module(f"src.automacao.{module_name}.report_generator")
                security_analyzer = importlib.import_module("src.automacao.security_analyzer")
                final_formatter = importlib.import_module("src.automacao.final_formatter")
                
                logging.info("--- ETAPA 1: Coleta de Dados ---")
                collector.collect_and_save_as_json(output_path=path_raw_json, regions_to_scan=regions_to_scan)
                time.sleep(1)

                logging.info("--- ETAPA 2: Geração do Relatório Base ---")
                report_generator.create_report_from_json(input_json_path=path_raw_json, output_excel_path=path_base_excel)
                time.sleep(1)
                
                logging.info("--- ETAPA 3: Análise de Segurança ---")
                sg_risk_map = security_analyzer.analyze_and_update_report(input_path=path_base_excel, output_path=path_analyzed, json_path=path_raw_json)
                time.sleep(1)

                logging.info("--- ETAPA 4: Formatação Final ---")
                final_formatter.apply_final_formatting(input_path=path_analyzed, output_path=path_final, sg_risk_map=sg_risk_map)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {path_final}")
            except Exception as e:
                logging.critical(f"A automação foi interrompida por um erro: {e}", exc_info=True)
            break
        else:
            print("\nOpção inválida!")

if __name__ == "__main__":
    main()