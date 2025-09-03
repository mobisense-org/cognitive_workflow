import os
import tempfile
import wave
import struct
from typing import Optional, Union
import whisper_timestamped as whisper
from pyannote.audio import Pipeline
from config import settings
import torch
import numpy as np
from utils.logger import setup_logger
from pyannote.audio.core.io import Audio
import time

# Import NeMo components
try:
    from nemo.collections.asr.models import SortformerEncLabelModel

    NEMO_AVAILABLE = True
except ImportError:
    SortformerEncLabelModel = None
    NEMO_AVAILABLE = False
    print("[WARNING] NeMo not available. Install with: pip install nemo_toolkit[asr]")

logger = setup_logger(__name__)


class ModelManager:
    """Centralized model loading and caching service"""

    def __init__(self):
        self._whisper_model = None
        self._diarization_pipeline = None  # pyannote pipeline
        self._nemo_model = None  # nemo model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _warmup_whisper_model(self, model: whisper.Whisper) -> bool:
        """Warm up Whisper model with a small audio sample"""
        try:
            print("[INFO] Warming up Whisper model...")

            # Create a small dummy audio sample (1 second of silence at 16kHz)
            sample_rate = 16000
            duration = 1.0
            dummy_audio = np.zeros(int(sample_rate * duration), dtype=np.float32)

            # Run a small inference pass to warm up the model
            with torch.no_grad():
                result = model.transcribe(dummy_audio, language="en")

            print("[INFO] Whisper model warmed up successfully")
            return True

        except Exception as e:
            print(f"[WARNING] Whisper model warmup failed: {e}")
            return False

    def _warmup_diarization_pipeline(self, pipeline: Pipeline) -> bool:
        """Warm up diarization pipeline with a small audio sample"""
        temp_path = None
        try:
            print("[INFO] Warming up diarization pipeline...")

            # Create a small dummy audio sample (2 seconds of silence at 16kHz)
            sample_rate = 16000
            duration = 2.0
            dummy_audio = np.zeros(int(sample_rate * duration), dtype=np.float32)

            # Convert float32 to int16 for WAV format
            dummy_audio_int16 = (dummy_audio * 32767).astype(np.int16)

            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                
                with wave.open(temp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(dummy_audio_int16.tobytes())

            # Run a small inference pass to warm up the pipeline
            with torch.no_grad():
                start_time = time.time()
                diarization = pipeline(
                    temp_path,
                    min_speakers=1,
                    max_speakers=2
                )
                end_time = time.time()
                print(
                    f"[INFO] Diarization pipeline warmed up successfully in {end_time - start_time:.2f} seconds"
                )
            print("[INFO] Diarization pipeline warmed up successfully")
            return True

        except Exception as e:
            print(f"[WARNING] Diarization pipeline warmup failed: {e}")
            return False
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass

    def get_optimized_transcription_params(self) -> dict:
        """Get optimized transcription parameters for CPU inference"""
        return {
            "beam_size": 1,  # Reduce beam search complexity
            "best_of": 1,  # Reduce candidate generation
            "temperature": 0.0,  # Deterministic output
            "condition_on_previous_text": False,  # Disable context conditioning
            "language": "en",  # Specify language to avoid detection overhead
            "task": "transcribe",
            "fp16": False,  # Disable FP16 on CPU
            "verbose": False,  # Reduce logging overhead
        }

    def load_whisper_model(self) -> Optional[whisper.Whisper]:
        """Load Whisper model from cache if available, otherwise download"""
        if self._whisper_model is not None:
            return self._whisper_model

        try:
            whisper_cache = str(settings.WHISPER_MODELS_DIR)
            model_size = settings.WHISPER_MODEL_SIZE
            print(f"[INFO] Loading Whisper model: {model_size}")

            # Map model sizes to actual file names
            model_filename_map = {
                "turbo": "large-v3-turbo.pt",
                "large-v3": "large-v3.pt",
                "base": "base.pt",
                "small": "small.pt",
                "medium": "medium.pt",
                "large": "large.pt",
                "large-v2": "large-v2.pt",
            }

            # Check for existing model file first
            expected_filename = model_filename_map.get(model_size, f"{model_size}.pt")
            model_file = os.path.join(whisper_cache, expected_filename)

            if os.path.exists(model_file):
                print(f"[INFO] Found cached Whisper model: {model_file}")
                os.environ["WHISPER_CACHE_DIR"] = whisper_cache
                self._whisper_model = whisper.load_model(
                    model_size, download_root=whisper_cache, device=self.device
                )
            elif os.path.exists(whisper_cache):
                print(
                    f"[INFO] Cache directory exists but no {expected_filename} found, downloading..."
                )
                os.environ["WHISPER_CACHE_DIR"] = whisper_cache
                self._whisper_model = whisper.load_model(
                    model_size, download_root=whisper_cache, device=self.device
                )
            else:
                print("[INFO] Downloading Whisper model (no cache found)...")
                self._whisper_model = whisper.load_model(model_size, device=self.device)

            # Warm up the model after loading
            self._warmup_whisper_model(self._whisper_model)

            print("[INFO] Whisper model loaded successfully")
            return self._whisper_model

        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            return None

    def load_diarization_pipeline(self) -> Optional[Pipeline]:
        """Load pyannote diarization model from cache if available"""
        if self._diarization_pipeline is not None:
            return self._diarization_pipeline

        try:
            pyannote_cache = str(settings.PYANNOTE_MODELS_DIR)
            print("[INFO] Loading pyannote speaker diarization pipeline...")

            # Set HuggingFace cache directories consistently with download script
            if os.path.exists(pyannote_cache):
                os.environ["HF_HOME"] = pyannote_cache
                os.environ["TRANSFORMERS_CACHE"] = os.path.join(
                    pyannote_cache, "transformers"
                )
                os.environ["HUGGINGFACE_HUB_CACHE"] = os.path.join(
                    pyannote_cache, "hub"
                )
                print(f"[INFO] Using cached pyannote model from: {pyannote_cache}")

            auth_token = settings.PYANNOTE_AUTH_TOKEN or os.getenv("HUGGINGFACE_TOKEN")
            self._diarization_pipeline = Pipeline.from_pretrained(
                settings.DIARIZATION_MODEL,
                use_auth_token=auth_token,
                cache_dir=pyannote_cache if os.path.exists(pyannote_cache) else None,
            )

            # Move to device after loading
            if hasattr(self._diarization_pipeline, "to"):
                self._diarization_pipeline = self._diarization_pipeline.to(self.device)

            # Warm up the pipeline after loading
            self._warmup_diarization_pipeline(self._diarization_pipeline)

            print("[INFO] Diarization pipeline loaded successfully")
            return self._diarization_pipeline

        except Exception as e:
            print(f"Warning: Could not load diarization pipeline: {e}")
            if not settings.PYANNOTE_AUTH_TOKEN:
                print(
                    "Please set HUGGINGFACE_TOKEN environment variable or add it to config"
                )
            return None

    def load_nemo_model(self) -> Optional[SortformerEncLabelModel]:
        """Load NeMo diarization model from cache if available, otherwise download"""
        if self._nemo_model is not None:
            return self._nemo_model

        if not NEMO_AVAILABLE:
            print(
                "[ERROR] NeMo not available. Install with: pip install nemo_toolkit[asr]"
            )
            return None

        try:
            # Use pyannote cache dir for NeMo models as well, or create a separate one
            nemo_cache = str(settings.PYANNOTE_MODELS_DIR)
            model_name = (
                "nvidia/speakerverification_en_titanet_large"  # Default NeMo model
            )
            print(f"[INFO] Loading NeMo model: {model_name}")

            # Create cache directory if it doesn't exist
            if nemo_cache:
                os.makedirs(nemo_cache, exist_ok=True)

            # Check for locally saved model first
            local_model_path = os.path.join(nemo_cache, "diar_sortformer_4spk-v1.nemo")
            if os.path.exists(local_model_path):
                print(f"[INFO] Loading cached NeMo model from: {local_model_path}")
                self._nemo_model = SortformerEncLabelModel.restore_from(
                    restore_path=local_model_path,
                    map_location=str(self.device),
                    strict=False,
                )
            else:
                print(
                    f"[INFO] Cached model not found, downloading from Hugging Face..."
                )
                # Load model from Hugging Face
                self._nemo_model = SortformerEncLabelModel.from_pretrained(model_name)
                # Save model for future use
                print(f"[INFO] Saving model to: {local_model_path}")
                self._nemo_model.save_to(local_model_path)

            # Switch to evaluation mode
            self._nemo_model.eval()
            print(f"[INFO] NeMo model loaded successfully")
            return self._nemo_model

        except Exception as e:
            print(f"Warning: Could not load NeMo model: {e}")
            return None

    @property
    def whisper_model(self):
        """Get the loaded Whisper model"""
        return self.load_whisper_model()

    @property
    def nemo_model(self):
        """Get the loaded NeMo model"""
        return self.load_nemo_model()

    @property
    def diarization_pipeline(self):
        """Get the loaded diarization pipeline (pyannote)"""
        return self.load_diarization_pipeline()

    def get_diarization_model(self) -> Union[Pipeline, SortformerEncLabelModel, None]:
        """Get the appropriate diarization model based on configuration"""
        # For now, default to pyannote since we don't have a backend setting in current config
        # You can add DIARIZATION_BACKEND = "pyannote" or "nemo" to settings.py if needed
        backend = getattr(settings, "DIARIZATION_BACKEND", "pyannote").lower()

        if backend == "nemo":
            return self.load_nemo_model()
        elif backend == "pyannote":
            return self.load_diarization_pipeline()
        else:
            print(f"[ERROR] Unknown diarization backend: {backend}")
            return None

    def is_ready(self) -> bool:
        """Check if all models are loaded"""
        diarization_model = self.get_diarization_model()
        return self.whisper_model is not None and diarization_model is not None

    def preload_all_models(self) -> bool:
        """Preload all models into memory for immediate inference"""
        success = True

        try:
            # Force load Whisper model
            whisper_model = self.load_whisper_model()
            if not whisper_model:
                success = False

            # Force load diarization model based on backend
            diarization_model = self.get_diarization_model()
            if not diarization_model:
                success = False

        except Exception as e:
            print(f"Error preloading models: {e}")
            success = False

        return success

    def warmup_all_models(self) -> bool:
        """Explicitly warm up all loaded models"""
        success = True

        try:
            if self._whisper_model is not None:
                if not self._warmup_whisper_model(self._whisper_model):
                    success = False

            if self._diarization_pipeline is not None:
                if not self._warmup_diarization_pipeline(self._diarization_pipeline):
                    success = False

        except Exception as e:
            print(f"Error warming up models: {e}")
            success = False

        return success


# Global model manager instance
model_manager = ModelManager()
