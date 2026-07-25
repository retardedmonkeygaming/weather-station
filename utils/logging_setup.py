"""Centralized logging configuration."""
import logging
import sys


def setup_logging(level: int = logging.INFO):
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger("weather_station")
    logger.setLevel(level)
    logger.addHandler(handler)
    
    return logger