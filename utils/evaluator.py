import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from utils.logger import setup_logger
from utils.file_handler import get_output_file
from config.settings import PERFORMANCE_METRICS_FILE

logger = setup_logger(__name__)

@dataclass
class TranscriptionMetrics:
    """Metrics for transcription step"""
    audio_file: str
    audio_duration_seconds: float
    whisper_time_seconds: float
    diarization_time_seconds: float
    total_time_seconds: float
    speakers_detected: int
    total_speech_duration: float
    transcription_efficiency: float  # audio_duration / processing_time
    timestamp: str

@dataclass
class LLMMetrics:
    """Metrics for LLM calls"""
    step_name: str  # "summarization" or "judgment"
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    response_time_seconds: float
    tokens_per_second: float
    input_characters: int
    output_characters: int
    timestamp: str

@dataclass
class WorkflowMetrics:
    """Overall workflow metrics"""
    total_workflow_time: float
    transcription_metrics: TranscriptionMetrics
    llm_metrics: List[LLMMetrics]
    timestamp: str
    audio_file: str

class PerformanceEvaluator:
    """Tracks and evaluates performance metrics for the audio workflow"""
    
    def __init__(self, output_dir: Path = Path("outputs")):
        self.base_output_dir = output_dir
        self.base_output_dir.mkdir(exist_ok=True)
        
        self.global_metrics_file = get_output_file(PERFORMANCE_METRICS_FILE)
        
        # Current run specific metrics file (will be set when run starts)
        self.current_run_metrics_file = None
        
        # Track current workflow session
        self.current_workflow_start: Optional[float] = None
        self.current_audio_file: Optional[str] = None
        self.current_transcription_metrics: Optional[TranscriptionMetrics] = None
        self.current_llm_metrics: List[LLMMetrics] = []
    
    def set_run_directory(self, run_dir: Path):
        """Set the current run directory for metrics"""
        self.current_run_metrics_file = run_dir / "performance_metrics.json"
    
    def start_workflow_tracking(self, audio_file: str):
        """Start tracking a new workflow session"""
        self.current_workflow_start = time.time()
        self.current_audio_file = audio_file
        self.current_transcription_metrics = None
        self.current_llm_metrics = []
        logger.info(f"Started performance tracking for workflow: {audio_file}")
    
    def track_transcription(self, 
                          audio_file: str, 
                          audio_duration: float, 
                          whisper_time: float, 
                          diarization_time: float, 
                          speakers_detected: int, 
                          total_speech_duration: float) -> TranscriptionMetrics:
        """Track transcription and diarization performance"""
        
        total_time = whisper_time + diarization_time
        efficiency = audio_duration / total_time if total_time > 0 else 0
        
        metrics = TranscriptionMetrics(
            audio_file=audio_file,
            audio_duration_seconds=audio_duration,
            whisper_time_seconds=whisper_time,
            diarization_time_seconds=diarization_time,
            total_time_seconds=total_time,
            speakers_detected=speakers_detected,
            total_speech_duration=total_speech_duration,
            transcription_efficiency=efficiency,
            timestamp=datetime.now().isoformat()
        )
        
        self.current_transcription_metrics = metrics
        
        logger.info(f"Transcription metrics - Audio: {audio_duration:.2f}s, "
                   f"Whisper: {whisper_time:.2f}s, Diarization: {diarization_time:.2f}s, "
                   f"Efficiency: {efficiency:.2f}x, Speakers: {speakers_detected}")
        
        return metrics
    
    def track_llm_call(self, 
                      step_name: str, 
                      model_name: str, 
                      input_text: str, 
                      output_text: str, 
                      response_time: float) -> LLMMetrics:
        """Track LLM call performance"""
        
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        input_tokens = len(input_text) // 4
        output_tokens = len(output_text) // 4
        total_tokens = input_tokens + output_tokens
        
        tokens_per_second = output_tokens / response_time if response_time > 0 else 0
        
        metrics = LLMMetrics(
            step_name=step_name,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            response_time_seconds=response_time,
            tokens_per_second=tokens_per_second,
            input_characters=len(input_text),
            output_characters=len(output_text),
            timestamp=datetime.now().isoformat()
        )
        
        self.current_llm_metrics.append(metrics)
        
        logger.info(f"LLM metrics ({step_name}) - Model: {model_name}, "
                   f"Response time: {response_time:.2f}s, "
                   f"Output tokens: {output_tokens}, Tokens/s: {tokens_per_second:.1f}")
        
        return metrics
    
    def finalize_workflow_metrics(self) -> Optional[WorkflowMetrics]:
        """Finalize and save workflow metrics"""
        if not self.current_workflow_start or not self.current_transcription_metrics:
            logger.warning("Cannot finalize metrics - workflow not properly started or transcription missing")
            return None
        
        total_time = time.time() - self.current_workflow_start
        
        workflow_metrics = WorkflowMetrics(
            total_workflow_time=total_time,
            transcription_metrics=self.current_transcription_metrics,
            llm_metrics=self.current_llm_metrics,
            timestamp=datetime.now().isoformat(),
            audio_file=self.current_audio_file or "unknown"
        )
        
        self._save_metrics(workflow_metrics)
        self._log_summary(workflow_metrics)
        
        return workflow_metrics
    
    def _save_metrics(self, metrics: WorkflowMetrics):
        """Save metrics to both global and run-specific JSON files"""
        metrics_data = asdict(metrics)
        
        try:
            # Save to global metrics file
            all_metrics = []
            if self.global_metrics_file.exists():
                with open(self.global_metrics_file, 'r') as f:
                    all_metrics = json.load(f)
            
            all_metrics.append(metrics_data)
            
            with open(self.global_metrics_file, 'w') as f:
                json.dump(all_metrics, f, indent=2)
            
            logger.info(f"Performance metrics saved to {self.global_metrics_file}")
            
            # Also save to run-specific file if available
            if self.current_run_metrics_file:
                with open(self.current_run_metrics_file, 'w') as f:
                    json.dump(metrics_data, f, indent=2)
                logger.info(f"Run-specific metrics saved to {self.current_run_metrics_file}")
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def _log_summary(self, metrics: WorkflowMetrics):
        """Log a summary of the workflow performance"""
        logger.info("\n" + "="*60)
        logger.info("PERFORMANCE METRICS SUMMARY")
        logger.info("="*60)
        logger.info(f"Audio File: {metrics.audio_file}")
        logger.info(f"Total Workflow Time: {metrics.total_workflow_time:.2f}s")
        logger.info("")
        
        # Transcription metrics
        t = metrics.transcription_metrics
        logger.info(f"TRANSCRIPTION:")
        logger.info(f"  Audio Duration: {t.audio_duration_seconds:.2f}s")
        logger.info(f"  Whisper Time: {t.whisper_time_seconds:.2f}s")
        logger.info(f"  Diarization Time: {t.diarization_time_seconds:.2f}s")
        logger.info(f"  Total Processing: {t.total_time_seconds:.2f}s")
        logger.info(f"  Efficiency: {t.transcription_efficiency:.2f}x realtime")
        logger.info(f"  Speakers Detected: {t.speakers_detected}")
        logger.info("")
        
        # LLM metrics
        logger.info(f"LLM CALLS:")
        total_llm_time = sum(m.response_time_seconds for m in metrics.llm_metrics)
        total_output_tokens = sum(m.output_tokens for m in metrics.llm_metrics)
        avg_tokens_per_second = total_output_tokens / total_llm_time if total_llm_time > 0 else 0
        
        for llm in metrics.llm_metrics:
            logger.info(f"  {llm.step_name.upper()}:")
            logger.info(f"    Model: {llm.model_name}")
            logger.info(f"    Response Time: {llm.response_time_seconds:.2f}s")
            logger.info(f"    Output Tokens: {llm.output_tokens}")
            logger.info(f"    Tokens/s: {llm.tokens_per_second:.1f}")
        
        logger.info(f"  Total LLM Time: {total_llm_time:.2f}s")
        logger.info(f"  Average Tokens/s: {avg_tokens_per_second:.1f}")
        logger.info("="*60)
    
    def get_historical_metrics(self) -> List[WorkflowMetrics]:
        """Load and return historical metrics"""
        try:
            if self.global_metrics_file.exists():
                with open(self.global_metrics_file, 'r') as f:
                    data = json.load(f)
                
                metrics_list = []
                for item in data:
                    # Convert nested dictionaries back to dataclasses
                    transcription_data = item['transcription_metrics']
                    transcription_metrics = TranscriptionMetrics(**transcription_data)
                    
                    llm_metrics = []
                    for llm_data in item['llm_metrics']:
                        llm_metrics.append(LLMMetrics(**llm_data))
                    
                    workflow_metrics = WorkflowMetrics(
                        total_workflow_time=item['total_workflow_time'],
                        transcription_metrics=transcription_metrics,
                        llm_metrics=llm_metrics,
                        timestamp=item['timestamp'],
                        audio_file=item['audio_file']
                    )
                    metrics_list.append(workflow_metrics)
                
                return metrics_list
            return []
        except Exception as e:
            logger.error(f"Failed to load historical metrics: {e}")
            return []
    
    def generate_performance_report(self) -> str:
        """Generate a performance analysis report"""
        metrics_list = self.get_historical_metrics()
        
        if not metrics_list:
            return "No performance data available."
        
        report = ["PERFORMANCE ANALYSIS REPORT", "="*50, ""]
        
        # Overall statistics
        total_workflows = len(metrics_list)
        avg_workflow_time = sum(m.total_workflow_time for m in metrics_list) / total_workflows
        avg_transcription_efficiency = sum(m.transcription_metrics.transcription_efficiency for m in metrics_list) / total_workflows
        
        report.extend([
            f"Total Workflows Analyzed: {total_workflows}",
            f"Average Workflow Time: {avg_workflow_time:.2f}s",
            f"Average Transcription Efficiency: {avg_transcription_efficiency:.2f}x realtime",
            ""
        ])
        
        # LLM performance analysis
        all_llm_metrics = [llm for m in metrics_list for llm in m.llm_metrics]
        if all_llm_metrics:
            summarization_metrics = [llm for llm in all_llm_metrics if llm.step_name == "summarization"]
            judgment_metrics = [llm for llm in all_llm_metrics if llm.step_name == "judgment"]
            
            if summarization_metrics:
                avg_summ_time = sum(m.response_time_seconds for m in summarization_metrics) / len(summarization_metrics)
                avg_summ_tokens_per_sec = sum(m.tokens_per_second for m in summarization_metrics) / len(summarization_metrics)
                report.extend([
                    f"SUMMARIZATION PERFORMANCE:",
                    f"  Average Response Time: {avg_summ_time:.2f}s",
                    f"  Average Tokens/s: {avg_summ_tokens_per_sec:.1f}",
                    ""
                ])
            
            if judgment_metrics:
                avg_judge_time = sum(m.response_time_seconds for m in judgment_metrics) / len(judgment_metrics)
                avg_judge_tokens_per_sec = sum(m.tokens_per_second for m in judgment_metrics) / len(judgment_metrics)
                report.extend([
                    f"JUDGMENT PERFORMANCE:",
                    f"  Average Response Time: {avg_judge_time:.2f}s",
                    f"  Average Tokens/s: {avg_judge_tokens_per_sec:.1f}",
                    ""
                ])
        
        return "\n".join(report)

# Global evaluator instance
evaluator = PerformanceEvaluator() 