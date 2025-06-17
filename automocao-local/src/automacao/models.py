# Arquivo: src/automacao/models.py

class SecurityGroup:
    """
    Representa um Security Group da AWS.
    """
    def __init__(self, sg_data: dict):
        self.id = sg_data.get('GroupId')
        self.name = sg_data.get('GroupName')
        self.description = sg_data.get('Description')
        self.vpc_id = sg_data.get('VpcId')
        self.region = sg_data.get('Region')
        
        # --- A LINHA DA CORREÇÃO ---
        # Armazena os dados brutos completos para análise precisa
        self.raw_rules = sg_data 
        
        # Este atributo será preenchido depois pela análise
        self.risk_level = "Seguro"

class VPC:
    """
    Representa uma VPC da AWS e conterá seus recursos associados.
    """
    def __init__(self, vpc_data: dict):
        self.id = vpc_data.get('VpcId')
        # Tenta pegar a tag 'Name', se não houver, usa o próprio ID como nome
        self.name = next((tag['Value'] for tag in vpc_data.get('Tags', []) if isinstance(vpc_data.get('Tags'), list) and tag.get('Key') == 'Name'), self.id)
        self.region = vpc_data.get('Region')
        
        # Estas listas serão preenchidas pela nossa "fábrica"
        self.security_groups: list[SecurityGroup] = []