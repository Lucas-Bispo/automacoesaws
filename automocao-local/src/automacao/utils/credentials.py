import boto3
from botocore.exceptions import ClientError
import logging

# Note o import relativo, dentro do mesmo pacote 'utils'
from .config import get_config 

def validate_aws_credentials():
    """
    Usa o STS para validar as credenciais AWS carregadas no ambiente.
    Retorna True se as credenciais forem válidas, False caso contrário.
    """
    try:
        aws_region = get_config('AWS_REGION', 'us-east-1')
        sts_client = boto3.client('sts', region_name=aws_region)
        sts_client.get_caller_identity()
        logging.info("Credenciais AWS validadas com sucesso.")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ['InvalidClientTokenId', 'AuthFailure']:
            logging.error(f"Falha de autenticação ({error_code}). Verifique as credenciais no arquivo config/.env")
        else:
            logging.error(f"Erro inesperado ao validar credenciais: {e}")
        return False
    except Exception as e:
        logging.error(f"Não foi possível conectar à AWS. Verifique sua conexão ou configuração. Erro: {e}")
        return False