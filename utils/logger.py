# Python Libraries
import logging

# External Libraries

# PIA Libraries

def setup_logger(name: str) -> logging.Logger:
    logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler("agent_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)