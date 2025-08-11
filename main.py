#!/usr/bin/env python3
"""
Audio Workflow Analysis System - Main Orchestrator

This script coordinates the three-step audio analysis workflow:
1. Transcription using Whisper v3 Large Turbo
2. Summarization using AI model
3. Situation judgment and action classification
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from modules.transcriber import AudioTranscriber
from modules.summarizer import ConversationSummarizer
from modules.judge import SituationJudge
from utils.logger import setup_logger
from utils.file_handler import file_exists, get_output_file
from utils.evaluator import evaluator
from config.settings import (
    TRANSCRIPTION_FILE, 
    SUMMARY_FILE, 
    JUDGMENT_FILE,
    PERFORMANCE_METRICS_FILE,
    AUDIO_INPUT_DIR,
)

logger = setup_logger(__name__)

class AudioWorkflowOrchestrator:
    """Main orchestrator for the audio workflow analysis system."""
    
    def __init__(self):
        """Initialize the workflow components."""
        self.transcriber = None
        self.summarizer = None
        self.judge = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all workflow components."""
        try:
            logger.info("Initializing workflow components...")
            
            # Initialize transcriber (this may take some time due to model loading)
            logger.info("Loading transcription model...")
            self.transcriber = AudioTranscriber()
            
            # Initialize summarizer
            self.summarizer = ConversationSummarizer()
            
            # Initialize judge
            self.judge = SituationJudge()
            
            logger.info("All workflow components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize workflow components: {e}")
            raise
    
    def run_full_workflow(self, audio_file_path: Path, speed: float = 1.0) -> bool:
        """
        Run the complete three-step workflow.
        
        Args:
            audio_file_path: Path to the input audio file
            
        Returns:
            True if all steps completed successfully, False otherwise
        """
        logger.info(f"Starting full workflow for {audio_file_path}")
        
        # Start performance tracking
        evaluator.start_workflow_tracking(str(audio_file_path))
        
        try:
            # Step 1: Transcription
            logger.info("=== STEP 1: TRANSCRIPTION ===")
            if not self.run_transcription(audio_file_path, speed=speed):
                logger.error("Transcription step failed")
                return False
            
            # Step 2: Summarization
            logger.info("=== STEP 2: SUMMARIZATION ===")
            if not self.run_summarization():
                logger.error("Summarization step failed")
                return False
            
            # Step 3: Situation Judgment
            logger.info("=== STEP 3: SITUATION JUDGMENT ===")
            if not self.run_judgment():
                logger.error("Judgment step failed")
                return False
            
            logger.info("=== WORKFLOW COMPLETED SUCCESSFULLY ===")
            self._display_results()
            
            # Finalize performance metrics
            workflow_metrics = evaluator.finalize_workflow_metrics()
            
            return True
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            return False
    
    def run_transcription(self, audio_file_path: Path, speed: float = 1.0) -> bool:
        """Run the transcription step."""
        if not file_exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return False
        
        return self.transcriber.transcribe_and_save(audio_file_path, speed=speed)
    
    def run_summarization(self) -> bool:
        """Run the summarization step."""
        transcription_file = get_output_file(TRANSCRIPTION_FILE)
        if not file_exists(transcription_file):
            logger.error(f"Transcription file not found: {transcription_file}")
            return False
        
        return self.summarizer.summarize_and_save(transcription_file)
    
    def run_judgment(self) -> bool:
        """Run the judgment step."""
        summary_file = get_output_file(SUMMARY_FILE)
        if not file_exists(summary_file):
            logger.error(f"Summary file not found: {summary_file}")
            return False
        
        return self.judge.analyze_and_save(summary_file)
    
    def _display_results(self):
        """Display a summary of the workflow results."""
        logger.info("\n" + "="*60)
        logger.info("WORKFLOW RESULTS SUMMARY")
        logger.info("="*60)
        
        # Check output files
        files_info = [
            (get_output_file(TRANSCRIPTION_FILE), "Transcription"),
            (get_output_file(SUMMARY_FILE), "Summary"),
            (get_output_file(JUDGMENT_FILE), "Judgment"),
            (get_output_file(PERFORMANCE_METRICS_FILE), "Performance Metrics")
        ]
        
        for file_path, file_type in files_info:
            if file_exists(file_path):
                size = file_path.stat().st_size
                logger.info(f"{file_type}: {file_path} ({size} bytes)")
            else:
                logger.info(f"{file_type}: {file_path} (not found)")
        
        logger.info("="*60)
    
    def show_performance_report(self):
        """Display performance analysis report"""
        report = evaluator.generate_performance_report()
        print("\n" + report)

