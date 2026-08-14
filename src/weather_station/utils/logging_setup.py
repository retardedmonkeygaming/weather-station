import logging
import sys

def setup_logging(level: str = "INFO"):
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # Clean up library logging noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)