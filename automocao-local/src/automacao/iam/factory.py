import pandas as pd
import boto3
import logging
import io
import os
from datetime import datetime, timezone
from openpyxl import load_workbook
from ..models import IAMUser, AccessKey
from ..utils import formatters

# --- CRITÉRIOS DE RISCO PARA IAM ---
ADMIN_POLICY_ARN = "arn:aws:iam::aws:policy/AdministratorAccess"
KEY_MAX_AGE_DAYS = 90

class IAMReport:
    """Fábrica autônoma para criar o relatório de segurança do IAM."""
    def __init__(self, regions_to_scan=None): # regions_to_scan é ignorado, IAM é global
        self.users: list[IAMUser] = []
        self.findings_df = pd.DataFrame()
        self.user_risk_map = {}
        logging.info("Fábrica de Relatório IAM iniciada.")

    def collect_data(self):
        """Coleta todos os dados de usuários, chaves, MFA e políticas."""
        logging.info("Coletando dados do IAM...")
        iam = boto3.client('iam')
        
        # Coleta todos os usuários
        users_raw = iam.list_users().get('Users', [])
        users_obj = [IAMUser(data) for data in users_raw]
        
        # Para cada usuário, coleta detalhes adicionais
        for user in users_obj:
            logging.info(f"Coletando detalhes para o usuário: {user.name}...")
            # Verifica MFA
            user.mfa_enabled = bool(iam.list_mfa_devices(UserName=user.name).get('MFADevices', []))
            
            # Coleta chaves de acesso
            keys_raw = iam.list_access_keys(UserName=user.name).get('AccessKeyMetadata', [])
            user.access_keys = [AccessKey(key) for key in keys_raw]

            # Coleta políticas atreladas diretamente
            user.attached_policies = [p['PolicyArn'] for p in iam.list_attached_user_policies(UserName=user.name).get('AttachedPolicies', [])]

        self.users = users_obj
        return self

    def analyze_security(self):
        """Analisa cada usuário em busca de riscos de segurança."""
        logging.info("Analisando riscos de segurança para cada usuário IAM...")
        findings = []
        
        for user in self.users:
            highest_risk_level = 0
            
            # VERIFICAÇÃO 1: MFA está ativado?
            if not user.mfa_enabled:
                highest_risk_level = max(highest_risk_level, 2) # Alto Risco
                findings.append({"Risco": "Alto", "Usuário": user.name, "Achado": "MFA não está ativado", "Recomendação": "Ative a Autenticação Multi-Fator para este usuário."})
            
            # VERIFICAÇÃO 2: Chaves de acesso antigas ou inativas?
            for key in user.access_keys:
                if key.status == 'Active':
                    age = (datetime.now(timezone.utc) - key.create_date).days
                    if age > KEY_MAX_AGE_DAYS:
                        highest_risk_level = max(highest_risk_level, 2) # Alto Risco
                        findings.append({"Risco": "Alto", "Usuário": user.name, "Achado": f"Chave de Acesso ativa com {age} dias", "Recomendação": f"Rotacione a chave de acesso {key.id}."})

            # VERIFICAÇÃO 3: Usuário tem permissão de Administrador?
            if ADMIN_POLICY_ARN in user.attached_policies:
                highest_risk_level = max(highest_risk_level, 2) # Alto Risco
                findings.append({"Risco": "Alto", "Usuário": user.name, "Achado": "Política 'AdministratorAccess' diretamente atrelada", "Recomendação": "Conceda permissões através de grupos e use o princípio do menor privilégio."})

            # Mapeia o risco final
            if highest_risk_level == 2: self.user_risk_map[user.name] = "Alto"
            elif highest_risk_level == 1: self.user_risk_map[user.name] = "Médio"
            else: self.user_risk_map[user.name] = "Seguro"

        self.findings_df = pd.DataFrame(findings) if findings else pd.DataFrame([{"Risco": "Parabéns!", "Usuário": "Nenhum risco comum detectado."}])
        return self

    def generate_report(self, output_path: str):
        """Gera a planilha final e a salva no disco."""
        # (Lógica para criar DataFrames, gerar o workbook em memória, formatar e salvar)
        # Este método será muito parecido com o da VPCReport que já fizemos.
        logging.info("Geração do relatório IAM ainda não implementada completamente.")
        # Por enquanto, vamos apenas salvar os achados para provar que a lógica funciona
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        self.findings_df.to_excel(output_path, sheet_name="IAM_Security_Analysis", index=False)
        logging.info(f"Relatório de análise de segurança do IAM salvo em: {output_path}")