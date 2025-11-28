"""Unified LLM client interface for Groq (DeepSeek R1 Distilled)."""

import logging
import os
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

from groq import Groq
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class LLMConfig(BaseModel):
    """LLM configuration model."""
    
    provider: str = Field(default="groq", description="LLM provider name")
    model: str = Field(default="llama-3.1-8b-instant", description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="Temperature")
    max_tokens: int = Field(default=4096, ge=1, le=8192, description="Max tokens")
    timeout: int = Field(default=60, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Max retry attempts")


class LLMClient:
    """Unified LLM client for Groq API."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize LLM client.
        
        Args:
            config: LLM configuration. If None, loads from config/llm.json and .env
        """
        if config is None:
            config = self._load_config()
        
        self.config = config
        self.client = None
        
        # Initialize Groq client
        api_key = config.api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables or config")
        
        self.client = Groq(api_key=api_key)
        logger.info(f"LLMClient initialized: {config.provider}/{config.model}")
    
    @property
    def model(self) -> str:
        """Get current model name."""
        return self.config.model
    
    def _load_config(self) -> LLMConfig:
        """Load configuration from config/llm.json and environment."""
        import json
        
        config_path = Path("config/llm.json")
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return LLMConfig()
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Get API key from environment
        api_key = os.getenv("GROQ_API_KEY")
        
        return LLMConfig(
            provider=config_data.get("provider", "groq"),
            model=config_data.get("model", "llama-3.1-8b-instant"),
            api_key=api_key,
            temperature=config_data.get("settings", {}).get("temperature", 0.3),
            max_tokens=config_data.get("settings", {}).get("max_tokens", 4096),
            timeout=config_data.get("timeout", 60),
            max_retries=config_data.get("max_retries", 3)
        )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_case: Optional[str] = None
    ) -> str:
        """
        Generate text using the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            use_case: Use case name (e.g., "classification", "summary_generation")
                     to apply use-case-specific settings
        
        Returns:
            Generated text
        """
        # Apply use-case-specific settings
        if use_case:
            use_case_config = self._get_use_case_config(use_case)
            if use_case_config:
                temperature = temperature or use_case_config.get("temperature")
                max_tokens = max_tokens or use_case_config.get("max_tokens")
        
        # Use defaults from config if not provided
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Retry logic
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"LLM request (attempt {attempt + 1}/{self.config.max_retries + 1})")
                logger.debug(f"Model: {self.config.model}, Temperature: {temperature}, Max tokens: {max_tokens}")
                
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.config.timeout
                )
                
                result = response.choices[0].message.content
                logger.debug(f"LLM response received ({len(result)} chars)")
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"LLM request failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.config.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"LLM request failed after {self.config.max_retries + 1} attempts")
                    raise RuntimeError(f"LLM request failed: {last_error}") from last_error
        
        raise RuntimeError(f"LLM request failed: {last_error}") from last_error
    
    def _get_use_case_config(self, use_case: str) -> Optional[Dict[str, Any]]:
        """Get use-case-specific configuration."""
        import json
        
        config_path = Path("config/llm.json")
        if not config_path.exists():
            return None
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return config_data.get("use_cases", {}).get(use_case)
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_case: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON response from LLM.
        
        Args:
            prompt: User prompt (should instruct LLM to return JSON)
            system_prompt: Optional system prompt
            use_case: Use case name for settings
        
        Returns:
            Parsed JSON dictionary
        """
        import json
        
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            use_case=use_case
        )
        
        # Try to extract JSON from response (handle markdown code blocks)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        # Robust JSON parsing: handle control characters and find the last closing brace
        try:
            # Attempt direct parse
            return json.loads(response)
        except json.JSONDecodeError as e:
            import re
            
            # Try to fix unescaped control characters in JSON string values
            # Pattern to match JSON string values (handles escaped quotes and backslashes)
            pattern = r'("(?:[^"\\]|\\.)*")'
            
            def escape_control_chars(m):
                """Escape control characters in a JSON string value."""
                s = m.group(1)
                # Check if this is a string value (starts and ends with quotes)
                if s.startswith('"') and s.endswith('"'):
                    # Extract the content (without quotes)
                    content = s[1:-1]
                    # Escape control characters (but preserve already-escaped ones)
                    # Replace unescaped newlines, carriage returns, tabs
                    content = re.sub(r'(?<!\\)\n', r'\\n', content)
                    content = re.sub(r'(?<!\\)\r', r'\\r', content)
                    content = re.sub(r'(?<!\\)\t', r'\\t', content)
                    return f'"{content}"'
                return s
            
            try:
                fixed_response = re.sub(pattern, escape_control_chars, response)
                return json.loads(fixed_response)
            except (json.JSONDecodeError, Exception) as fix_error:
                # If fixing fails, try to find the last closing brace and slice
                last_brace_idx = response.rfind('}')
                if last_brace_idx != -1:
                    try:
                        # Try parsing up to the last brace
                        return json.loads(response[:last_brace_idx + 1])
                    except json.JSONDecodeError:
                        pass # Fall through to original error
                
                logger.error(f"Failed to parse JSON from LLM response: {e}")
                logger.error(f"Fix attempt also failed: {fix_error}")
                logger.error(f"Response: {response[:500]}")
                raise ValueError(f"Invalid JSON response from LLM: {e}") from e


# Global client instance (lazy initialization)
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client instance."""
    global _llm_client
    
    if _llm_client is None:
        _llm_client = LLMClient()
    
    return _llm_client

