#!/usr/bin/env python3
"""
Model Download Script
Downloads and caches Whisper and pyannote models locally
Usage: python download_models.py [--whisper-model base] [--models-dir ./models]
"""

import os
import sys
import argparse
from pathlib import Path
import whisper
from pyannote.audio import Pipeline
from dotenv import load_dotenv
import torch

load_dotenv()

def setup_cache_directories(models_dir: str):
    """Create cache directories"""
    models_path = Path(models_dir)
    whisper_cache = models_path / "whisper" / "whisper"
    pyannote_cache = models_path / "pyannote"
    
    whisper_cache.mkdir(parents=True, exist_ok=True)
    pyannote_cache.mkdir(parents=True, exist_ok=True)
    
    return whisper_cache, pyannote_cache

def download_whisper_model(model_size: str, cache_dir: Path):
    """Download Whisper model to cache directory"""
    print(f"[INFO] Downloading Whisper model '{model_size}'...")
    
    # Set environment variable to use our cache directory
    os.environ["WHISPER_CACHE_DIR"] = str(cache_dir)
    
    try:
        model = whisper.load_model(model_size, download_root=str(cache_dir))
        print(f"[SUCCESS] Whisper model '{model_size}' downloaded successfully")
        print(f"[INFO] Cached in: {cache_dir}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download Whisper model: {e}")
        return False

def download_pyannote_model(cache_dir: Path):
    """Download pyannote diarization model to cache directory"""
    print("[INFO] Downloading pyannote speaker-diarization model...")
    
    # Get HuggingFace token
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if not hf_token or hf_token == "your_huggingface_token_here":
        print("[ERROR] HUGGINGFACE_TOKEN not found in environment")
        print("[INFO] Get token from: https://huggingface.co/settings/tokens")
        print("[INFO] Add to .env file: HUGGINGFACE_TOKEN=your_token_here")
        return False
    
    # Set HuggingFace cache directory
    os.environ["HF_HOME"] = str(cache_dir)
    os.environ["TRANSFORMERS_CACHE"] = str(cache_dir / "transformers")
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(cache_dir / "hub")
    
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
            cache_dir=str(cache_dir)
        )
        print("[SUCCESS] Pyannote model downloaded successfully")
        print(f"[INFO] Cached in: {cache_dir}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download pyannote model: {e}")
        print("[INFO] Make sure your HuggingFace token has access to pyannote models")
        return False

def verify_models(models_dir: str, whisper_model: str):
    """Verify that models are properly cached"""
    print("\n[INFO] Verifying cached models...")
    
    models_path = Path(models_dir)
    whisper_cache = models_path / "whisper" / "whisper"
    pyannote_cache = models_path / "pyannote"
    
    success = True
    
    # Check Whisper model
    whisper_files = list(whisper_cache.glob("*.pt"))
    if whisper_files:
        print(f"[SUCCESS] Whisper model found: {len(whisper_files)} files")
        for file in whisper_files:
            print(f"[INFO]   {file.name}")
    else:
        print("[ERROR] Whisper model not found in cache")
        success = False
    
    # Check pyannote model
    pyannote_files = list(pyannote_cache.rglob("*"))
    pyannote_files = [f for f in pyannote_files if f.is_file()]
    if pyannote_files:
        print(f"[SUCCESS] Pyannote model found: {len(pyannote_files)} files")
        # Show a few example files
        for file in pyannote_files[:3]:
            print(f"[INFO]   {file.relative_to(pyannote_cache)}")
        if len(pyannote_files) > 3:
            print(f"[INFO]   ... and {len(pyannote_files) - 3} more files")
    else:
        print("[ERROR] Pyannote model not found in cache")
        success = False
    
    return success

def get_cache_size(models_dir: str):
    """Calculate total size of cached models"""
    models_path = Path(models_dir)
    total_size = 0
    
    for file in models_path.rglob("*"):
        if file.is_file():
            total_size += file.stat().st_size
    
    # Convert to human readable
    if total_size > 1024**3:  # GB
        size_str = f"{total_size / 1024**3:.1f} GB"
    elif total_size > 1024**2:  # MB
        size_str = f"{total_size / 1024**2:.1f} MB"
    else:  # KB
        size_str = f"{total_size / 1024:.1f} KB"
    
    return size_str

def main():
    parser = argparse.ArgumentParser(description="Download and cache AI models locally")
    parser.add_argument("--whisper-model", default="turbo", 
                        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "turbo"],
                        help="Whisper model size to download")
    parser.add_argument("--models-dir", default="./models",
                        help="Directory to store cached models")
    parser.add_argument("--skip-whisper", action="store_true",
                        help="Skip Whisper model download")
    parser.add_argument("--skip-pyannote", action="store_true", 
                        help="Skip pyannote model download")
    
    args = parser.parse_args()
    
    print("AI Model Downloader")
    print("==================")
    print(f"Models directory: {args.models_dir}")
    print(f"Whisper model: {args.whisper_model}")
    print()
    
    # Setup cache directories
    whisper_cache, pyannote_cache = setup_cache_directories(args.models_dir)
    
    success = True
    
    # Download Whisper model
    if not args.skip_whisper:
        if not download_whisper_model(args.whisper_model, whisper_cache):
            success = False
    
    print()
    
    # Download pyannote model
    if not args.skip_pyannote:
        if not download_pyannote_model(pyannote_cache):
            success = False
    
    print()
    
    # Verify models
    if verify_models(args.models_dir, args.whisper_model):
        cache_size = get_cache_size(args.models_dir)
        print(f"\n[SUCCESS] All models cached successfully!")
        print(f"[INFO] Location: {os.path.abspath(args.models_dir)}")
        print(f"[INFO] Total size: {cache_size}")
        
        print(f"\n[INFO] To use cached models:")
        print(f"   export WHISPER_CACHE_DIR={os.path.abspath(whisper_cache)}")
        print(f"   export HF_HOME={os.path.abspath(pyannote_cache)}")
        
        # If verification passes, exit successfully regardless of download attempts
        sys.exit(0)
    else:
        print("\n[ERROR] Some models failed to download")
        sys.exit(1)

if __name__ == "__main__":
    main() 