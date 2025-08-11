import whisper_timestamped as whisper
import time
import torchaudio
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from pyannote.audio import Pipeline
from pyannote.core import Annotation, Segment
import warnings
from utils.logger import setup_logger
from utils.file_handler import write_text_file, get_output_file
from utils.evaluator import evaluator
from config.settings import (
    TRANSCRIPTION_FILE, 
    WHISPER_MODEL_SIZE,
    DIARIZATION_MODEL, 
    DIARIZATION_MIN_SPEAKERS, 
    DIARIZATION_MAX_SPEAKERS,
    DIARIZATION_MIN_DURATION_OFF,
    DIARIZATION_MIN_DURATION_ON,
    WHISPER_MODELS_DIR,
    PYANNOTE_MODELS_DIR,
    PYANNOTE_AUTH_TOKEN,
    USE_AIHUB,
    APP_DEVICE,
    ENCODER_PATH,
    DECODER_PATH
)
from utils.model_manager import ModelManager
import torch
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote")

logger = setup_logger(__name__)

class DiarizationService:
    """Service for speaker diarization using pyannote via ModelManager"""
    
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.diarization_pipeline = None
        self._load_pipeline()
    
    def _load_pipeline(self):
        """Load the diarization pipeline using model manager"""
        try:
            self.diarization_pipeline = self.model_manager.load_diarization_pipeline()
            
            if self.diarization_pipeline:
                # Optimize pipeline for speed and accuracy
                self._configure_pipeline_for_performance()
                logger.info("Diarization pipeline loaded and configured successfully")
            else:
                logger.warning("Diarization pipeline not available")
                
        except Exception as e:
            logger.warning(f"Could not load diarization pipeline: {e}")
            logger.info("Diarization will not be available")
            self.diarization_pipeline = None
    
    def _configure_pipeline_for_performance(self):
        """Configure pipeline parameters for optimal performance and accuracy"""
        if not self.diarization_pipeline:
            return
            
        try:
            # Configure segmentation for better speaker boundary detection
            if hasattr(self.diarization_pipeline, '_segmentation'):
                seg = self.diarization_pipeline._segmentation
                seg.min_duration_off = DIARIZATION_MIN_DURATION_OFF  # Longer silence = more confident speaker change
                if hasattr(seg, 'min_duration_on'):
                    seg.min_duration_on = DIARIZATION_MIN_DURATION_ON   # Minimum speech duration
                
            # Configure speaker clustering for better separation
            if hasattr(self.diarization_pipeline, '_clustering'):
                clustering = self.diarization_pipeline._clustering
                clustering.method = "centroid"
                clustering.min_cluster_size = 10  # Minimum frames per speaker
                clustering.threshold = 0.7155  # Optimized threshold for speaker separation
                
            # Configure embedding extraction for faster processing
            if hasattr(self.diarization_pipeline, '_embedding'):
                emb = self.diarization_pipeline._embedding
                if hasattr(emb, 'batch_size'):
                    emb.batch_size = 32  # Larger batch for faster processing
                    
            logger.info("Diarization pipeline optimized for performance")
            
        except Exception as e:
            logger.warning(f"Could not fully optimize diarization pipeline: {e}")
            logger.info("Using default pipeline configuration")
    
    def diarize(self, audio_path: str) -> Tuple[Optional[Annotation], float]:
        """Perform speaker diarization on audio file with timeout and fallback"""
        if self.diarization_pipeline is None:
            logger.warning("Diarization pipeline not available, skipping speaker diarization")
            return None, 0.0
        
        try:
            logger.info(f"Starting diarization for: {Path(audio_path).name}")
            diarization_start = time.time()
            
            # Get audio duration to estimate processing time
            audio_duration = 0
            try:
                waveform, sample_rate = torchaudio.load(audio_path)
                audio_duration = waveform.shape[1] / sample_rate
                logger.info(f"Audio duration: {audio_duration:.1f}s")
            except:
                pass
            
            # For shorter audio files, use a timeout to prevent excessive processing
            max_processing_time = max(audio_duration * 0.8, 15.0) if audio_duration > 0 else 30.0
            logger.info(f"Diarization timeout set to: {max_processing_time:.1f}s")
            
            # Apply diarization with optimized parameters  
            diarization = self.diarization_pipeline(
                audio_path,
                min_speakers=DIARIZATION_MIN_SPEAKERS,
                max_speakers=DIARIZATION_MAX_SPEAKERS
            )
            
            diarization_time = time.time() - diarization_start
            
            # Log performance ratio
            if audio_duration > 0:
                efficiency_ratio = audio_duration / diarization_time
                logger.info(f"Diarization efficiency: {efficiency_ratio:.2f}x realtime")
                
                # If diarization took too long, recommend skipping it next time
                if diarization_time > max_processing_time:
                    logger.warning(f"Diarization took {diarization_time:.1f}s (>{max_processing_time:.1f}s timeout) - consider using rule-based fallback")
            
            # Log diarization stats and validate results
            if diarization:
                speakers = set()
                total_speech_duration = 0
                speaker_durations = {}
                
                for segment, _, speaker in diarization.itertracks(yield_label=True):
                    speakers.add(speaker)
                    total_speech_duration += segment.duration
                    
                    if speaker not in speaker_durations:
                        speaker_durations[speaker] = 0
                    speaker_durations[speaker] += segment.duration
                
                # Filter out speakers with very short durations (likely noise)
                min_speaker_duration = 2.0  # Minimum 2 seconds to be considered a real speaker
                valid_speakers = {speaker for speaker, duration in speaker_durations.items() 
                                if duration >= min_speaker_duration}
                
                if len(valid_speakers) < len(speakers):
                    logger.info(f"Filtered out {len(speakers) - len(valid_speakers)} speakers with insufficient speech duration")
                
                logger.info(f"Diarization completed: {len(valid_speakers)} valid speakers detected "
                           f"({len(speakers)} total), {total_speech_duration:.2f}s total speech duration, "
                           f"processing time: {diarization_time:.2f}s")
                
                # Log speaker timeline with durations
                logger.info("Speaker timeline:")
                for turn, track, speaker in diarization.itertracks(yield_label=True):
                    if speaker in valid_speakers:  # Only log valid speakers
                        start_min = int(turn.start // 60)
                        start_sec = int(turn.start % 60)
                        end_min = int(turn.end // 60)
                        end_sec = int(turn.end % 60)
                        duration = turn.duration
                        logger.info(f"  {speaker}: {start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d} ({duration:.1f}s)")
                
                # Update the annotation to only include valid speakers
                if len(valid_speakers) > 0 and len(valid_speakers) != len(speakers):
                    # Create new annotation with only valid speakers
                    filtered_diarization = Annotation()
                    for segment, _, speaker in diarization.itertracks(yield_label=True):
                        if speaker in valid_speakers:
                            filtered_diarization[segment] = speaker
                    diarization = filtered_diarization
                    
            else:
                logger.warning("Diarization returned empty result")
            
            return diarization, diarization_time
            
        except Exception as e:
            logger.error(f"Diarization failed for {audio_path}: {str(e)}")
            # Transcription can still work
            return None, 0.0
    
    def is_available(self) -> bool:
        """Check if diarization service is available"""
        return self.diarization_pipeline is not None


class TranscriptionService:
    """Service for audio transcription using Whisper via ModelManager"""
    
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.whisper_model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model using model manager"""
        try:
            if USE_AIHUB:
                from qai_hub_models.models._shared.whisper.app import WhisperApp
                from qai_hub_models.utils.onnx_torch_wrapper import OnnxModelTorchWrapper
                
                logger.info("Loading AI Hub Whisper app")
                if APP_DEVICE == "NPU":
                    self.app = WhisperApp(
                        OnnxModelTorchWrapper.OnNPU(ENCODER_PATH),
                        OnnxModelTorchWrapper.OnNPU(DECODER_PATH),
                        num_decoder_blocks=6,
                        num_decoder_heads=8,
                        attention_dim=512,
                        mean_decode_len=224,
                    )
                else:
                    self.app = WhisperApp(
                        OnnxModelTorchWrapper.OnCPU(ENCODER_PATH),
                        OnnxModelTorchWrapper.OnCPU(DECODER_PATH),
                        num_decoder_blocks=6,
                        num_decoder_heads=8,
                        attention_dim=512,
                        mean_decode_len=224,
                    )
                self.whisper_model = None  # Not used in AI Hub mode
                logger.info("AI Hub Whisper app loaded successfully")
            else:
                self.whisper_model = self.model_manager.load_whisper_model()
                self.app = None  # Not used in regular mode
                if not self.whisper_model:
                    raise Exception("Failed to load Whisper model via ModelManager")
                logger.info("Whisper model loaded successfully via ModelManager")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe(self, audio_path: str) -> Tuple[Dict[str, Any], float]:
        """Transcribe audio file using Whisper model"""
        if USE_AIHUB:
            raise Exception("Use transcribe_aihub() method when USE_AIHUB is True")
            
        if self.whisper_model is None:
            raise Exception("Whisper model not available")
        
        try:
            logger.info(f"Starting transcription for: {Path(audio_path).name}")
            
            # Get optimized parameters
            optimized_params = self.model_manager.get_optimized_transcription_params()
                        
            transcription_start = time.time()
            result = whisper.transcribe(
                self.whisper_model, 
                audio_path,
                **optimized_params
            )
            transcription_time = time.time() - transcription_start
            
            # Log transcription stats
            segments = result.get("segments", [])
            duration = result.get("duration", 0)
            language = result.get("language", "unknown")
            
            logger.info(f"Transcription completed: {len(segments)} segments, "
                       f"{duration:.2f}s duration, language: {language}, "
                       f"processing time: {transcription_time:.2f}s")
            
            return result, transcription_time
            
        except Exception as e:
            logger.error(f"Transcription failed for {audio_path}: {str(e)}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if transcription service is available"""
        if USE_AIHUB:
            return self.app is not None
        else:
            return self.whisper_model is not None

    def transcribe_aihub(self, audio_path: str) -> Tuple[Dict[str, Any], float]:
        """Transcribe audio file using AI Hub Whisper app"""
        if not USE_AIHUB:
            raise Exception("Use transcribe() method when USE_AIHUB is False")
            
        if self.app is None:
            raise Exception("AI Hub Whisper app not available")
        
        try:
            logger.info(f"Starting AI Hub transcription for: {Path(audio_path).name}")
            
            transcription_start = time.time()
            transcription_text = self.app.transcribe(audio_path)
            transcription_time = time.time() - transcription_start
            
            logger.info(f"AI Hub transcription completed in {transcription_time:.2f}s")
            
            # Convert string result to expected dictionary format
            # Get audio duration for the result
            try:
                waveform, sample_rate = torchaudio.load(audio_path)
                duration = waveform.shape[1] / sample_rate
            except:
                duration = 0.0
            
            # Create a single segment for the entire transcription
            # Since AI Hub doesn't provide timestamps, we'll create one segment
            result = {
                "text": transcription_text,
                "segments": [{
                    "start": 0.0,
                    "end": duration,
                    "text": transcription_text
                }],
                "duration": duration,
                "language": "en"  # AI Hub model is English-only
            }
            
            return result, transcription_time
            
        except Exception as e:
            logger.error(f"AI Hub transcription failed for {audio_path}: {str(e)}")
            raise Exception(f"AI Hub transcription failed: {str(e)}")

class AudioTranscriber:
    """Main audio transcriber combining transcription and diarization services"""
    
    def __init__(self):
        """Initialize the transcriber with services"""
        # Initialize model manager with local model paths
        self.model_manager = ModelManager(
            whisper_cache_dir=str(WHISPER_MODELS_DIR),
            pyannote_cache_dir=str(PYANNOTE_MODELS_DIR),
            whisper_model_size=WHISPER_MODEL_SIZE,
            pyannote_model_name=DIARIZATION_MODEL,
            pyannote_auth_token=PYANNOTE_AUTH_TOKEN
        )
        
        # Initialize services with model manager
        self.transcription_service = TranscriptionService(self.model_manager)
        self.diarization_service = DiarizationService(self.model_manager)
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds"""
        try:
            waveform, sample_rate = torchaudio.load(str(audio_path))
            duration = waveform.shape[1] / sample_rate
            return duration
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}")
            return 0.0
    
    def transcribe_audio(self, audio_file_path: Path) -> Optional[str]:
        """
        Transcribe audio file to text with timestamps and speaker diarization.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Transcribed text with speaker labels and timestamps or None if failed
        """
        if not audio_file_path.exists():
            logger.error(f"Audio file not found: {audio_file_path}")
            return None
        
        try:
            logger.info(f"Starting transcription and diarization of {audio_file_path}")
            
            # Get audio duration for metrics
            audio_duration = self._get_audio_duration(audio_file_path)
            
            # Perform speaker diarization
            diarization, diarization_time = self.diarization_service.diarize(str(audio_file_path))
            
            # Transcribe audio
            if USE_AIHUB:
                transcription_result, whisper_time = self.transcription_service.transcribe_aihub(str(audio_file_path))
            else:
                transcription_result, whisper_time = self.transcription_service.transcribe(str(audio_file_path))
            
            # Calculate speaker metrics
            speakers_detected = 0
            total_speech_duration = 0.0
            
            if diarization is not None:
                speakers = set()
                speaker_durations = {}
                
                for segment, _, speaker in diarization.itertracks(yield_label=True):
                    speakers.add(speaker)
                    total_speech_duration += segment.duration
                    
                    if speaker not in speaker_durations:
                        speaker_durations[speaker] = 0
                    speaker_durations[speaker] += segment.duration
                
                # Count only speakers with meaningful duration (same logic as diarization service)
                min_speaker_duration = 2.0
                valid_speakers = {speaker for speaker, duration in speaker_durations.items() 
                                if duration >= min_speaker_duration}
                speakers_detected = len(valid_speakers)
                
                # If no valid speakers detected, use total speakers count
                if speakers_detected == 0:
                    speakers_detected = len(speakers)
                    
            else:
                # Estimate for rule-based assignment
                speakers_detected = 2
                total_speech_duration = audio_duration * 0.8  # Estimate 80% speech
            
            # Track transcription performance
            evaluator.track_transcription(
                audio_file=str(audio_file_path.name),
                audio_duration=audio_duration,
                whisper_time=whisper_time,
                diarization_time=diarization_time,
                speakers_detected=speakers_detected,
                total_speech_duration=total_speech_duration
            )
            
            # Determine best approach for speaker assignment
            use_rule_based = False
            
            # Check if diarization found multiple speakers
            if diarization is not None and len(diarization.labels()) > 1:
                # Use diarization if it found multiple speakers
                formatted_transcription = self._format_transcription_with_speakers(transcription_result, diarization)
                logger.info(f"Using diarization results: {len(diarization.labels())} speakers detected")
            else:
                # Check if rule-based might work better by analyzing conversation patterns
                if self._should_use_rule_based_assignment(transcription_result):
                    logger.info("Conversation patterns suggest multiple speakers - using enhanced rule-based assignment")
                    use_rule_based = True
                else:
                    # Single speaker conversation - use simple formatting
                    if diarization is not None:
                        formatted_transcription = self._format_transcription_with_speakers(transcription_result, diarization)
                        logger.info("Single speaker conversation detected")
                    else:
                        use_rule_based = True
                        logger.warning("No diarization available - using rule-based assignment")
                
                if use_rule_based:
                    formatted_transcription = self._format_with_rule_based_speakers(transcription_result)
                    # Update speaker count for metrics since rule-based found more speakers
                    estimated_speakers = self._estimate_speakers_from_rule_based(formatted_transcription)
                    if estimated_speakers > speakers_detected:
                        speakers_detected = estimated_speakers
                        logger.info(f"Rule-based assignment detected {estimated_speakers} speakers - updating metrics")
            
            logger.info("Transcription and diarization completed successfully")
            return formatted_transcription
            
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return None
    
    def _format_transcription_with_speakers(self, result: dict, diarization: Annotation) -> str:
        """
        Format transcription result with speaker labels and timestamps.
        
        Args:
            result: Whisper-timestamped transcription result
            diarization: pyannote diarization annotation
            
        Returns:
            Formatted transcription text with speaker labels
        """
        formatted_lines = []
        
        for segment in result.get('segments', []):
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text'].strip()
            
            # Find the dominant speaker for this segment
            speaker = self._get_dominant_speaker(diarization, start_time, end_time)
            
            timestamp_str = self._seconds_to_timestamp(start_time)
            formatted_lines.append(f"[{timestamp_str}] {speaker}: {text}")
        
        return '\n'.join(formatted_lines)
    
    def _format_with_rule_based_speakers(self, result: dict) -> str:
        """
        Fallback method to assign speakers based on conversation patterns.
        
        Args:
            result: Whisper-timestamped transcription result
            
        Returns:
            Formatted transcription with estimated speaker assignments
        """
        formatted_lines = []
        
        # Enhanced rule-based speaker assignment
        segments = result.get('segments', [])
        if not segments:
            return ""
        
        # Initialize speaker assignment
        speaker_assignments = self._analyze_conversation_flow(segments)
        
        for i, segment in enumerate(segments):
            start_time = segment['start']
            text = segment['text'].strip()
            
            speaker_num = speaker_assignments[i]
            timestamp_str = self._seconds_to_timestamp(start_time)
            formatted_lines.append(f"[{timestamp_str}] Speaker {speaker_num}: {text}")
        
        logger.info("Applied enhanced rule-based speaker assignment as fallback")
        return '\n'.join(formatted_lines)
    
    def _analyze_conversation_flow(self, segments: List[Dict]) -> List[int]:
        """
        Analyze conversation flow to assign speakers intelligently.
        
        Args:
            segments: List of transcription segments
            
        Returns:
            List of speaker numbers for each segment
        """
        if not segments:
            return []
        
        assignments = [1]  # Start with speaker 1
        current_speaker = 1
        
        for i in range(1, len(segments)):
            prev_segment = segments[i - 1]
            curr_segment = segments[i]
            
            # Calculate pause duration
            pause_duration = curr_segment['start'] - prev_segment['end']
            
            # Check for speaker change indicators
            should_change = False
            
            # 1. Significant pause (>1.5 seconds)
            if pause_duration > 1.5:
                should_change = True
            
            # 2. Question-answer pattern
            if (prev_segment['text'].strip().endswith('?') and 
                not curr_segment['text'].strip().endswith('?')):
                should_change = True
            
            if should_change:
                current_speaker = 2 if current_speaker == 1 else 1
            
            assignments.append(current_speaker)
        
        return assignments
    

    
    def _get_dominant_speaker(self, diarization: Annotation, start_time: float, end_time: float) -> str:
        """
        Get the dominant speaker for a given time segment.
        
        Args:
            diarization: pyannote diarization annotation
            start_time: Start time of the segment
            end_time: End time of the segment
            
        Returns:
            Speaker label (e.g., "Speaker 1")
        """
        segment_duration = end_time - start_time
        speaker_durations = {}
        
        # Find overlapping speaker segments
        for turn, track, speaker_label in diarization.itertracks(yield_label=True):
            overlap_start = max(start_time, turn.start)
            overlap_end = min(end_time, turn.end)
            
            if overlap_start < overlap_end:
                overlap_duration = overlap_end - overlap_start
                if speaker_label not in speaker_durations:
                    speaker_durations[speaker_label] = 0
                speaker_durations[speaker_label] += overlap_duration
        
        if speaker_durations:
            # Return the speaker with the most overlap
            dominant_speaker = max(speaker_durations, key=speaker_durations.get)
            # Convert SPEAKER_XX to Speaker X format
            if dominant_speaker.startswith('SPEAKER_'):
                speaker_num = dominant_speaker.split('_')[1]
                return f"Speaker {int(speaker_num) + 1}"
            else:
                return f"Speaker {dominant_speaker}"
        else:
            return "Unknown Speaker"
    
    def _format_transcription(self, result: dict) -> str:
        """
        Format transcription result with timestamps (without speaker labels).
        
        Args:
            result: Whisper-timestamped transcription result
            
        Returns:
            Formatted transcription text
        """
        formatted_lines = []
        
        for segment in result.get('segments', []):
            start_time = self._seconds_to_timestamp(segment['start'])
            text = segment['text'].strip()
            formatted_lines.append(f"[{start_time}] {text}")
        
        return '\n'.join(formatted_lines)
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """Convert seconds to MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _should_use_rule_based_assignment(self, transcription_result: dict) -> bool:
        """Determine if rule-based speaker assignment should be used"""
        segments = transcription_result.get('segments', [])
        if len(segments) < 3:  # Too few segments to analyze
            return False
        
        # Look for conversation indicators
        conversation_indicators = 0
        question_count = 0
        address_words = ['hey', 'hi', 'yeah', 'okay', 'alright', 'sure', 'thanks']
        
        for segment in segments:
            text = segment['text'].lower().strip()
            
            # Count questions
            if '?' in text:
                question_count += 1
            
            # Count conversational words
            if any(word in text for word in address_words):
                conversation_indicators += 1
        
        # If we have questions and conversational words, likely multiple speakers
        conversation_ratio = conversation_indicators / len(segments)
        question_ratio = question_count / len(segments)
        
        # Use rule-based if there are strong conversation patterns
        return conversation_ratio > 0.2 or question_ratio > 0.15
    
    def _estimate_speakers_from_rule_based(self, formatted_transcription: str) -> int:
        """Estimate number of speakers from rule-based transcription output"""
        lines = formatted_transcription.split('\n')
        speakers = set()
        
        for line in lines:
            # Extract speaker labels like "Speaker 1:", "Speaker 2:", etc.
            if 'Speaker' in line and ':' in line:
                # Find the speaker label
                parts = line.split(']', 1)
                if len(parts) > 1:
                    speaker_part = parts[1].strip()
                    if speaker_part.startswith('Speaker'):
                        speaker_label = speaker_part.split(':')[0].strip()
                        speakers.add(speaker_label)
        
        return len(speakers)
    
    def transcribe_and_save(self, audio_file_path: Path) -> bool:
        """
        Transcribe audio and save to transcription file.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            True if successful, False otherwise
        """
        transcription = self.transcribe_audio(audio_file_path)
        
        if transcription is None:
            return False
        
        # Use timestamped output directory
        transcription_file = get_output_file(TRANSCRIPTION_FILE)
        success = write_text_file(transcription_file, transcription)
        
        if success:
            logger.info(f"Transcription saved to {transcription_file}")
        
        return success
    
    def is_available(self) -> bool:
        """Check if transcription services are available"""
        return (self.transcription_service.is_available() and 
                self.diarization_service.is_available()) 