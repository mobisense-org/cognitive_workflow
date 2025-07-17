import os
from typing import Optional
import whisper_timestamped as whisper
from pyannote.audio import Pipeline
import torch
from utils.logger import setup_logger

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
        
        # Store configuration
        self.whisper_cache_dir = whisper_cache_dir
        self.pyannote_cache_dir = pyannote_cache_dir
        self.whisper_model_size = whisper_model_size
        self.pyannote_model_name = pyannote_model_name
        self.pyannote_auth_token = pyannote_auth_token or os.getenv("HUGGINGFACE_TOKEN")
    
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