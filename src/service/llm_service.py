"""
LLM服务模块

统一管理所有LLM调用，提供一致的接口和错误处理。
支持多种模型提供商的切换。
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union, Callable
from enum import Enum
import json
import httpx
import asyncio
import logging
from functools import lru_cache


class ModelProvider(Enum):
    """模型提供商枚举"""
    MINIMAX = "minimax"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    OLLAMA = "ollama"


class ModelCapability(Enum):
    """模型能力枚举"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    VISION = "vision"
    FUNCTION_CALL = "function_call"


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = None
    finish_reason: str = "stop"
    raw_response: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage,
            "finish_reason": self.finish_reason
        }


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: ModelProvider
    model_name: str
    endpoint: str
    api_key: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    capabilities: List[ModelCapability] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = [ModelCapability.CHAT]


class BaseLLMAdapter:
    """LLM适配器基类"""
    
    provider: ModelProvider = None
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger(f"llm.{self.provider.value}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """发送对话补全请求"""
        raise NotImplementedError
    
    async def completion(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """发送补全请求"""
        raise NotImplementedError
    
    async def embedding(self, text: str, **kwargs) -> List[float]:
        """获取文本嵌入"""
        raise NotImplementedError
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Content-Type": "application/json"
        }
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """处理响应"""
        response.raise_for_status()
        return response.json()


class MiniMaxAdapter(BaseLLMAdapter):
    """MiniMax适配器"""
    
    provider = ModelProvider.MINIMAX
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": False,
            **kwargs
        }
        
        headers = self._build_headers()
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            data = self._handle_response(response)
            
            choice = data.get("choices", [{}])[0]
            return LLMResponse(
                content=choice.get("message", {}).get("content", ""),
                model=self.config.model_name,
                provider=self.provider.value,
                usage=data.get("usage", {}),
                finish_reason=choice.get("finish_reason", "stop"),
                raw_response=data
            )


class DeepSeekAdapter(BaseLLMAdapter):
    """DeepSeek适配器"""
    
    provider = ModelProvider.DEEPSEEK
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            **kwargs
        }
        
        headers = self._build_headers()
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            data = self._handle_response(response)
            
            choice = data.get("choices", [{}])[0]
            return LLMResponse(
                content=choice.get("message", {}).get("content", ""),
                model=self.config.model_name,
                provider=self.provider.value,
                usage=data.get("usage", {}),
                finish_reason=choice.get("finish_reason", "stop"),
                raw_response=data
            )


class OllamaAdapter(BaseLLMAdapter):
    """Ollama适配器"""
    
    provider = ModelProvider.OLLAMA
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        url = f"{self.config.endpoint}/api/chat"
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_ctx": max_tokens or self.config.max_tokens
            },
            "stream": False,
            **kwargs
        }
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload)
            data = self._handle_response(response)
            
            return LLMResponse(
                content=data.get("message", {}).get("content", ""),
                model=self.config.model_name,
                provider=self.provider.value,
                usage={"prompt_tokens": 0, "completion_tokens": 0},
                finish_reason="stop",
                raw_response=data
            )
    
    async def embedding(self, text: str, **kwargs) -> List[float]:
        url = f"{self.config.endpoint}/api/embeddings"
        
        payload = {
            "model": self.config.model_name,
            "prompt": text
        }
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload)
            data = self._handle_response(response)
            return data.get("embedding", [])


class LLMService:
    """LLM服务"""
    
    def __init__(self):
        self.logger = logging.getLogger("llm-service")
        self._adapters: Dict[ModelProvider, BaseLLMAdapter] = {}
        self._init_adapters()
    
    def _init_adapters(self):
        """初始化适配器"""
        from ..config.settings import get_settings
        settings = get_settings()
        
        if settings.llm.minimax_api_key or settings.llm.minimax_endpoint:
            self._adapters[ModelProvider.MINIMAX] = MiniMaxAdapter(
                LLMConfig(
                    provider=ModelProvider.MINIMAX,
                    model_name=settings.llm.minimax_model,
                    endpoint=settings.llm.minimax_endpoint,
                    api_key=settings.llm.minimax_api_key
                )
            )
        
        if settings.llm.deepseek_api_key or settings.llm.deepseek_endpoint:
            self._adapters[ModelProvider.DEEPSEEK] = DeepSeekAdapter(
                LLMConfig(
                    provider=ModelProvider.DEEPSEEK,
                    model_name="deepseek-chat",
                    endpoint=settings.llm.deepseek_endpoint,
                    api_key=settings.llm.deepseek_api_key
                )
            )
        
        if settings.llm.ollama_endpoint:
            self._adapters[ModelProvider.OLLAMA] = OllamaAdapter(
                LLMConfig(
                    provider=ModelProvider.OLLAMA,
                    model_name=settings.llm.ollama_model,
                    endpoint=settings.llm.ollama_endpoint
                )
            )
        
        self.logger.info(f"Initialized adapters: {[p.value for p in self._adapters.keys()]}")
    
    def get_adapter(self, provider: ModelProvider) -> Optional[BaseLLMAdapter]:
        """获取适配器"""
        return self._adapters.get(provider)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "minimax",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Optional[str]:
        """
        调用LLM进行对话补全
        
        Args:
            messages: 消息列表
            model: 模型名称 ("minimax", "deepseek", "ollama")
            temperature: 温度参数
            max_tokens: 最大token数
        
        Returns:
            响应文本
        """
        provider = self._resolve_provider(model)
        
        if not provider:
            self.logger.error(f"No adapter available for model: {model}")
            return None
        
        adapter = self._adapters.get(provider)
        if not adapter:
            self.logger.error(f"Adapter not found for provider: {provider}")
            return None
        
        try:
            response = await adapter.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            self.logger.info(f"LLM call succeeded: {response.provider}/{response.model}")
            return response.content
        
        except httpx.TimeoutException:
            self.logger.error(f"LLM call timeout: {provider.value}")
            raise
        except httpx.HTTPStatusError as e:
            self.logger.error(f"LLM call HTTP error: {e.response.status_code}")
            raise
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise
    
    async def generate(
        self,
        prompt: str,
        model: str = "minimax",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """生成文本"""
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat_completion(messages, model, temperature, max_tokens)
        return result or ""
    
    async def embedding(self, text: str, model: str = "ollama") -> List[float]:
        """获取文本嵌入"""
        provider = self._resolve_provider(model)
        
        if not provider:
            self.logger.error(f"No embedding adapter for: {model}")
            return []
        
        adapter = self._adapters.get(provider)
        if not adapter:
            self.logger.error(f"Adapter not found: {provider}")
            return []
        
        try:
            return await adapter.embedding(text)
        except Exception as e:
            self.logger.error(f"Embedding failed: {e}")
            return []
    
    def _resolve_provider(self, model: str) -> Optional[ModelProvider]:
        """解析模型对应的提供商"""
        provider_map = {
            "minimax": ModelProvider.MINIMAX,
            "deepseek": ModelProvider.DEEPSEEK,
            "qwen": ModelProvider.QWEN,
            "ollama": ModelProvider.OLLAMA,
        }
        return provider_map.get(model.lower())
    
    def list_providers(self) -> List[str]:
        """列出可用的提供商"""
        return [p.value for p in self._adapters.keys()]
    
    def is_provider_available(self, provider: ModelProvider) -> bool:
        """检查提供商是否可用"""
        return provider in self._adapters


from dataclasses import dataclass