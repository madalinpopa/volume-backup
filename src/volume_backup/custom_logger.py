import logging
import sys


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name=name)
    logger.setLevel(logging.DEBUG)

    # Create a handler that outputs to standard output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("backup.log")
    file_handler.setLevel(logging.DEBUG)

    # Create a formatter and add it to the handler
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
