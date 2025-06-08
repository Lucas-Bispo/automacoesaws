import logging
import os
import importlib
import pandas as pd
from src.automacao.utils.logger import setup_logging
from src.automacao.utils.config import load_environment
from src.automacao.utils.credentials import validate_aws_credentials
from src.automacao.final_formatter import apply_final_formatting

# Pega o caminho absoluto do diretório onde main.py está.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- CONFIGURAÇÃO DOS RELATÓRIOS DISPONÍVEIS ---
REPORTS = {
    "1": {
        "name": "VPC e Recursos Associados",
        "module": "vpc",
        "output_path": os.path.join("output", "vpc", "relatorio_completo_vpc.xlsx")
    },
    "2": {
        "name": "Instâncias EC2",
        "module": "ec2",
        "output_path": os.path.join("output", "ec2", "relatorio_ec2.xlsx")
    },
    "3": {
        "name": "IAM (Usuários e Grupos)",
        "module": "iam",
        "output_path": os.path.join("output", "iam", "relatorio_iam.xlsx")
    }
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
            absolute_report_path = os.path.join(PROJECT_ROOT, report_config["output_path"])
            
            logging.info(f"Gerando relatório: '{report_config['name']}'...")
            
            try:
                collector = importlib.import_module(f"src.automacao.{module_name}.collector")
                report_generator = importlib.import_module(f"src.automacao.{module_name}.report_generator")
                
                # ETAPA 1: COLETA DOS DADOS BRUTOS
                logging.info("ETAPA 1: Coletando dados da AWS...")
                data_pack = collector.collect_data()
                
                # ETAPA 2: ANÁLISE DE SEGURANÇA (se aplicável)
                findings_df = pd.DataFrame() # DataFrame vazio por padrão
                if module_name == 'vpc':
                    from src.automacao.security_analyzer import analyze_sgs_for_risks
                    logging.info("ETAPA 2: Analisando riscos de segurança...")
                    findings_df = analyze_sgs_for_risks(sg_dataframe=data_pack['SecurityGroups'])
                
                # ETAPA 3: GERAÇÃO DO RELATÓRIO EM MEMÓRIA
                logging.info("ETAPA 3: Gerando estrutura do relatório...")
                workbook = report_generator.create_report(
                    data_frames=data_pack, 
                    security_findings_df=findings_df
                )
                
                # ETAPA 4: FORMATAÇÃO FINAL (CORES, LINKS, LAYOUT)
                logging.info("ETAPA 4: Aplicando formatação final...")
                workbook = apply_final_formatting(workbook=workbook)

                # ETAPA FINAL: SALVAR NO DISCO
                logging.info(f"Salvando relatório final em: {absolute_report_path}")
                workbook.save(absolute_report_path)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {report_config['output_path']}")

            except Exception as e:
                logging.critical(f"A automação foi interrompida por um erro: {e}", exc_info=True)
            
            break
        else:
            print("\nOpção inválida! Por favor, escolha um número do menu.")

if __name__ == "__main__":
    main()