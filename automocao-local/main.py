import logging  # Biblioteca para registrar logs de eventos e erros
import os  # Biblioteca para manipulação de arquivos e diretórios
import re  # Biblioteca para trabalhar com expressões regulares
import boto3  # Biblioteca oficial AWS para interagir com serviços AWS via API
from datetime import datetime  # Para manipulação de datas e horas
from src.automacao.utils.logger import setup_logging  # Função para configurar logging do projeto
from src.automacao.utils.config import load_environment  # Função para carregar variáveis de ambiente
from src.automacao.utils.credentials import validate_aws_credentials  # Função para validar credenciais AWS
from src.automacao.vpc.factory import VPCReport  # Classe que gera o relatório de VPCs (fábrica)

# CONSTANTES GLOBAIS
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))  # Caminho absoluto da pasta do script atual

# Dicionário que mapeia opções do menu para configurações de relatórios
REPORTS = {
    "1": {
        "name": "VPC e Recursos Associados",  # Nome exibido no menu
        "factory": VPCReport,  # Classe responsável por gerar o relatório
        "output_dir_name": "vpc",  # Pasta onde o relatório será salvo
        "output_prefix": "RELATORIO_FINAL_VPC"  # Prefixo do nome do arquivo gerado
    },
}

# FUNÇÕES DE AJUDA

def display_menu():
    """Mostra o menu de opções para o usuário."""
    print("\n+-------------------------------------------------------------+")
    print("|                MENU DE RELATÓRIOS AWS                     |")
    print("+-------------------------------------------------------------+")
    for key, value in REPORTS.items():
        print(f"  [{key}] - {value['name']}")  # Exibe as opções do menu dinamicamente
    print("  [q] - Sair")  # Opção para sair do programa
    print("+-------------------------------------------------------------+")

def get_next_run_number(output_dir: str, report_prefix: str) -> int:
    """
    Escaneia o diretório de saída para encontrar o maior número de execução já salvo
    e retorna o próximo número sequencial para nomear o novo arquivo.
    """
    os.makedirs(output_dir, exist_ok=True)  # Cria o diretório caso não exista
    max_run_num = 0  # Inicializa contador do maior número de execução
    # Expressão regular para encontrar arquivos que seguem o padrão do prefixo e número da execução
    pattern = re.compile(f"^{report_prefix}_(\\d+)_.*")
    for filename in os.listdir(output_dir):  # Lista arquivos no diretório
        match = pattern.match(filename)
        if match:
            run_num = int(match.group(1))  # Extrai o número da execução do nome do arquivo
            if run_num > max_run_num:
                max_run_num = run_num  # Atualiza o maior número encontrado
    return max_run_num + 1  # Retorna o próximo número sequencial

def find_active_vpc_regions(session):
    """
    Varre todas as regiões AWS para encontrar aquelas que possuem VPCs customizadas (não padrão),
    ou recursos na VPC padrão, indicando que estão ativas e devem ser escaneadas.
    """
    logging.info("Iniciando varredura em todas as regiões para encontrar VPCs ativas...")
    ec2_global = session.client('ec2', region_name='us-east-1')  # Cliente EC2 global para listar regiões
    try:
        # Obtém lista de regiões AWS disponíveis (não todas, apenas as habilitadas na conta)
        all_regions = [region['RegionName'] for region in ec2_global.describe_regions(AllRegions=False)['Regions']]
    except Exception as e:
        logging.error(f"Não foi possível buscar a lista de regiões da AWS: {e}.")
        return []  # Retorna lista vazia se falhar
    
    active_regions = []  # Lista para armazenar regiões que possuem VPCs ativas
    for region_name in all_regions:
        logging.info(f"Sondando região: {region_name}...")
        try:
            ec2_regional = session.client('ec2', region_name=region_name)  # Cliente EC2 regional
            # Consulta VPCs customizadas (não padrão) na região
            custom_vpcs = ec2_regional.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['false']}]).get('Vpcs', [])
            if custom_vpcs:
                logging.info(f"-> Região ATIVA encontrada (VPC customizada): {region_name}")
                active_regions.append(region_name)  # Adiciona região ativa na lista
                continue  # Passa para próxima região
        except Exception as e:
            logging.warning(f"Não foi possível sondar a região {region_name}. Erro: {e}.")
            
    logging.info(f"Análise concluída. Regiões com VPCs em uso: {active_regions}")
    return active_regions  # Retorna lista de regiões ativas

# FUNÇÃO PRINCIPAL (ORQUESTRADOR)

def main():
    setup_logging()  # Configura o sistema de logs
    load_environment()  # Carrega variáveis de ambiente (ex: credenciais)
    if not validate_aws_credentials():  # Valida se as credenciais AWS estão corretas
        return  # Encerra se credenciais inválidas

    while True:
        display_menu()  # Mostra menu para o usuário
        choice = input("Por favor, escolha uma opção e pressione Enter: ").strip()  # Recebe escolha do usuário

        if choice.lower() == 'q':  # Se usuário digitar 'q', encerra o programa
            logging.info("Encerrando o programa.")
            break
        
        if choice in REPORTS:  # Se a escolha for uma opção válida de relatório
            report_config = REPORTS[choice]  # Obtém configuração do relatório escolhido
            
            # Define o diretório onde o relatório será salvo
            output_dir = os.path.join(PROJECT_ROOT, "output", report_config["output_dir_name"])
            
            # Obtém o próximo número sequencial para o arquivo de relatório
            run_number = get_next_run_number(output_dir, report_config["output_prefix"])
            
            # Gera timestamp para o nome do arquivo (formato: AAAAMMDD_HHMMSS)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Monta o caminho completo do arquivo Excel que será salvo
            path_final = os.path.join(output_dir, f"{report_config['output_prefix']}_{run_number}_{timestamp}.xlsx")

            logging.info(f"Gerando Relatório: '{report_config['name']}' (Execução #{run_number})")
            
            try:
                # Cria sessão boto3 e identifica regiões AWS ativas com VPCs para escanear
                active_regions = find_active_vpc_regions(boto3.Session())
                if not active_regions:  # Se não houver regiões ativas, encerra
                    logging.warning("Nenhuma região ativa para escanear. Encerrando a execução.")
                    break

                # Cria a "fábrica" do relatório, passando as regiões ativas
                report_factory = report_config["factory"](regions_to_scan=active_regions)

                # Executa o fluxo completo: coleta dados, analisa segurança e gera o relatório Excel
                report_factory.collect_data().analyze_security().generate_report(output_path=path_final)
                
                logging.info(f"SUCESSO! Relatório final salvo em: {path_final}")
            except Exception as e:
                # Caso ocorra erro, registra log crítico com detalhes da exceção
                logging.critical(f"A automação foi interrompida por um erro: {e}", exc_info=True)
            
            break  # Encerra após gerar o relatório (remova para permitir múltiplas execuções)
        else:
            print("\nOpção inválida!")  # Mensagem para opção inválida no menu

# Executa a função principal somente se o script for executado diretamente
if __name__ == "__main__":
    main()
