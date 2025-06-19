import boto3  # Biblioteca oficial AWS para interagir com serviços AWS via API
from botocore.exceptions import ClientError  # Exceções específicas da AWS para tratamento de erros
import logging  # Biblioteca para registrar logs de eventos e erros

# Importa função para obter configurações do ambiente, dentro do mesmo pacote 'utils'
from .config import get_config 

def validate_aws_credentials():
    """
    Valida as credenciais AWS carregadas no ambiente usando o serviço STS (Security Token Service).
    Retorna True se as credenciais forem válidas, False caso contrário.
    """
    try:
        # Obtém a região AWS configurada, padrão para 'us-east-1' se não definida
        aws_region = get_config('AWS_REGION', 'us-east-1')
        
        # Cria cliente STS na região configurada
        sts_client = boto3.client('sts', region_name=aws_region)
        
        # Chama a API get_caller_identity para verificar se as credenciais são válidas
        sts_client.get_caller_identity()
        
        # Se não lançar exceção, credenciais são válidas
        logging.info("Credenciais AWS validadas com sucesso.")
        return True
    
    except ClientError as e:
        # Captura erros específicos do cliente AWS
        error_code = e.response['Error']['Code']
        
        # Trata erros comuns de autenticação
        if error_code in ['InvalidClientTokenId', 'AuthFailure']:
            logging.error(f"Falha de autenticação ({error_code}). Verifique as credenciais no arquivo config/.env")
        else:
            # Outros erros inesperados relacionados à AWS
            logging.error(f"Erro inesperado ao validar credenciais: {e}")
        return False
    
    except Exception as e:
        # Captura qualquer outro erro genérico, como problemas de rede
        logging.error(f"Não foi possível conectar à AWS. Verifique sua conexão ou configuração. Erro: {e}")
        return False
