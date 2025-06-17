import logging

class SecurityGroup:
    """
    Representa um Security Group da AWS.
    Armazena os dados brutos para serem usados depois pela análise e formatação.
    """
    def __init__(self, sg_data: dict):
        self.id = sg_data.get('GroupId')
        self.name = sg_data.get('GroupName')
        self.description = sg_data.get('Description')
        self.vpc_id = sg_data.get('VpcId')
        self.region = sg_data.get('Region')
        
        # Mantém os dados brutos das regras para análise precisa
        self.raw_ip_permissions = sg_data.get('IpPermissions', [])
        self.raw_ip_permissions_egress = sg_data.get('IpPermissionsEgress', [])
        
        # Este atributo será preenchido depois pela análise de segurança
        self.risk_level = "Seguro"

class VPC:
    """
    Representa uma VPC da AWS e conterá a lista de seus
    recursos associados, como Security Groups.
    """
    def __init__(self, vpc_data: dict):
        self.id = vpc_data.get('VpcId')
        # Tenta pegar a tag 'Name', se não houver, usa o próprio ID como nome
        self.name = next((tag['Value'] for tag in vpc_data.get('Tags', []) if isinstance(vpc_data.get('Tags'), list) and tag.get('Key') == 'Name'), self.id)
        self.region = vpc_data.get('Region')
        self.cidr_block = vpc_data.get('CidrBlock')
        self.is_default = vpc_data.get('IsDefault', False)
        self.tags = {tag['Key']: tag['Value'] for tag in vpc_data.get('Tags', []) if isinstance(vpc_data.get('Tags'), list)}
        
        # Esta lista será preenchida pela nossa "fábrica"
        self.security_groups = []