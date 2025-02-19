import logging
import sys
from datetime import datetime

class Logger:
    """
    Logger utility for consistent logging across the project.
    """
    def __init__(self, name: str):
        """
        Initializes the logger with custom settings.
        :param name: Name of the logger (typically the module name).
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Define log format with timestamp
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # File handler
        log_filename = f"logs_{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        """
        Returns the configured logger instance.
        """
        return self.logger
