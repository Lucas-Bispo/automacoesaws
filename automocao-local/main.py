import logging
import os
import re
import importlib
import pandas as pd
import time
import boto3
from datetime import datetime, timedelta
from collections import defaultdict

# Importa as funções de utilidade dos nossos módulos
from src.automacao.utils.logger import setup_logging
from src.automacao.utils.config import load_environment
from src.automacao.utils.credentials import validate_aws_credentials

# --- CONSTANTES GLOBAIS ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Dicionário de relatórios com o novo escopo 'regional' ou 'global'
REPORTS = {
    "1": {"name": "VPC e Recursos Associados", "module": "vpc", "scope": "regional"},
    "2": {"name": "Instâncias EC2", "module": "ec2", "scope": "regional"},
    "3": {"name": "IAM (Usuários e Grupos)", "module": "iam", "scope": "global"}
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

def get_active_regions(session):
    """Usa o AWS Cost Explorer para encontrar regiões com custos ou retorna todas as ativas."""
    logging.info("Consultando o AWS Cost Explorer para encontrar regiões ativas (com custos)...")
    cost_explorer = session.client('ce', region_name='us-east-1')
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    try:
        response = cost_explorer.get_cost_and_usage(
            TimePeriod={'Start': start_date.strftime('%Y-%m-%d'), 'End': end_date.strftime('%Y-%m-%d')},
            Granularity='MONTHLY', Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'REGION'}]
        )
        active_regions = [group['Keys'][0] for group in response['ResultsByTime'][0]['Groups'] if float(group['Metrics']['UnblendedCost']['Amount']) > 0]
        if active_regions:
            logging.info(f"Regiões com custos encontradas: {active_regions}")
            return active_regions
    except Exception as e:
        logging.error(f"Não foi possível buscar dados do Cost Explorer: {e}. Verifique a permissão 'ce:GetCostAndUsage'.")
    
    logging.warning("Nenhuma região com custos encontrada ou falha na API. Verificando todas as regiões ativas como fallback.")
    ec2 = session.client('ec2', region_name='us-east-1')
    return [region['RegionName'] for region in ec2.describe_regions(AllRegions=False)['Regions']]

# --- FUNÇÃO PRINCIPAL ---

def main():
    """Função principal que orquestra a automação interativa."""
    setup_logging()
    load_environment()
    if not validate_aws_credentials():
        logging.critical("Autenticação na AWS falhou. Encerrando.")
        return

    while True:
        display_menu()
        choice = input("Por favor, escolha uma opção e pressione Enter: ").strip()

        if choice.lower() == 'q':
            logging.info("Encerrando o programa. Até mais!")
            break

        if choice in REPORTS:
            report_config = REPORTS[choice]
            module_name = report_config["module"]
            
            # Geração de nomes de arquivo únicos
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
                # --- INÍCIO DO PIPELINE ---
                aws_session = boto3.Session()
                regions_to_scan = []
                if report_config["scope"] == "regional":
                    regions_to_scan = get_active_regions(aws_session)
                
                # ETAPA 1: COLETA GLOBAL/REGIONAL
                collector = importlib.import_module(f"src.automacao.{module_name}.collector")
                logging.info(f"ETAPA 1: Coletando dados e salvando em '{os.path.basename(path_raw_json)}'")
                collector.collect_and_save_as_json(output_path=path_raw_json, regions_to_scan=regions_to_scan)
                time.sleep(1)

                # ETAPA 2: GERAÇÃO DA PLANILHA BASE
                report_generator = importlib.import_module(f"src.automacao.{module_name}.report_generator")
                logging.info(f"ETAPA 2: Gerando planilha base em '{os.path.basename(path_base_excel)}'")
                report_generator.create_report_from_json(input_json_path=path_raw_json, output_excel_path=path_base_excel)
                time.sleep(1)

                # ETAPA 3: ANÁLISE DE SEGURANÇA
                path_for_formatter = path_base_excel
                if module_name == 'vpc': # Análise de segurança só se aplica a VPC por enquanto
                    from src.automacao.security_analyzer import analyze_security_report
                    logging.info(f"ETAPA 3: Adicionando aba de segurança e salvando em '{os.path.basename(path_analyzed)}'")
                    analyze_security_report(input_path=path_base_excel, output_path=path_analyzed)
                    path_for_formatter = path_analyzed # O próximo passo usará este arquivo
                    time.sleep(1)

                # ETAPA 4: FORMATAÇÃO FINAL
                from src.automacao.final_formatter import apply_final_formatting
                logging.info(f"ETAPA 4: Aplicando formatação final e salvando em '{os.path.basename(path_final)}'")
                apply_final_formatting(input_path=path_for_formatter, output_path=path_final)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {path_final}")

            except Exception as e:
                logging.critical(f"A automação foi interrompida por um erro: {e}", exc_info=True)
            
            break
        else:
            print("\nOpção inválida! Por favor, escolha um número do menu.")

if __name__ == "__main__":
    main()