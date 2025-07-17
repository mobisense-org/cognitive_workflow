import json
from pathlib import Path
from typing import Any, Dict
from utils.logger import setup_logger
from config.settings import CURRENT_RUN_DIR, BASE_OUTPUTS_DIR
from datetime import datetime

logger = setup_logger(__name__)

def write_text_file(file_path: Path, content: str) -> bool:
    """Write text content to a file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Successfully wrote text to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing text file {file_path}: {e}")
        return False

def read_text_file(file_path: Path) -> str:
    """Read text content from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Successfully read text from {file_path}")
        return content
    except Exception as e:
        logger.error(f"Error reading text file {file_path}: {e}")
        return ""

def write_json_file(file_path: Path, data: Dict[str, Any]) -> bool:
    """Write JSON data to a file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully wrote JSON to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing JSON file {file_path}: {e}")
        return False

def read_json_file(file_path: Path) -> Dict[str, Any]:
    """Read JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully read JSON from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        return {}

def file_exists(file_path: Path) -> bool:
    """Check if a file exists."""
    return file_path.exists() and file_path.is_file() 

def get_output_file(filename: str) -> Path:
    """Get the path for an output file in the current run directory"""
    if CURRENT_RUN_DIR is None:
        create_run_directory()
    return CURRENT_RUN_DIR / filename

def create_run_directory():
    """Create a new timestamped run directory"""
    global CURRENT_RUN_DIR, CURRENT_RUN_TIMESTAMP
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    CURRENT_RUN_TIMESTAMP = timestamp
    run_dir = BASE_OUTPUTS_DIR / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    CURRENT_RUN_DIR = run_dir
    return run_dir
