#!/usr/bin/env python3
"""
Local Whisper Transcription Script

This script loads locally compiled ONNX models and transcribes audio files
without using Hugging Face. It uses the same WhisperApp infrastructure as
the original demo but with local ONNX models.
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import onnxruntime

# Add the ai-hub-models directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "ai-hub-models"))

from qai_hub_models.models._shared.whisper.app import WhisperApp
from qai_hub_models.utils.onnx_torch_wrapper import (
    OnnxModelTorchWrapper,
    OnnxSessionOptions,
)


def load_local_whisper_models(encoder_path: str, decoder_path: str):
    """
    Load local ONNX models for Whisper encoder and decoder.
    
    Args:
        encoder_path: Path to the encoder ONNX model
        decoder_path: Path to the decoder ONNX model
    
    Returns:
        tuple: (encoder_model, decoder_model)
    """
    print(f"Loading encoder from: {encoder_path}")
    print(f"Loading decoder from: {decoder_path}")
    
    # Create session options
    session_options = OnnxSessionOptions()
    
    # Load encoder model
    encoder_model = OnnxModelTorchWrapper.OnCPU(
        encoder_path,
        session_options=session_options,
        quantize_io=True
    )
    
    # Load decoder model  
    decoder_model = OnnxModelTorchWrapper.OnCPU(
        decoder_path,
        session_options=session_options,
        quantize_io=True
    )
    
    print("Models loaded successfully!")
    return encoder_model, decoder_model


def transcribe_audio_file(
    audio_file_path: str,
    encoder_model,
    decoder_model,
    num_decoder_blocks: int = 6,
    num_decoder_heads: int = 8,
    attention_dim: int = 512,
    mean_decode_len: int = 224
):
    """
    Transcribe an audio file using the loaded Whisper models.
    
    Args:
        audio_file_path: Path to the audio file to transcribe
        encoder_model: Loaded encoder model
        decoder_model: Loaded decoder model
        num_decoder_blocks: Number of decoder blocks
        num_decoder_heads: Number of decoder heads
        attention_dim: Attention dimension
        mean_decode_len: Mean decode length
    
    Returns:
        str: Transcribed text
    """
    # Create WhisperApp instance
    app = WhisperApp(
        encoder_model,
        decoder_model,
        num_decoder_blocks=num_decoder_blocks,
        num_decoder_heads=num_decoder_heads,
        attention_dim=attention_dim,
        mean_decode_len=mean_decode_len,
    )
    
    print(f"Transcribing audio file: {audio_file_path}")
    
    # Perform transcription
    transcription = app.transcribe(audio_file_path)
    
    return transcription


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio using local ONNX Whisper models"
    )
    parser.add_argument(
        "audio_file",
        help="Path to the audio file to transcribe"
    )
    parser.add_argument(
        "--encoder-path",
        default="models/whisper-onnx/whisper-encoder/model.onnx/model.onnx",
        help="Path to the encoder ONNX model"
    )
    parser.add_argument(
        "--decoder-path", 
        default="models/whisper-onnx/whisper-decoder/model.onnx/model.onnx",
        help="Path to the decoder ONNX model"
    )
    parser.add_argument(
        "--num-decoder-blocks",
        type=int,
        default=6,
        help="Number of decoder blocks"
    )
    parser.add_argument(
        "--num-decoder-heads",
        type=int,
        default=8,
        help="Number of decoder heads"
    )
    parser.add_argument(
        "--attention-dim",
        type=int,
        default=512,
        help="Attention dimension"
    )
    parser.add_argument(
        "--mean-decode-len",
        type=int,
        default=224,
        help="Mean decode length"
    )
    
    args = parser.parse_args()
    
    # Check if audio file exists
    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file '{args.audio_file}' not found!")
        sys.exit(1)
    
    # Check if model files exist
    if not os.path.exists(args.encoder_path):
        print(f"Error: Encoder model '{args.encoder_path}' not found!")
        sys.exit(1)
    
    if not os.path.exists(args.decoder_path):
        print(f"Error: Decoder model '{args.decoder_path}' not found!")
        sys.exit(1)
    
    try:
        # Load models
        encoder_model, decoder_model = load_local_whisper_models(
            args.encoder_path, args.decoder_path
        )
        
        # Transcribe audio
        transcription = transcribe_audio_file(
            args.audio_file,
            encoder_model,
            decoder_model,
            num_decoder_blocks=args.num_decoder_blocks,
            num_decoder_heads=args.num_decoder_heads,
            attention_dim=args.attention_dim,
            mean_decode_len=args.mean_decode_len
        )
        
        # Print results
        print("\n" + "="*50)
        print("TRANSCRIPTION RESULT:")
        print("="*50)
        print(transcription)
        print("="*50)
        
    except Exception as e:
        print(f"Error during transcription: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 