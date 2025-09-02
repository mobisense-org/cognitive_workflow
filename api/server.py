import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.job_queue import job_queue, JobStatus
from config.settings import AUDIO_INPUT_DIR
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Audio Workflow API",
    description="API for processing audio files through transcription, summarization, and judgment workflow",
    version="1.0.0"
)

# Pydantic models for responses
class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    audio_filename: str
    created_at: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    audio_filename: str
    created_at: str
    progress: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Audio Workflow API",
        "version": "1.0.0",
        "endpoints": {
            "POST /flow": "Submit audio file for processing",
            "GET /job/{job_id}": "Check job status and get results"
        }
    }

@app.post("/flow", response_model=JobResponse)
async def process_audio_flow(file: UploadFile = File(...)):
    """
    Submit an audio file for processing through the complete workflow.
    
    The workflow includes:
    1. Audio transcription with speaker diarization
    2. Conversation summarization
    3. Situation analysis and judgment
    
    Returns a job ID immediately. Use GET /job/{job_id} to check status and get results.
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
            
        # Check file extension
        allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac'}
        file_path = Path(file.filename)
        if file_path.suffix.lower() not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save uploaded file to audio_input directory
        audio_input_path = AUDIO_INPUT_DIR / f"upload_{file.filename}"
        AUDIO_INPUT_DIR.mkdir(exist_ok=True)
        
        with open(audio_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"Audio file uploaded: {file.filename} -> {audio_input_path}")
        
        # Submit job to queue
        job_id = job_queue.submit_job(audio_input_path)
        
        return JobResponse(
            job_id=job_id,
            status="queued",
            message="Audio file submitted for processing",
            audio_filename=file.filename,
            created_at=job_queue.get_job_status(job_id).created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing audio upload: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a job and retrieve results when complete.
    
    Status values:
    - queued: Job is waiting to be processed
    - processing: Job is currently being processed
    - completed: Job finished successfully, results available
    - failed: Job failed, error details available
    """
    job = job_queue.get_job_status(job_id)
    
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    response = JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        audio_filename=job.audio_filename,
        created_at=job.created_at.isoformat(),
        progress=job.progress,
        result=job.result,
        error=job.error
    )
    
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "audio-workflow-api"}

if __name__ == "__main__":
    import uvicorn
    
    # Start cleanup task
    from api.job_queue import start_cleanup_task
    start_cleanup_task()
    
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
