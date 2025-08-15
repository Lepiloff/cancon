from loguru import logger
import sys
import os

# Temporarily disable file logging to fix permission issues
logger.remove()
logger.add(sys.stdout, colorize=True, format="{time} {level} {message}", level="DEBUG")
