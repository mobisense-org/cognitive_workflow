import logging
import sys
from pathlib import Path
from config.settings import LOG_LEVEL, LOG_FILE

def setup_logger(name: str = "audio_workflow") -> logging.Logger:
    """Set up and configure logger for the workflow system."""
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger 