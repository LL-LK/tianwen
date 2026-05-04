"""
天问-AGI 推理引擎 v1.0
ModelConfig - 模型配置管理
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ModelConfig:
    """模型配置"""
    model: str
    endpoint: str
    api_key: str
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False

    @classmethod
    def openai(cls, api_key: str, model: str = "gpt-4", **kwargs):
        return cls(
            model=model,
            endpoint="https://api.openai.com/v1",
            api_key=api_key,
            **kwargs
        )

    @classmethod
    def ollama(cls, base_url: str = "http://localhost:11434", model: str = "llama2", **kwargs):
        return cls(
            model=model,
            endpoint=base_url,
            api_key="",
            **kwargs
        )

    @classmethod
    def minimax_api(cls, api_key: str, model: str = "abab5.5-chat", **kwargs):
        return cls(
            model=model,
            endpoint="https://api.minimax.chat/v1",
            api_key=api_key,
            **kwargs
        )


class ReasoningEngine:
    """推理引擎 - LLM调用封装"""

    def __init__(self, config: ModelConfig):
        self.config = config

    async def think(self, prompt: str) -> str:
        """执行推理"""
        return f"[Reasoning] {prompt}"

    async def batch_think(self, prompts: List[str]) -> List[str]:
        """批量推理"""
        return [await self.think(p) for p in prompts]
