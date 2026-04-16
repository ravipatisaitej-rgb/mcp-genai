import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", name: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


class ToolLogger:
    def __init__(self, tool_name: str, level: str = "INFO"):
        self.logger = setup_logging(level, name=tool_name)

    def debug(self, message: str, **kwargs):
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        self.logger.critical(message, extra=kwargs)
