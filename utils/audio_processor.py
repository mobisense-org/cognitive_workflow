"""
Audio processing utilities for speed modification
"""
import torchaudio
import torch
from pathlib import Path
from typing import Tuple, Union
import tempfile
from utils.logger import setup_logger

logger = setup_logger(__name__)


def load_and_speed_audio(audio_path: Path, speed: float) -> Tuple[torch.Tensor, int]:
    """
    Load audio and modify speed in memory.
    
    Args:
        audio_path: Path to the input audio file
        speed: Speed multiplier (e.g., 1.5 for 1.5x speed, 2.0 for 2x speed)
        
    Returns:
        Tuple of (modified_waveform, sample_rate)
    """
    # Load audio
    waveform, sample_rate = torchaudio.load(str(audio_path))
    
    if speed == 1.0:
        return waveform, sample_rate
        
    logger.info(f"Modifying audio speed by {speed}x for {audio_path.name} in memory")
    
    try:
        # Apply speed change by resampling
        # For 2x speed: we want the audio to be half as long when played back
        # So we need to downsample the waveform by the speed factor
        target_length = int(waveform.shape[1] / speed)
        
        # Create a shorter version by taking every nth sample
        step = int(speed)
        modified_waveform = waveform[:, ::step]
        
        # If we need exact length, use interpolation
        if modified_waveform.shape[1] != target_length:
            import torch.nn.functional as F
            # Reshape for interpolation (add batch dimension)
            waveform_batch = modified_waveform.unsqueeze(0)  # (1, channels, samples)
            # Interpolate to exact target length
            interpolated = F.interpolate(waveform_batch, size=target_length, mode='linear', align_corners=False)
            modified_waveform = interpolated.squeeze(0)  # Remove batch dimension
        
        duration = modified_waveform.shape[1] / sample_rate
        logger.info(f"Audio speed modified: {duration:.1f}s duration ({speed}x faster)")
        return modified_waveform, sample_rate
        
    except Exception as e:
        logger.error(f"Failed to modify audio speed: {e}")
        logger.warning("Using original audio without speed modification")
        return waveform, sample_rate


def modify_audio_speed(audio_path: Path, speed: float) -> Path:
    """
    Legacy function for backward compatibility - still creates temp files.
    Use load_and_speed_audio() for in-memory processing.
    """
    if speed == 1.0:
        return audio_path
        
    waveform, sample_rate = load_and_speed_audio(audio_path, speed)
    
    # Create temporary file
    temp_fd, temp_path_str = tempfile.mkstemp(suffix=f"_speed_{speed}x.wav", prefix="audio_")
    temp_path = Path(temp_path_str)
    # Close the file descriptor as we'll use torchaudio to save
    import os
    os.close(temp_fd)
    
    # Save modified audio
    torchaudio.save(str(temp_path), waveform, sample_rate)
    
    logger.info(f"Audio speed modified and saved to {temp_path}")
    return temp_path


def get_audio_duration(audio_path: Path) -> float:
    """
    Get audio duration in seconds.
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Duration in seconds
    """
    try:
        waveform, sample_rate = torchaudio.load(str(audio_path))
        duration = waveform.shape[1] / sample_rate
        return duration
    except Exception as e:
        logger.warning(f"Could not get audio duration: {e}")
        return 0.0