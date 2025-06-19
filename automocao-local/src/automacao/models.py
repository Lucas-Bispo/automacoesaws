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
