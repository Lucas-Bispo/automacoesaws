# Arquivo: src/automacao/models.py

import logging

class Rule:
    """Representa uma única regra (de entrada ou saída) de um Security Group."""
    def __init__(self, rule_data: dict, direction: str):
        self.direction = direction
        self.protocol = str(rule_data.get('IpProtocol', '-1')).upper().replace('-1', 'All Traffic')
        self.from_port = rule_data.get('FromPort')
        self.to_port = rule_data.get('ToPort')
        self.sources = self._extract_sources(rule_data)

    def _extract_sources(self, rule_data):
        """Extrai todas as fontes de uma regra (CIDRs, outros SGs, etc.)."""
        sources = []
        sources.extend([ip.get('CidrIp') for ip in rule_data.get('IpRanges', []) if ip.get('CidrIp')])
        sources.extend([group.get('GroupId') for group in rule_data.get('UserIdGroupPairs', []) if group.get('GroupId')])
        return sources if sources else ['N/A']

    def to_text(self):
        """Converte a regra em um texto formatado para o relatório."""
        port_str = "All"
        if self.from_port is not None:
            port_str = f"{self.from_port}" if self.from_port == self.to_port else f"{self.from_port}-{self.to_port}"
        
        return f"Protocol: {self.protocol}, Ports: {port_str}\n  Source/Dest: {', '.join(self.sources)}"

class SecurityGroup:
    """
    Representa um Security Group da AWS.
    Esta classe guarda as informações essenciais de um SG e também os dados brutos
    das regras para serem usados depois pela análise e formatação.
    """
    def __init__(self, sg_data: dict):
        self.id = sg_data.get('GroupId')
        self.name = sg_data.get('GroupName')
        self.description = sg_data.get('Description')
        self.vpc_id = sg_data.get('VpcId')
        self.region = sg_data.get('Region')
        
        # --- A LINHA DA CORREÇÃO ---
        # Armazena os dados brutos completos para análise posterior
        self.raw_rules = sg_data 
        
        # Este atributo será preenchido depois pela análise de segurança
        self.risk_level = "Seguro"  

    def get_formatted_inbound_rules(self):
        """Retorna todas as regras de entrada como um único texto formatado."""
        if not self.inbound_rules: return "Nenhuma regra de entrada."
        return "\n\n".join([f"Rule {i+1}:\n{rule.to_text()}" for i, rule in enumerate(self.inbound_rules)])

    def get_formatted_outbound_rules(self):
        """Retorna todas as regras de saída como um único texto formatado."""
        if not self.outbound_rules: return "Nenhuma regra de saída."
        return "\n\n".join([f"Rule {i+1}:\n{rule.to_text()}" for i, rule in enumerate(self.outbound_rules)])

class Subnet:
    """Representa uma Subnet da AWS."""
    def __init__(self, subnet_data: dict):
        self.id = subnet_data.get('SubnetId')
        self.vpc_id = subnet_data.get('VpcId')
        self.cidr_block = subnet_data.get('CidrBlock')
        self.availability_zone = subnet_data.get('AvailabilityZone')
        self.is_public = subnet_data.get('MapPublicIpOnLaunch', False)
        self.tags = {tag['Key']: tag['Value'] for tag in subnet_data.get('Tags', [])}
        self.region = subnet_data.get('Region')

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
        
        # Estas listas serão preenchidas pela nossa "fábrica"
        self.security_groups: list[SecurityGroup] = []