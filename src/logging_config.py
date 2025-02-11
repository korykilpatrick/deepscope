import logging
import json_log_formatter

formatter = json_log_formatter.JSONFormatter()

json_handler = logging.StreamHandler()
json_handler.setFormatter(formatter)

logger = logging.getLogger("deepscope")
logger.setLevel(logging.INFO)
logger.addHandler(json_handler)

def get_logger():
    return logger