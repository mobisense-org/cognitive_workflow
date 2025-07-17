import json
import time
from datetime import datetime
from imagine import ChatMessage, ImagineClient
from pathlib import Path
from typing import Optional, Dict, Any
from utils.logger import setup_logger
from utils.file_handler import read_text_file, write_json_file, get_output_file
from utils.evaluator import evaluator
from config.settings import API_KEY, ENDPOINT, JUDGE_MODEL, MAX_TOKENS, TEMPERATURE, JUDGMENT_FILE
from config.prompts import get_judgment_prompt

logger = setup_logger(__name__)

class SituationJudge:
    """Handles situation analysis and judgment using AI model."""
    
    def __init__(self):
        """Initialize the judge with API client."""
        self.client = ImagineClient(
            api_key=API_KEY,
            endpoint=ENDPOINT
        )
    
    def analyze_situation(self, summary_text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze conversation summary and determine next actions.
        
        Args:
            summary_text: The conversation summary to analyze
            
        Returns:
            Analysis result as dictionary or None if failed
        """
        if not summary_text.strip():
            logger.error("Empty summary text provided")
            return None
        
        try:
            logger.info("Starting situation analysis...")
            
            # Prepare the prompt
            prompt = get_judgment_prompt(summary_text)
            
            # Create messages for the chat
            messages = [
                ChatMessage(role="system", content="You are a senior incident analyst and decision support system. Always respond with valid JSON."),
                ChatMessage(role="user", content=prompt)
            ]
            
            # Track LLM call performance
            start_time = time.time()
            
            # Get analysis from the model
            response_parts = []
            for chunk in self.client.chat_stream(
                messages=messages,
                model=JUDGE_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            ):
                if chunk.first_content is not None:
                    response_parts.append(chunk.first_content)
            
            response_time = time.time() - start_time
            response_text = ''.join(response_parts).strip()
            
            if not response_text:
                logger.error("Received empty response from model")
                return None
            
            # Track the LLM performance (regardless of JSON parsing success)
            evaluator.track_llm_call(
                step_name="judgment",
                model_name=JUDGE_MODEL,
                input_text=prompt,
                output_text=response_text,
                response_time=response_time
            )
            
            # Parse JSON response
            try:
                analysis_result = json.loads(response_text)
                
                # Add timestamp to the result
                analysis_result["timestamp"] = datetime.now().isoformat()
                
                logger.info("Situation analysis completed successfully")
                return analysis_result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response_text}")
                
                # Try to extract JSON from response if it's wrapped in text
                return self._extract_json_from_text(response_text)
                
        except Exception as e:
            logger.error(f"Error during situation analysis: {e}")
            return None
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Try to extract JSON from text response.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Extracted JSON or None if failed
        """
        try:
            # Look for JSON-like content between braces
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start != -1 and end > start:
                json_text = text[start:end]
                result = json.loads(json_text)
                result["timestamp"] = datetime.now().isoformat()
                logger.info("Successfully extracted JSON from text response")
                return result
                
        except Exception as e:
            logger.error(f"Failed to extract JSON from text: {e}")
        
        return None
    
    def analyze_from_file(self, summary_file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Read summary from file and perform situation analysis.
        
        Args:
            summary_file_path: Path to the summary file
            
        Returns:
            Analysis result as dictionary or None if failed
        """
        summary_text = read_text_file(summary_file_path)
        
        if not summary_text:
            logger.error(f"Could not read summary from {summary_file_path}")
            return None
        
        return self.analyze_situation(summary_text)
    
    def analyze_and_save(self, summary_file_path: Path) -> bool:
        """
        Perform analysis and save to judgment file.
        
        Args:
            summary_file_path: Path to the summary file
            
        Returns:
            True if successful, False otherwise
        """
        analysis = self.analyze_from_file(summary_file_path)
        
        if analysis is None:
            return False
        
        # Use timestamped output directory
        judgment_file = get_output_file(JUDGMENT_FILE)
        success = write_json_file(judgment_file, analysis)
        
        if success:
            logger.info(f"Judgment saved to {judgment_file}")
        
        return success 