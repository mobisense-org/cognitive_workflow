from imagine import ChatMessage, ImagineClient
from pathlib import Path
from typing import Optional
import time
from utils.logger import setup_logger
from utils.file_handler import read_text_file, write_text_file, get_output_file
from utils.evaluator import evaluator
from config.settings import API_KEY, ENDPOINT, SUMMARIZER_MODEL, MAX_TOKENS, TEMPERATURE, SUMMARY_FILE
from config.prompts import get_summarization_prompt

logger = setup_logger(__name__)

class ConversationSummarizer:
    """Handles text summarization using AI model."""
    
    def __init__(self):
        """Initialize the summarizer with API client."""
        self.client = ImagineClient(
            api_key=API_KEY,
            endpoint=ENDPOINT
        )
    
    def summarize_text(self, transcription_text: str) -> Optional[str]:
        """
        Summarize transcription text into a concise paragraph.
        
        Args:
            transcription_text: The transcribed text to summarize
            
        Returns:
            Summary text or None if failed
        """
        if not transcription_text.strip():
            logger.error("Empty transcription text provided")
            return None
        
        try:
            logger.info("Starting text summarization...")
            
            # Prepare the prompt
            prompt = get_summarization_prompt(transcription_text)
            
            # Create messages for the chat
            messages = [
                ChatMessage(role="system", content="You are an expert conversation analyst and summarizer."),
                ChatMessage(role="user", content=prompt)
            ]
            
            # Track LLM call performance
            start_time = time.time()
            
            # Get summary from the model
            summary_parts = []
            for chunk in self.client.chat_stream(
                messages=messages,
                model=SUMMARIZER_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            ):
                if chunk.first_content is not None:
                    summary_parts.append(chunk.first_content)
            
            response_time = time.time() - start_time
            summary = ''.join(summary_parts).strip()
            
            if summary:
                # Track the LLM performance
                evaluator.track_llm_call(
                    step_name="summarization",
                    model_name=SUMMARIZER_MODEL,
                    input_text=prompt,
                    output_text=summary,
                    response_time=response_time
                )
                
                logger.info("Text summarization completed successfully")
                return summary
            else:
                logger.error("Received empty summary from model")
                return None
                
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
            return None
    
    def summarize_from_file(self, transcription_file_path: Path) -> Optional[str]:
        """
        Read transcription from file and generate summary.
        
        Args:
            transcription_file_path: Path to the transcription file
            
        Returns:
            Summary text or None if failed
        """
        transcription_text = read_text_file(transcription_file_path)
        
        if not transcription_text:
            logger.error(f"Could not read transcription from {transcription_file_path}")
            return None
        
        return self.summarize_text(transcription_text)
    
    def summarize_and_save(self, transcription_file_path: Path) -> bool:
        """
        Generate summary and save to summary file.
        
        Args:
            transcription_file_path: Path to the transcription file
            
        Returns:
            True if successful, False otherwise
        """
        summary = self.summarize_from_file(transcription_file_path)
        
        if summary is None:
            return False
        
        # Use timestamped output directory
        summary_file = get_output_file(SUMMARY_FILE)
        success = write_text_file(summary_file, summary)
        
        if success:
            logger.info(f"Summary saved to {summary_file}")
        
        return success 