import logging.config
import os

try:
    logging.config.fileConfig('logging.ini')
except FileNotFoundError:
    os.mkdir('log')
logging.config.fileConfig('logging.ini')
logger = logging.getLogger('Watcher')
