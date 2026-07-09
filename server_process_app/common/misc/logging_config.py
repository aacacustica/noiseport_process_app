import logging
import os

from server_process_app.common.utils.utils import * 

config = load_config()

FULL_PATH_LOG_DIR = config['paths']['logs']

def setup_logging(script_name, level=logging.INFO):

    os.makedirs(FULL_PATH_LOG_DIR, exist_ok=True)

    #log file 
    log_file = os.path.join(FULL_PATH_LOG_DIR, f"{script_name}.log")
    

    logger = logging.getLogger(script_name)
    logger.setLevel(level)


    #keeping  console handler quiet
    logger.propagate = False

    # file handler overwrites the log file each time
    file_handler = logging.FileHandler(log_file, mode='w')
    file_formatter = logging.Formatter('%(asctime)s - %(filename)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)


    # preventing duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()


    logger.addHandler(file_handler)
    return logger
