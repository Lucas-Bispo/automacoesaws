import pandas as pd
import boto3
import logging
import io
import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment, PatternFill, Font
from openpyxl.utils import get_column_letter
from collections import defaultdict
from ..models import VPC, SecurityGroup
from ..utils import formatters
from ..security_analyzer import analyze_sgs

class VPCReport:
    """Fábrica autônoma para criar o relatório completo de VPC em memória."""
    
    def __init__(self, regions_to_scan: list):
        self.regions_to_scan = regions_to_scan
        # Atributos para armazenar os dados e resultados em memória
        self.vpcs: list[VPC] = []
        self.findings_df = pd.DataFrame()
        self.sg_risk_map = {}
        logging.info(f"Fábrica de Relatório VPC iniciada para {len(self.regions_to_scan)} região(ões).")

    def collect_data(self):
        """ETAPA 1: Coleta e hidrata todos os objetos de VPC e seus recursos."""
        logging.info("Coletando e construindo o modelo de dados em memória...")
        all_sgs_raw = []
        all_vpcs_raw = []
        session = boto3.Session()
        for region in self.regions_to_scan:
            logging.info(f"Coletando dados da região: {region}...")
            try:
                client = session.client('ec2', region_name=region)
                vpcs_data = client.describe_vpcs().get('Vpcs', [])
                sgs_data = client.describe_security_groups().get('SecurityGroups', [])
                for item in vpcs_data: item['Region'] = region
                for item in sgs_data: item['Region'] = region
                all_vpcs_raw.extend(vpcs_data)
                all_sgs_raw.extend(sgs_data)
            except Exception as e:
                logging.warning(f"Falha ao coletar dados da região {region}: {e}")
        
        vpcs_obj = [VPC(data) for data in all_vpcs_raw]
        sgs_obj = [SecurityGroup(data) for data in all_sgs_raw]
        
        sgs_by_vpc = defaultdict(list)
        for sg in sgs_obj: sgs_by_vpc[sg.vpc_id].append(sg)
        
        for vpc in vpcs_obj:
            vpc.security_groups = sgs_by_vpc.get(vpc.id, [])
        
        self.vpcs = vpcs_obj
        return self

    def analyze_security(self):
        """ETAPA 2: Analisa os SGs coletados e armazena os resultados internamente."""
        logging.info("Analisando riscos de segurança dos objetos...")
        all_sgs_objects = [sg for vpc in self.vpcs for sg in vpc.security_groups]
        
        # Chama a função de análise pura que importamos
        self.findings_df, self.sg_risk_map = analyze_sgs(all_sgs_objects)
        
        # Atualiza cada objeto SG com seu nível de risco para a coloração
        for sg in all_sgs_objects:
            sg.risk_level = self.sg_risk_map.get(sg.id, "Seguro")
        return self

    def generate_report(self, output_path: str):
        """ETAPA 3 e 4: Gera a planilha final, formatada, com links e a salva no disco."""
        logging.info("Gerando e formatando relatório final...")
        
        # Converte os objetos em listas de dicionários para criar os DataFrames
        data_frames = self._build_dataframes()
        
        # Gera o workbook em memória
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            sheet_order = ['Security_Analysis', 'VPCs', 'SecurityGroups']
            for sheet_name in sheet_order:
                if sheet_name in data_frames and not data_frames[sheet_name].empty:
                    df = data_frames[sheet_name]
                    df.to_excel(writer, sheet_name=sheet_name.replace('_Formatted',''), index=False)
        
        workbook = load_workbook(buffer)
        
        # Aplica a formatação final de cores, links e layout
        workbook = self._apply_final_formatting(workbook)

        # Salva o arquivo final no disco
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        workbook.save(output_path)
        logging.info(f"Relatório final gerado e salvo com sucesso em: {os.path.basename(output_path)}")

    def _build_dataframes(self):
        """Método privado para converter os objetos em DataFrames prontos para o Excel."""
        vpcs_for_df = [{'VPC ID': v.id, 'VPC Name': v.name, 'Region': v.region, 'CIDR Block': v.cidr_block} for v in self.vpcs]
        sgs_for_df = [
            {'GroupId': sg.id, 'GroupName': sg.name, 'VpcId': sg.vpc_id, 'Region': sg.region, 
             'Inbound Rules': formatters.format_rules(sg.raw_rules.get('IpPermissions', [])), 
             'Outbound Rules': formatters.format_rules(sg.raw_rules.get('IpPermissionsEgress', []))} 
            for v in self.vpcs for sg in v.security_groups
        ]
        return {
            'VPCs': pd.DataFrame(vpcs_for_df),
            'SecurityGroups': pd.DataFrame(sgs_for_df),
            'Security_Analysis': self.findings_df
        }

    def _apply_final_formatting(self, workbook):
        """Método privado para aplicar cores de linha, hyperlinks e layout."""
        LINKING_CONFIG = {'SecurityGroups': {'VpcId': 'VPCs'}, 'Security_Analysis': {'ID do Security Group': 'SecurityGroups'}}
        RED_FILL = PatternFill(start_color='FFC7CE', fill_type='solid')
        YELLOW_FILL = PatternFill(start_color='FFEB9C', fill_type='solid')
        GREEN_FILL = PatternFill(start_color='C6EFCE', fill_type='solid')
        
        id_maps = {sheet.title: {str(cell.value): cell.row for cell in sheet['A'] if cell.value is not None} for sheet in workbook}

        # Colore linhas na aba SecurityGroups
        if 'SecurityGroups' in workbook.sheetnames and self.sg_risk_map:
            sheet = workbook['SecurityGroups']
            try:
                sg_id_col_idx = [c.value for c in sheet[1]].index('GroupId') + 1
                for row_cells in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
                    sg_id = str(row_cells[sg_id_col_idx - 1].value)
                    risk_level = self.sg_risk_map.get(sg_id, "Seguro")
                    fill = {"Alto": RED_FILL, "Médio": YELLOW_FILL, "Seguro": GREEN_FILL}.get(risk_level)
                    if fill:
                        for cell in row_cells: cell.fill = fill
            except ValueError:
                logging.warning("Coluna 'GroupId' não encontrada para colorir linhas.")
        
        # Ajusta Layout Geral e Links
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            for col in sheet.columns:
                max_length = 0
                column_letter = get_column_letter(col[0].column)
                for cell in col:
                    cell.alignment = Alignment(wrap_text=True, vertical='top', horizontal='left')
                    if cell.value:
                        max_length = max(max_length, max(len(line) for line in str(cell.value).split('\n')))
                adjusted_width = (max_length + 2) * 1.2
                sheet.column_dimensions[column_letter].width = min(adjusted_width, 70)
        return workbook