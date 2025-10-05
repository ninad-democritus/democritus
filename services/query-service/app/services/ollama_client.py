"""Ollama client for LLM inference"""
import logging
from typing import Optional
from langchain_community.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate

from ..config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama LLM"""
    
    def __init__(self):
        self.host = settings.OLLAMA_HOST
        self.nl_model = settings.OLLAMA_NL_MODEL
        self.chart_model = settings.OLLAMA_CHART_MODEL
        self.temperature = settings.OLLAMA_TEMPERATURE
        self.timeout = settings.OLLAMA_TIMEOUT
    
    def get_llm(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False
    ) -> ChatOllama:
        """
        Get Ollama LLM instance.
        
        Args:
            model: Model name (defaults to NL model)
            temperature: Temperature for generation (0-1)
            json_mode: Whether to request JSON output format
            
        Returns:
            ChatOllama instance
        """
        model_name = model or self.nl_model
        temp = temperature if temperature is not None else self.temperature
        
        kwargs = {
            "base_url": self.host,
            "model": model_name,
            "temperature": temp,
            "timeout": self.timeout,
        }
        
        # Only set JSON format if explicitly requested
        if json_mode:
            kwargs["format"] = "json"
        
        return ChatOllama(**kwargs)
    
    def test_connection(self) -> bool:
        """
        Test Ollama connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            llm = self.get_llm()
            response = llm.invoke("Say 'OK' if you can read this.")
            return True
        except Exception as e:
            logger.error(f"Ollama connection test failed: {e}")
            return False


# Global client instance
_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get global Ollama client instance"""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client


def get_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    json_mode: bool = False
) -> ChatOllama:
    """
    Convenience function to get LLM instance.
    
    Args:
        model: Model name
        temperature: Temperature for generation
        json_mode: Whether to request JSON output format
        
    Returns:
        ChatOllama instance
    """
    client = get_ollama_client()
    return client.get_llm(model=model, temperature=temperature, json_mode=json_mode)