def find_audio_files(directory: Path) -> list[Path]:
    """Find all audio files in the specified directory."""
    audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac'}
    
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(directory.glob(f"*{ext}"))
        audio_files.extend(directory.glob(f"*{ext.upper()}"))
    
    return sorted(audio_files)

def main():
    """Main entry point for the audio workflow system."""
    parser = argparse.ArgumentParser(
        description="Audio Workflow Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py /path/to/audio.wav            # Process specific audio file
  python main.py                               # Process first audio file in audio_input/
  python main.py --list-files                  # List available audio files
  python main.py --step transcribe audio.wav   # Run only transcription step
  python main.py --speed 1.5 audio.wav         # Process audio at 1.5x speed
  python main.py --speed 2.0 --step transcribe audio.wav # Transcribe at 2x speed
  python main.py --performance-report          # Show performance metrics report
        """
    )
    
    parser.add_argument(
        'audio_file',
        nargs='?',
        help='Path to audio file to process'
    )
    
    parser.add_argument(
        '--step',
        choices=['transcribe', 'summarize', 'judge', 'all'],
        default='all',
        help='Run specific step only (default: all)'
    )
    
    parser.add_argument(
        '--list-files',
        action='store_true',
        help='List available audio files in audio_input directory'
    )
    
    parser.add_argument(
        '--performance-report',
        action='store_true',
        help='Show performance analysis report from historical data'
    )
    
    parser.add_argument(
        '--speed',
        type=float,
        default=1.0,
        help='Audio playback speed multiplier (e.g., 1.5 for 1.5x speed, 2.0 for 2x speed)'
    )
    
    args = parser.parse_args()
    
    try:
        # Handle list files option
        if args.list_files:
            audio_files = find_audio_files(AUDIO_INPUT_DIR)
            if audio_files:
                print(f"\nFound {len(audio_files)} audio file(s) in {AUDIO_INPUT_DIR}:")
                for i, file_path in enumerate(audio_files, 1):
                    print(f"  {i}. {file_path.name}")
            else:
                print(f"\nNo audio files found in {AUDIO_INPUT_DIR}")
            return
        
        # Handle performance report option
        if args.performance_report:
            orchestrator = AudioWorkflowOrchestrator()
            orchestrator.show_performance_report()
            return
        
        # Determine audio file to process
        audio_file_path = None
        
        if args.audio_file:
            audio_file_path = Path(args.audio_file)
        else:
            # Look for audio files in the input directory
            audio_files = find_audio_files(AUDIO_INPUT_DIR)
            if audio_files:
                audio_file_path = audio_files[0]
                logger.info(f"No audio file specified, using: {audio_file_path}")
            else:
                logger.error(f"No audio file specified and none found in {AUDIO_INPUT_DIR}")
                logger.info("Use --list-files to see available files")
                sys.exit(1)
        
        # Initialize orchestrator
        orchestrator = AudioWorkflowOrchestrator()
        
        # Run requested workflow steps
        if args.step == 'all':
            success = orchestrator.run_full_workflow(audio_file_path, speed=args.speed)
        elif args.step == 'transcribe':
            success = orchestrator.run_transcription(audio_file_path, speed=args.speed)
        elif args.step == 'summarize':
            success = orchestrator.run_summarization()
        elif args.step == 'judge':
            success = orchestrator.run_judgment()
        
        if success:
            logger.info("Workflow completed successfully!")
            sys.exit(0)
        else:
            logger.error("Workflow failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 