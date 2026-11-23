import logging
import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE, "logs")
LOG_PATH = os.path.join(LOG_DIR, "app.log")

_logger = None


def setup_logging(level=logging.INFO):
    global _logger
    if _logger is not None:
        return _logger
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("travel_itinerary")
    logger.setLevel(level)
    logger.propagate = False
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    _logger = logger
    return logger


def get_logger(name=None):
    return setup_logging().getChild(name) if name else setup_logging()
