import logging
import sys

def setup_logging():
    """Configura o formato de logging padrão para a aplicação."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        stream=sys.stdout
    )