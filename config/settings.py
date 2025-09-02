import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
API_KEY = os.getenv("API_KEY", "")
ENDPOINT = os.getenv("ENDPOINT", "https://aisuite.cirrascale.com/apis/v2")

# Model Configuration
WHISPER_MODEL_SIZE = "base" 
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"
DIARIZATION_BACKEND = "nemo"  # Options: "pyannote", "nemo"
SUMMARIZER_MODEL = "Llama-3.1-8B"
JUDGE_MODEL = "Llama-3.1-8B"
PYANNOTE_AUTH_TOKEN = os.getenv("HUGGINGFACE_TOKEN")  # Optional for cached models

# Diarization Configuration
DIARIZATION_MIN_SPEAKERS = 1
DIARIZATION_MAX_SPEAKERS = 5
DIARIZATION_MIN_DURATION_OFF = 0.5  # Minimum silence duration between speakers
DIARIZATION_MIN_DURATION_ON = 1.0   # Minimum duration for speech segments

# File Paths
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
WHISPER_MODELS_DIR = MODELS_DIR  / "whisper"
PYANNOTE_MODELS_DIR = MODELS_DIR / "pyannote"
AUDIO_INPUT_DIR = PROJECT_ROOT / "audio_input"

# Base outputs directory
BASE_OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Current run directory (will be set when workflow starts)
CURRENT_RUN_DIR = None
CURRENT_RUN_TIMESTAMP = None

# Dynamic output file paths (use get_output_file() to get current paths)
TRANSCRIPTION_FILE = "transcription.txt"
SUMMARY_FILE = "summary.txt"
JUDGMENT_FILE = "judgment.json"
PERFORMANCE_METRICS_FILE = "performance_metrics.json"

# Model Parameters
MAX_TOKENS = 2048
TEMPERATURE = 0.3

# Ensure directories exist
BASE_OUTPUTS_DIR.mkdir(exist_ok=True)
AUDIO_INPUT_DIR.mkdir(exist_ok=True)

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FILE = PROJECT_ROOT / "workflow.log" 

USE_AIHUB=False
APP_DEVICE="NPU"
ENCODER_PATH="ai-hub-apps/apps/windows/python/Whisper/build/whisper_base_en/WhisperEncoderInf/model.onnx"
DECODER_PATH="ai-hub-apps/apps/windows/python/Whisper/build/whisper_base_en/WhisperDecoderInf/model.onnx"