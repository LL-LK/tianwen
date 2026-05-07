"""
LLM服务模块 - 统一管理所有LLM调用
"""

from typing import Optional, Dict, Any, List
from enum import Enum
import json
import httpx

from ..utils.logger import get_logger
from ..utils.errors import LLMError
from ..config.settings import get_settings


class ModelProvider(Enum):
    MINIMAX = "minimax"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    OLLAMA = "ollama"


class LLMService:
    """LLM服务"""
    
    def __init__(self):
        self.logger = get_logger("llm-service")
        self.settings = get_settings()
        self.clients = {
            "minimax": httpx.AsyncClient(timeout=60),
            "deepseek": httpx.AsyncClient(timeout=60),
            "qwen": httpx.AsyncClient(timeout=60),
            "ollama": httpx.AsyncClient(timeout=60),
        }
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "minimax",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Optional[str]:
        try:
            if model == "minimax":
                return await self._call_minimax(messages, temperature, max_tokens)
            elif model == "deepseek":
                return await self._call_deepseek(messages, temperature, max_tokens)
            elif model == "qwen":
                return await self._call_qwen(messages, temperature, max_tokens)
            elif model == "ollama":
                return await self._call_ollama(messages, temperature, max_tokens)
            else:
                raise LLMError(f"Unknown model: {model}")
        
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise LLMError(f"LLM调用失败: {e}", retryable=True)
    
    async def _call_minimax(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        url = f"{self.settings.llm.minimax_endpoint}/chat/completions"
        
        payload = {
            "model": self.settings.llm.minimax_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.llm.minimax_api_key}",
        }
        
        if self.settings.llm.minimax_group_id:
            headers["Group-Id"] = self.settings.llm.minimax_group_id
        
        response = await self.clients["minimax"].post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    async def _call_deepseek(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        url = f"{self.settings.llm.deepseek_endpoint}/chat/completions"
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.llm.deepseek_api_key}"
        }
        
        response = await self.clients["deepseek"].post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    async def _call_qwen(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        url = f"{self.settings.llm.qwen_endpoint}/v1/chat/completions"
        
        payload = {
            "model": "qwen",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = await self.clients["qwen"].post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    async def _call_ollama(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        url = f"{self.settings.llm.ollama_endpoint}/api/chat"
        
        payload = {
            "model": self.settings.llm.ollama_model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_ctx": max_tokens
            },
            "stream": False
        }
        
        response = await self.clients["ollama"].post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data.get("message", {}).get("content", "")
    
    async def close(self):
        for client in self.clients.values():
            await client.aclose()