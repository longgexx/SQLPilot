from typing import List, Dict, Any, AsyncGenerator, Optional
from openai import AsyncOpenAI
from sqlpilot.core.config import LLMConfig
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = config.default_provider
        
        # Get provider config
        provider_config = getattr(config, self.provider, None)
        if not provider_config:
            raise ValueError(f"Configuration for LLM provider '{self.provider}' not found")
            
        self.client = AsyncOpenAI(
            api_key=provider_config.api_key,
            base_url=provider_config.base_url
        )
        self.model = provider_config.model
        logger.info(f"Initialized LLM Service with provider: {self.provider}, model: {self.model}")

    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ):
        """
        Send a chat completion request to the LLM.
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "stream": stream,
                "temperature": 0.1 # Low temperature for more deterministic output
            }
            if tools:
                kwargs["tools"] = [{"type": "function", "function": t} for t in tools]
                kwargs["tool_choice"] = "auto"

            return await self.client.chat.completions.create(**kwargs)
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise
