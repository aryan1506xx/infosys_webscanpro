# log_config.py
import logging
import os
from pathlib import Path

LOG_PATH = Path("outputs/log.txt")
LOG_PATH.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_PATH),
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

def get_logger(name):
    return logging.getLogger(name)
