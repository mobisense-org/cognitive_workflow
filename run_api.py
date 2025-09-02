#!/usr/bin/env python3
"""
Audio Workflow API Server

Run the FastAPI server for audio processing workflow.

Usage:
    python run_api.py

The server will start on http://localhost:8000

Endpoints:
- POST /flow: Submit audio file for processing
- GET /job/{job_id}: Check job status and get results
- GET /health: Health check
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Main entry point for the API server."""
    try:
        from api.server import app
        import uvicorn
        
        print("Starting Audio Workflow API Server...")
        print("API will be available at: http://localhost:8000")
        print("Press Ctrl+C to stop the server")
        print()
        
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
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
