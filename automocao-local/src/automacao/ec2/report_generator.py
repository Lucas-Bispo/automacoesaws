import os
import pandas as pd
import logging

def create_report(output_path: str, data_frames: dict):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name, df in data_frames.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    logging.info(f"Relatório de EC2 gerado em: {output_path}")