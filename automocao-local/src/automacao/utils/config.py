import os
from dotenv import load_dotenv

def load_environment():
    """
    Encontra e carrega o arquivo .env da pasta 'config' na raiz do projeto.
    """
    # Constrói o caminho para a pasta raiz do projeto
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    
    # Constrói o caminho completo para o arquivo .env
    dotenv_path = os.path.join(project_root, 'config', '.env')

    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        # Se estiver em um ambiente de produção (ex: Docker) sem .env, ele usará as variáveis do sistema.
        print("Arquivo .env não encontrado, usando variáveis de ambiente do sistema (se existirem).")

def get_config(key, default=None):
    """
    Busca um valor de configuração do ambiente.

    Args:
        key (str): A chave da variável de ambiente (ex: 'AWS_REGION').
        default: O valor padrão a ser retornado se a chave não for encontrada.

    Returns:
        O valor da variável de ambiente ou o valor padrão.
    """
    return os.getenv(key, default)