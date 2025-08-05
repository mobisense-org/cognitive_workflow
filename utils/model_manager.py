import os
from typing import Optional
import whisper_timestamped as whisper
from pyannote.audio import Pipeline
import torch
import numpy as np
from utils.logger import setup_logger
from pyannote.audio.core.io import Audio
import time
logger = setup_logger(__name__)

class ModelManager:
    """Centralized model loading and caching service"""
    
    def __init__(self, whisper_cache_dir: str, pyannote_cache_dir: str, 
                 whisper_model_size: str = "turbo", 
                 pyannote_model_name: str = "pyannote/speaker-diarization-3.1",
                 pyannote_auth_token: Optional[str] = None):
        self._whisper_model = None
        self._diarization_pipeline = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # self.device = "cpu"
        
        # Store configuration
        self.whisper_cache_dir = whisper_cache_dir
        self.pyannote_cache_dir = pyannote_cache_dir
        self.whisper_model_size = whisper_model_size
        self.pyannote_model_name = pyannote_model_name
        self.pyannote_auth_token = pyannote_auth_token or os.getenv("HUGGINGFACE_TOKEN")
    
    def _warmup_whisper_model(self, model: whisper.Whisper) -> bool:
        """Warm up Whisper model with a small audio sample"""
        try:
            logger.info("Warming up Whisper model...")
            
            # Create a small dummy audio sample (1 second of silence at 16kHz)
            sample_rate = 16000
            duration = 1.0
            dummy_audio = np.zeros(int(sample_rate * duration), dtype=np.float32)
            
            # Run a small inference pass to warm up the model
            with torch.no_grad():
                result = model.transcribe(dummy_audio, language="en")
            
            logger.info("Whisper model warmed up successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Whisper model warmup failed: {e}")
            return False
    
    def _warmup_diarization_pipeline(self, pipeline: Pipeline) -> bool:
        """Warm up diarization pipeline with a small audio sample"""
        try:
            logger.info("Warming up diarization pipeline...")
            
            # Create a small dummy audio sample (2 seconds of silence at 16kHz)
            sample_rate = 16000
            duration = 2.0
            dummy_audio = np.zeros(int(sample_rate * duration), dtype=np.float32)
            
            # Convert to the format expected by pyannote
            audio = Audio(sample_rate=sample_rate, mono=True)
            waveform, sample_rate = audio.crop({"start": 0, "end": duration}, dummy_audio)
            
            # Run a small inference pass to warm up the pipeline
            with torch.no_grad():
                start_time = time.time()
                diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})
                end_time = time.time()
                logger.info(f"Diarization pipeline warmed up successfully in {end_time - start_time:.2f} seconds")
            logger.info("Diarization pipeline warmed up successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Diarization pipeline warmup failed: {e}")
            return False
    
    def get_optimized_transcription_params(self) -> dict:
        """Get optimized transcription parameters for CPU inference"""
        return {
            "beam_size": 1,  # Reduce beam search complexity
            "best_of": 1,    # Reduce candidate generation
            "temperature": 0.0,  # Deterministic output
            "condition_on_previous_text": False,  # Disable context conditioning
            "language": "en",  # Specify language to avoid detection overhead
            "task": "transcribe",
            "fp16": False,  # Disable FP16 on CPU
            "verbose": False  # Reduce logging overhead
        }
    
    def load_whisper_model(self) -> Optional[whisper.Whisper]:
        """Load Whisper model from cache if available, otherwise download"""
        if self._whisper_model is not None:
            return self._whisper_model
        
        try:
            logger.info(f"Loading Whisper model: {self.whisper_model_size}")
            
            # Map model sizes to actual file names
            model_filename_map = {
                "turbo": "large-v3-turbo.pt",
                "large-v3": "large-v3.pt", 
                "base": "base.pt",
                "small": "small.pt",
                "medium": "medium.pt",
                "large": "large.pt",
                "large-v2": "large-v2.pt"
            }
            
            # Check for existing model file first
            expected_filename = model_filename_map.get(self.whisper_model_size, f"{self.whisper_model_size}.pt")
            model_file = os.path.join(self.whisper_cache_dir, expected_filename)
            
            if os.path.exists(model_file):
                logger.info(f"Found cached Whisper model: {model_file}")
                os.environ["WHISPER_CACHE_DIR"] = self.whisper_cache_dir
                self._whisper_model = whisper.load_model(self.whisper_model_size, download_root=self.whisper_cache_dir, device=str(self.device))
            elif os.path.exists(self.whisper_cache_dir):
                logger.info(f"Cache directory exists but no {expected_filename} found, downloading...")
                os.environ["WHISPER_CACHE_DIR"] = self.whisper_cache_dir
                self._whisper_model = whisper.load_model(self.whisper_model_size, download_root=self.whisper_cache_dir, device=str(self.device))
            else:
                logger.info("Downloading Whisper model (no cache found)...")
                self._whisper_model = whisper.load_model(self.whisper_model_size, device=str(self.device))
            
            # Warm up the model after loading
            self._warmup_whisper_model(self._whisper_model)
            
            logger.info("Whisper model loaded successfully")
            return self._whisper_model
            
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            return None
    
    def load_diarization_pipeline(self) -> Optional[Pipeline]:
        """Load pyannote diarization model from cache if available"""
        if self._diarization_pipeline is not None:
            return self._diarization_pipeline
        
        try:
            logger.info("Loading pyannote speaker diarization pipeline...")
            
            # Set HuggingFace cache directories consistently
            if os.path.exists(self.pyannote_cache_dir):
                os.environ["HF_HOME"] = self.pyannote_cache_dir
                os.environ["TRANSFORMERS_CACHE"] = os.path.join(self.pyannote_cache_dir, "transformers")
                os.environ["HUGGINGFACE_HUB_CACHE"] = os.path.join(self.pyannote_cache_dir, "hub")
                logger.info(f"Using cached pyannote model from: {self.pyannote_cache_dir}")
            
            self._diarization_pipeline = Pipeline.from_pretrained(
                self.pyannote_model_name,
                use_auth_token=self.pyannote_auth_token,
                cache_dir=self.pyannote_cache_dir if os.path.exists(self.pyannote_cache_dir) else None
            )
            
            # Move to device after loading
            if hasattr(self._diarization_pipeline, 'to'):
                self._diarization_pipeline = self._diarization_pipeline.to(self.device)
            
            # Warm up the pipeline after loading
            self._warmup_diarization_pipeline(self._diarization_pipeline)
            
            logger.info("Diarization pipeline loaded successfully")
            return self._diarization_pipeline
            
        except Exception as e:
            logger.warning(f"Could not load diarization pipeline: {e}")
            if not self.pyannote_auth_token:
                logger.warning("Consider setting HUGGINGFACE_TOKEN environment variable for better model access")
            return None
    
    @property
    def whisper_model(self):
        """Get the loaded Whisper model"""
        return self.load_whisper_model()
    
    @property
    def diarization_pipeline(self):
        """Get the loaded diarization pipeline"""
        return self.load_diarization_pipeline()
    
    def is_ready(self) -> bool:
        """Check if all models are loaded"""
        return self.whisper_model is not None and self.diarization_pipeline is not None
    
    def preload_all_models(self) -> bool:
        """Preload all models into memory for immediate inference"""
        success = True
        
        try:
            # Force load Whisper model
            whisper_model = self.load_whisper_model()
            if not whisper_model:
                success = False
            
            # Force load diarization pipeline
            diarization_pipeline = self.load_diarization_pipeline()
            if not diarization_pipeline:
                success = False
                
        except Exception as e:
            logger.error(f"Error preloading models: {e}")
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
            logger.error(f"Error warming up models: {e}")
            success = False
            
        return success 