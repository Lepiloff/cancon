from loguru import logger
import sys
import os

LOG_PATH = "/app/logs/django.log"

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logger.remove()

logger.add(LOG_PATH, rotation="10 MB", retention="10 days", compression="zip")

logger.add(sys.stdout, colorize=True, format="{time} {level} {message}", level="DEBUG")
