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
from src.automacao.final_formatter import apply_final_formatting

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

REPORTS = {
    "1": {"name": "VPC e Recursos Associados", "module": "vpc", "scope": "regional"},
    "2": {"name": "Instâncias EC2", "module": "ec2", "scope": "regional"},
    "3": {"name": "IAM (Usuários e Grupos)", "module": "iam", "scope": "global"}
}

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
    try:
        cost_explorer = session.client('ce', region_name='us-east-1')
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
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

def main():
    """Função principal que orquestra a automação interativa."""
    setup_logging()
    load_environment()
    if not validate_aws_credentials(): return

    while True:
        display_menu()
        choice = input("Por favor, escolha uma opção e pressione Enter: ").strip()

        if choice.lower() == 'q':
            logging.info("Encerrando o programa. Até mais!")
            break

        if choice in REPORTS:
            report_config = REPORTS[choice]
            module_name = report_config["module"]
            
            output_dir = os.path.join(PROJECT_ROOT, "output", module_name)
            run_number = get_next_run_number(output_dir, f"RELATORIO_FINAL_{module_name.upper()}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            path_final_excel = os.path.join(output_dir, f"RELATORIO_FINAL_{module_name.upper()}_{run_number}_{timestamp}.xlsx")

            logging.info(f"Gerando Relatório: '{report_config['name']}' (Execução #{run_number})")
            
            try:
                # --- INÍCIO DO PIPELINE EM MEMÓRIA ---
                collector = importlib.import_module(f"src.automacao.{module_name}.collector")
                report_generator = importlib.import_module(f"src.automacao.{module_name}.report_generator")
                security_analyzer = importlib.import_module("src.automacao.security_analyzer")

                # ETAPA 1: COLETA DOS DADOS BRUTOS
                regions_to_scan = []
                if report_config["scope"] == "regional":
                    regions_to_scan = get_active_regions(boto3.Session())
                logging.info("ETAPA 1: Coletando dados da AWS...")
                data_pack = collector.collect_data(regions_to_scan=regions_to_scan)
                
                # ETAPA 2: ANÁLISE DE SEGURANÇA
                findings_df, sg_risk_map = pd.DataFrame(), {}
                if module_name == 'vpc':
                    logging.info("ETAPA 2: Analisando riscos de segurança...")
                    findings_df, sg_risk_map = security_analyzer.analyze_sgs(data_pack.get('SecurityGroups', pd.DataFrame()))
                
                # ETAPA 3: GERAÇÃO DO RELATÓRIO EM MEMÓRIA
                logging.info("ETAPA 3: Gerando estrutura do relatório...")
                workbook = report_generator.create_report(data_frames=data_pack, security_findings_df=findings_df)
                
                # ETAPA 4: FORMATAÇÃO FINAL
                logging.info("ETAPA 4: Aplicando formatação final (cores, links, layout)...")
                workbook = apply_final_formatting(workbook=workbook, sg_risk_map=sg_risk_map)

                # ETAPA FINAL: SALVAR NO DISCO
                logging.info(f"Salvando relatório final em: {os.path.basename(path_final_excel)}")
                os.makedirs(os.path.dirname(path_final_excel), exist_ok=True)
                workbook.save(path_final_excel)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {path_final_excel}")

            except Exception as e:
                logging.critical(f"A automação foi interrompida por um erro: {e}", exc_info=True)
            
            break
        else:
            print("\nOpção inválida! Por favor, escolha um número do menu.")

if __name__ == "__main__":
    main()