class SecurityGroup:
    """
    Representa um Security Group da AWS.
    """
    def __init__(self, sg_data: dict):
        # Pega o ID do Security Group do dicionário sg_data
        self.id = sg_data.get('GroupId')
        
        # Pega o nome do Security Group
        self.name = sg_data.get('GroupName')
        
        # Pega a descrição do Security Group
        self.description = sg_data.get('Description')
        
        # Pega o ID da VPC à qual esse Security Group pertence
        self.vpc_id = sg_data.get('VpcId')
        
        # Pega a região AWS onde esse Security Group está localizado
        self.region = sg_data.get('Region')
        
        # Armazena todos os dados brutos do Security Group para análises futuras
        self.raw_rules = sg_data 
        
        # Inicializa o nível de risco como "Seguro", podendo ser alterado depois
        self.risk_level = "Seguro"


class VPC:
    """
    Representa uma VPC da AWS e conterá seus recursos associados.
    """
    def __init__(self, vpc_data: dict):
        # Pega o ID da VPC
        self.id = vpc_data.get('VpcId')
        
        # Procura a tag 'Name' na lista de tags da VPC e usa seu valor como nome.
        # Se não encontrar, usa o próprio ID como nome.
        self.name = next(
            (
                tag['Value']
                for tag in vpc_data.get('Tags', [])
                if isinstance(vpc_data.get('Tags'), list) and tag.get('Key') == 'Name'
            ),
            self.id
        )
        
        # Pega a região AWS onde a VPC está localizada
        self.region = vpc_data.get('Region')
        
        # Inicializa uma lista vazia para armazenar os Security Groups associados a essa VPC
        self.security_groups: list[SecurityGroup] = []

# Adicione estas classes ao final do seu arquivo models.py

class IAMUser:
    """Representa um usuário do serviço IAM da AWS."""
    def __init__(self, user_data: dict):
        self.id = user_data.get('UserId')
        self.name = user_data.get('UserName')
        self.arn = user_data.get('Arn')
        self.create_date = user_data.get('CreateDate')
        self.password_last_used = user_data.get('PasswordLastUsed', 'Nunca')
        
        # Atributos que serão preenchidos pela fábrica
        self.groups = []
        self.attached_policies = []
        self.inline_policies = []
        self.mfa_enabled = False
        self.access_keys = []
        self.risk_level = "Seguro"

class AccessKey:
    """Representa uma chave de acesso de um usuário IAM."""
    def __init__(self, key_data: dict):
        self.id = key_data.get('AccessKeyId')
        self.status = key_data.get('Status')
        self.create_date = key_data.get('CreateDate')