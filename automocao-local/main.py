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
# Importa a nossa nova FÁBRICA de relatórios
from src.automacao.vpc.factory import VPCReport

# --- CONSTANTES GLOBAIS ---
# Projeto root é a pasta raiz do projeto
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Dicionário que armazena as opções de relatórios
REPORTS = {
    "1": {"name": "VPC e Recursos Associados", "module": "vpc", "scope": "regional"},
    # Futuramente, podemos adicionar outros relatórios aqui
}

# --- FUNÇÕES DE AJUDA ---
# Mostra o menu de opções para o usuário
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
    print("Iniciando varredura em todas as regiões para encontrar VPCs ativas...")
    ec2_global = session.client('ec2', region_name='us-east-1')
    try:
        all_regions = [region['RegionName'] for region in ec2_global.describe_regions(AllRegions=False)['Regions']]
    except Exception as e:
        print(f"Não foi possível buscar a lista de regiões da AWS: {e}.")
        return []
    
    active_regions = []
    for region_name in all_regions:
        logging.info(f"Sondando região: {region_name}...")
        try:
            ec2_regional = session.client('ec2', region_name=region_name)
            vpcs = ec2_regional.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['false']}]).get('Vpcs', [])
            if vpcs:
                logging.info(f"-> Região ATIVA encontrada (VPC customizada): {region_name}")
                active_regions.append(region_name)
                continue
            
            # Verificar esta condicao a nivel de servico
            # Se há apenas a VPC Padrão, verifica se há instâncias EC2 nela para confirmar o uso.
            #instances = ec2_regional.describe_instances(
             #   Filters=[{'Name': 'vpc-id', 'Values': [vpcs[0]['VpcId']]}]
            #).get('Reservations', [])

            #if instances:
            #   print(f"-> Região ATIVA encontrada (recursos na VPC Padrão): {region_name}")
            #  active_regions.append(region_name)

        except Exception as e:
            print(f"Não foi possível sondar a região {region_name}. Erro: {e}. Pulando região.")
            continue
            
    if not active_regions:
        print("Nenhuma região com VPCs ativas foi encontrada com base nos critérios.")
    else:
        print(f"Análise concluída. Regiões com VPCs em uso: {active_regions}")
        
    return active_regions

# --- FUNÇÃO PRINCIPAL (O ORQUESTRADOR) ---
# Função principal que orquestra a automação interativa
def main():
    """Função principal que orquestra a automação interativa."""
    print("Iniciando a automação...")
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
            
            # --- Geração de Nomes de Arquivo para o Pipeline ---
            output_dir = os.path.join(PROJECT_ROOT, "output", module_name)
            run_number = get_next_run_number(output_dir, f"RELATORIO_FINAL_{module_name.upper()}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path_final = os.path.join(output_dir, f"{report_config['output_prefix']}_{run_number}_{timestamp}.xlsx")

            logging.info(f"Gerando Relatório: '{report_config['name']}' (Execução #{run_number})")
            
            try:
                # --- INÍCIO DO PIPELINE SEQUENCIAL ---
                regions_to_scan = find_active_vpc_regions(boto3.Session()) if report_config["scope"] == "regional" else []
                if not regions_to_scan and report_config["scope"] == "regional":
                    print("Nenhuma região ativa para escanear. Encerrando a execução."); break
                
                collector = importlib.import_module(f"src.automacao.{module_name}.collector")
                report_generator = importlib.import_module(f"src.automacao.{module_name}.report_generator")
                security_analyzer = importlib.import_module("src.automacao.security_analyzer")
                final_formatter = importlib.import_module("src.automacao.final_formatter")
                
                print("--- ETAPA 1: Coleta de Dados ---")
                collector.collect_and_save_as_json(output_path=path_raw_json, regions_to_scan=regions_to_scan)
                time.sleep(1)

                print("--- ETAPA 2: Geração do Relatório Base ---")
                report_generator.create_report_from_json(input_json_path=path_raw_json, output_excel_path=path_base_excel)
                time.sleep(1)
                
                print("--- ETAPA 3: Análise de Segurança ---")
                sg_risk_map = security_analyzer.analyze_and_update_report(input_path=path_base_excel, output_path=path_analyzed, json_path=path_raw_json)
                time.sleep(1)

                print("--- ETAPA 4: Formatação Final ---")
                final_formatter.apply_final_formatting(input_path=path_analyzed, output_path=path_final, sg_risk_map=sg_risk_map)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {path_final}")
            except Exception as e:
                print(f"A automação foi interrompida por um erro: {e}", exc_info=True)
            break
        else:
            print("\nOpção inválida!")

if __name__ == "__main__":
    main()