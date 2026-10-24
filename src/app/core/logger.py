import logging

try:
    from core.config import LOGGER_FORMAT
except ImportError:
    try:
        from config import LOGGER_FORMAT
    except ImportError:
        LOGGER_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    global _configured

    if _configured:
        return

    logging.basicConfig(level=level, format=LOGGER_FORMAT)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


logger = get_logger("app")
