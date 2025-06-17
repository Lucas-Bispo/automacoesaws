import logging
import os
import re
from datetime import datetime
import boto3
from src.automacao.utils.logger import setup_logging
from src.automacao.utils.config import load_environment
from src.automacao.utils.credentials import validate_aws_credentials
# Importa a nossa nova FÁBRICA de relatórios
from src.automacao.vpc.factory import VPCReport

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# O menu agora aponta para a classe de fábrica correspondente
REPORTS = {
    "1": {
        "name": "VPC e Recursos Associados", 
        "factory": VPCReport,
        "output_prefix": "RELATORIO_FINAL_VPC"
    },
    # No futuro, podemos adicionar:
    # "2": {"name": "Instâncias EC2", "factory": EC2Report, "output_prefix": "RELATORIO_FINAL_EC2"},
}

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
    ec2_global = session.client('ec2', region_name='us-east-1')
    try:
        all_regions = [region['RegionName'] for region in ec2_global.describe_regions(AllRegions=False)['Regions']]
    except Exception as e:
        logging.error(f"Não foi possível buscar a lista de regiões da AWS: {e}."); return []
    
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
        except Exception as e:
            logging.warning(f"Não foi possível sondar a região {region_name}. Erro: {e}.")
    logging.info(f"Análise concluída. Regiões com VPCs em uso: {active_regions}")
    return active_regions

def main():
    """Função principal que orquestra a automação interativa."""
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
            
            output_dir = os.path.join(PROJECT_ROOT, "output", "vpc") # Simplificado
            run_number = get_next_run_number(output_dir, report_config["output_prefix"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path_final = os.path.join(output_dir, f"{report_config['output_prefix']}_{run_number}_{timestamp}.xlsx")

            logging.info(f"Gerando Relatório: '{report_config['name']}' (Execução #{run_number})")
            
            try:
                # --- O NOVO FLUXO ORIENTADO A OBJETOS ---
                active_regions = find_active_vpc_regions(boto3.Session())
                if not active_regions:
                    logging.warning("Nenhuma região ativa para escanear. Nenhum relatório será gerado.")
                    break

                # 1. Cria a "fábrica" com as regiões a serem escaneadas
                report_factory = report_config["factory"](regions_to_scan=active_regions)

                # 2. Executa o pipeline de ponta a ponta e gera o relatório final
                #    usando method chaining para um código mais elegante.
                report_factory.collect_data().analyze_security().generate_report(output_path=path_final)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {path_final}")
            except Exception as e:
                logging.critical(f"A automação foi interrompida por um erro: {e}", exc_info=True)
            
            break
        else:
            print("\nOpção inválida!")

if __name__ == "__main__":
    main()