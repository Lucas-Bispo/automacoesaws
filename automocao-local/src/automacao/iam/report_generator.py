# Este pode usar a mesma lógica simples do gerador de EC2
from .super.ec2.report_generator import create_report as create_iam_report

def create_report(output_path: str, data_frames: dict):
    # Reutilizando a lógica, mas com um log diferente
    create_iam_report(output_path, data_frames)
    logging.info(f"Relatório de IAM gerado em: {output_path}")