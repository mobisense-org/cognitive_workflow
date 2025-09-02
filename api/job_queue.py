import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import threading
import time
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from modules.transcriber import AudioTranscriber
from modules.summarizer import ConversationSummarizer
from modules.judge import SituationJudge
from utils.logger import setup_logger

logger = setup_logger(__name__)

class JobStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    job_id: str
    status: JobStatus
    created_at: datetime
    audio_filename: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[str] = None

class JobQueue:
    """Simple in-memory job queue for audio processing workflow."""
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)  # Limit concurrent jobs
        self._lock = threading.Lock()
        
        # Initialize workflow components once
        self._transcriber = None
        self._summarizer = None
        self._judge = None
        self._components_initialized = False
        
    def _initialize_components(self):
        """Initialize workflow components if not already done."""
        if self._components_initialized:
            return
            
        try:
            logger.info("Initializing workflow components for job queue...")
            self._transcriber = AudioTranscriber()
            self._summarizer = ConversationSummarizer()
            self._judge = SituationJudge()
            self._components_initialized = True
            logger.info("Workflow components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize workflow components: {e}")
            raise
    
    def submit_job(self, audio_file_path: Path) -> str:
        """Submit a new job to the queue."""
        job_id = str(uuid.uuid4())
        
        with self._lock:
            job = Job(
                job_id=job_id,
                status=JobStatus.QUEUED,
                created_at=datetime.now(),
                audio_filename=audio_file_path.name,
                progress="Job submitted, waiting to start processing..."
            )
            self.jobs[job_id] = job
            
        logger.info(f"Job {job_id} submitted for audio file: {audio_file_path.name}")
        
        # Start processing in background
        self.executor.submit(self._process_job, job_id, audio_file_path)
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get the status of a job."""
        with self._lock:
            return self.jobs.get(job_id)
    
    def _process_job(self, job_id: str, audio_file_path: Path):
        """Process a job asynchronously."""
        try:
            # Update job status to processing
            with self._lock:
                if job_id in self.jobs:
                    self.jobs[job_id].status = JobStatus.PROCESSING
                    self.jobs[job_id].progress = "Initializing workflow components..."
                    
            logger.info(f"Starting job {job_id} processing")
            
            # Initialize components if needed
            self._initialize_components()
            
            # Update progress
            with self._lock:
                if job_id in self.jobs:
                    self.jobs[job_id].progress = "Transcribing audio..."
                    
            # Step 1: Transcription
            logger.info(f"Job {job_id}: Starting transcription")
            transcription_result = self._transcriber.transcribe_audio(audio_file_path)
            
            if transcription_result is None:
                raise Exception("Transcription failed")
                
            # Update progress
            with self._lock:
                if job_id in self.jobs:
                    self.jobs[job_id].progress = "Generating summary..."
                    
            # Step 2: Summarization
            logger.info(f"Job {job_id}: Starting summarization")
            summary_result = self._summarizer.summarize_text(transcription_result)
            
            if summary_result is None:
                raise Exception("Summarization failed")
                
            # Update progress
            with self._lock:
                if job_id in self.jobs:
                    self.jobs[job_id].progress = "Analyzing situation..."
                    
            # Step 3: Judgment
            logger.info(f"Job {job_id}: Starting judgment")
            judgment_result = self._judge.analyze_situation(summary_result)
            
            if judgment_result is None:
                raise Exception("Judgment analysis failed")
            
            # Prepare final result
            result = {
                "job_id": job_id,
                "audio_filename": audio_file_path.name,
                "transcription": transcription_result,
                "summary": summary_result,
                "judgment": judgment_result,
                "completed_at": datetime.now().isoformat(),
                "processing_time_seconds": (datetime.now() - self.jobs[job_id].created_at).total_seconds()
            }
            
            # Update job as completed
            with self._lock:
                if job_id in self.jobs:
                    self.jobs[job_id].status = JobStatus.COMPLETED
                    self.jobs[job_id].result = result
                    self.jobs[job_id].progress = "Processing completed successfully"
                    
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job {job_id} failed: {error_msg}")
            
            with self._lock:
                if job_id in self.jobs:
                    self.jobs[job_id].status = JobStatus.FAILED
                    self.jobs[job_id].error = error_msg
                    self.jobs[job_id].progress = f"Processing failed: {error_msg}"
                    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed/failed jobs."""
        cutoff_time = datetime.now().replace(hour=datetime.now().hour - max_age_hours)
        
        with self._lock:
            jobs_to_remove = []
            for job_id, job in self.jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED] and job.created_at < cutoff_time:
                    jobs_to_remove.append(job_id)
                    
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                logger.info(f"Cleaned up old job: {job_id}")

# Global job queue instance
job_queue = JobQueue()

# Periodic cleanup task
def start_cleanup_task():
    """Start background cleanup task."""
    def cleanup_worker():
        while True:
            time.sleep(3600)  # Run every hour
            job_queue.cleanup_old_jobs()
            
    thread = threading.Thread(target=cleanup_worker, daemon=True)
    thread.start()
