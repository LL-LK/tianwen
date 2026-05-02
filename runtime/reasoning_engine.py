"""
天问-AGI 推理引擎模块 v1.2
ReasoningEngine - 多模型推理能力集成

功能:
- Qwen3-32B thinking/non-thinking双模式
- DeepSeek-R1 API集成
- Ollama本地LLM支持 (Llama2, Mistral, Qwen等本地模型)
- 复杂度自动选择
- LRU内存缓存（减少重复API调用）
- 与literature_researcher.py无缝集成

模型选择策略:
- LOW复杂度: 优先Ollama (低延迟低成本)
- MEDIUM/HIGH: 优先Qwen > Ollama > DeepSeek
- EXTREME: DeepSeek > Qwen > Ollama

使用方法:
    engine = ReasoningEngine()
    await engine.configure(ollama_config=ModelConfig.ollama("llama2"))
    result = await engine.think("问题")

    # 强制使用Ollama
    result = await engine.think("问题", force_model="ollama")
"""

import asyncio
import json
import re
import hashlib
import time
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict

from runtime_logger import get_logger

logger = get_logger(__name__)


class LRUCache:
    """
    LRU (Least Recently Used) 内存缓存

    特性:
    - 基于输入hash的缓存键
    - LRU淘汰策略
    - 可配置缓存大小和TTL
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        初始化LRU缓存

        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 缓存有效期（秒），默认1小时
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def _make_key(self, prompt: str, complexity: str = "", force_model: str = "") -> str:
        """
        生成缓存键

        Args:
            prompt: 输入提示
            complexity: 复杂度等级
            force_model: 强制模型

        Returns:
            str: SHA256哈希键
        """
        key_data = f"{prompt}|{complexity}|{force_model}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, prompt: str, complexity: str = "", force_model: str = "") -> Optional[Any]:
        """
        获取缓存

        Args:
            prompt: 输入提示
            complexity: 复杂度等级
            force_model: 强制模型

        Returns:
            Optional[Any]: 缓存结果或None
        """
        key = self._make_key(prompt, complexity, force_model)

        if key not in self._cache:
            return None

        # 检查TTL
        cached_result, timestamp = self._cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self._cache[key]
            return None

        # 移动到末尾（最新使用）
        self._cache.move_to_end(key)
        return cached_result

    def put(self, prompt: str, result: Any, complexity: str = "", force_model: str = ""):
        """
        存入缓存

        Args:
            prompt: 输入提示
            result: 推理结果
            complexity: 复杂度等级
            force_model: 强制模型
        """
        key = self._make_key(prompt, complexity, force_model)

        # 如果已存在，更新并移动到末尾
        if key in self._cache:
            self._cache.move_to_end(key)

        self._cache[key] = (result, time.time())

        # LRU淘汰：超过最大容量时移除最旧的
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def clear(self):
        """清空缓存"""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "enabled": True,
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "current_size": len(self._cache),
            "hit_rate": getattr(self, '_hit_rate', 0.0)
        }


class Complexity(Enum):
    """问题复杂度等级"""
    LOW = "low"          # 简单问答
    MEDIUM = "medium"    # 一般推理
    HIGH = "high"        # 复杂推理
    EXTREME = "extreme"  # 极复杂问题


class ReasoningMode(Enum):
    """
    推理模式枚举

    CoD (Chain of Draft) vs CoT (Chain of Thought):
    - CoT: 200+ tokens/step，完整推理过程，精度高但消耗大
    - CoD: <50 tokens/step，简短草稿标记，精度适中但速度快4倍

    选择原则:
    - LOW复杂度问题 -> 使用CoD
    - MEDIUM复杂度问题 -> 可选CoD或CoT
    - HIGH/EXTREME复杂度问题 -> 使用CoT
    """
    COT = "cot"   # Chain of Thought - 完整思维链
    COD = "cod"   # Chain of Draft - 简短草稿模式


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    endpoint: str
    api_key: Optional[str] = None
    model_type: str = "openai_compatible"  # openai_compatible, anthropic, custom

    @classmethod
    def qwen_local(cls, endpoint: str = "http://localhost:8000"):
        """Qwen本地部署配置"""
        return cls(name="qwen", endpoint=endpoint, model_type="openai_compatible")

    @classmethod
    def deepseek_api(cls, api_key: str):
        """DeepSeek API配置"""
        return cls(name="deepseek", endpoint="https://api.deepseek.com", api_key=api_key)

    @classmethod
    def ollama(cls, model: str = "llama2", endpoint: str = "http://localhost:11434"):
        """Ollama本地部署配置"""
        return cls(name=model, endpoint=endpoint, model_type="ollama")

    @classmethod
    def longcat_api(cls, api_key: str, model: str = "LongCat-Flash-Thinking"):
        """LongCat API配置 - OpenAI兼容格式"""
        return cls(
            name=model,
            endpoint="https://api.longcat.chat/openai/v1",
            api_key=api_key,
            model_type="openai_compatible"
        )

    @classmethod
    def minimax_api(cls, api_key: str, model: str = "MiniMax-Text-01"):
        """MiniMax API配置 - OpenAI兼容格式"""
        return cls(
            name=model,
            endpoint="https://api.minimax.chat/v1",
            api_key=api_key,
            model_type="openai_compatible"
        )


@dataclass
class ReasoningResult:
    """推理结果"""
    content: str
    thinking_process: str = ""      # 思维链过程
    model_used: str = ""
    complexity: str = ""
    tokens_used: int = 0
    latency_ms: float = 0


@dataclass
class PaperAnalysis:
    """论文分析结果"""
    paper_id: str
    research_gaps: List[Dict] = field(default_factory=list)
    innovation_score: float = 0.0
    summary: str = ""
    key_contributions: List[str] = field(default_factory=list)
    methodology_quality: str = ""


class BaseAdapter:
    """模型适配器基类"""

    def __init__(self, config: ModelConfig):
        self.config = config

    async def think(self, prompt: str, **kwargs) -> ReasoningResult:
        """执行推理"""
        raise NotImplementedError

    async def analyze(self, content: str, **kwargs) -> Dict:
        """分析内容"""
        raise NotImplementedError


class QwenAdapter(BaseAdapter):
    """
    Qwen3适配器 - 支持thinking/non-thinking双模式

    Qwen3支持两种模式:
    - thinking模式: 启用思维链，逐步推理
    - non-thinking模式: 快速响应
    """

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=120.0)

    async def think(
        self,
        prompt: str,
        thinking: bool = True,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> ReasoningResult:
        """
        执行推理

        Args:
            prompt: 输入提示
            thinking: 是否启用思维链模式
            max_tokens: 最大生成长度
            temperature: 温度参数
        """
        import time
        start_time = time.time()

        # 构建消息
        messages = [{"role": "user", "content": prompt}]

        # 添加thinking模式提示
        if thinking:
            thinking_instruction = """
请使用思维链(Chain-of-Thought)来逐步分析这个问题。
先展示你的推理过程（用<thinking>标签包裹），然后给出最终答案。
"""
            messages[0]["content"] = thinking_instruction + prompt

        # 构建请求
        payload = {
            "model": "qwen",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # 添加thinking参数（vLLM格式）
        if thinking:
            payload["extra_body"] = {"thinking_enabled": True}

        try:
            response = await self.client.post(
                f"{self.config.endpoint}/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.config.api_key or 'dummy'}"}
            )
            response.raise_for_status()
            result = response.json()

            content = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {}).get("total_tokens", 0)

            # 提取思维过程
            thinking_process = ""
            if thinking and "<thinking>" in content:
                match = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
                if match:
                    thinking_process = match.group(1).strip()
                    content = content.replace(f"<thinking>{thinking_process}</thinking>", "").strip()

            return ReasoningResult(
                content=content,
                thinking_process=thinking_process,
                model_used=f"Qwen3 (thinking={thinking})",
                complexity="high" if thinking else "low",
                tokens_used=tokens,
                latency_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return ReasoningResult(
                content=f"Qwen推理出错: {str(e)}",
                model_used="Qwen3",
                complexity="high" if thinking else "low"
            )

    async def analyze(self, text: str, analysis_type: str = "general") -> Dict:
        """分析文本"""
        prompt = f"""请分析以下内容，提取关键信息:

{text[:4000]}

分析要求:
1. 识别主要研究问题
2. 提取研究空白(gaps)
3. 评估创新性
4. 总结关键贡献

请以JSON格式返回分析结果。"""

        result = await self.think(prompt, thinking=True)

        try:
            # 尝试解析JSON
            json_match = re.search(r'\{.*\}', result.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {
            "raw_analysis": result.content,
            "thinking_process": result.thinking_process
        }


class OllamaAdapter(BaseAdapter):
    """
    Ollama本地LLM适配器 - 支持多种本地模型

    Ollama优势:
    - 完全本地运行，无需网络
    - 支持多种开源模型 (Llama2, Mistral, Qwen, etc.)
    - API兼容OpenAI格式
    - 隐私友好
    """

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=120.0)

    async def think(
        self,
        prompt: str,
        system_prompt: str = "你是一个专业的AI助手，擅长深度推理分析。",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        thinking: bool = False
    ) -> ReasoningResult:
        """
        执行Ollama推理

        Args:
            prompt: 用户输入
            system_prompt: 系统提示
            max_tokens: 最大生成长度
            temperature: 温度参数
            thinking: 是否启用思维链模式 (部分模型支持)
        """
        import time
        start_time = time.time()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": self.config.name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }

        # 部分模型支持thinking参数
        if thinking:
            payload["options"] = {"thinking": True}

        try:
            response = await self.client.post(
                f"{self.config.endpoint}/api/chat",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            content = result.get("message", {}).get("content", "")
            tokens = result.get("eval_count", 0)

            # 提取思维过程 (如果模型返回)
            thinking_process = ""
            if "<thinking>" in content:
                match = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
                if match:
                    thinking_process = match.group(1).strip()
                    content = content.replace(f"<thinking>{thinking_process}</thinking>", "").strip()

            return ReasoningResult(
                content=content,
                thinking_process=thinking_process,
                model_used=f"Ollama-{self.config.name}",
                complexity="high" if thinking else "medium",
                tokens_used=tokens,
                latency_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return ReasoningResult(
                content=f"Ollama推理出错: {str(e)}",
                model_used=f"Ollama-{self.config.name}",
                complexity="medium"
            )

    async def analyze(self, content: str, analysis_type: str = "general") -> Dict:
        """分析文本"""
        prompt = f"""请分析以下内容，提取关键信息:

{content[:4000]}

分析要求:
1. 识别主要研究问题
2. 提取研究空白(gaps)
3. 评估创新性
4. 总结关键贡献

请以JSON格式返回分析结果。"""

        result = await self.think(prompt, thinking=True)

        try:
            json_match = re.search(r'\{.*\}', result.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {
            "raw_analysis": result.content,
            "thinking_process": result.thinking_process
        }

    @staticmethod
    def list_models(endpoint: str = "http://localhost:11434") -> List[Dict]:
        """列出Ollama可用的模型"""
        import httpx
        try:
            client = httpx.Client(timeout=10.0)
            response = client.get(f"{endpoint}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            return []


class ChainOfDraftAdapter:
    """
    Chain of Draft (CoD) 适配器

    CoD协议:
    - 每个推理步骤 <50 tokens (相比CoT的200+ tokens/step)
    - 使用简短草稿标记: [D1] 步骤1, [D2] 步骤2, ...
    - 快速推理，适用于简单问题和批量处理

    优势:
    - token消耗降低60-80%
    - 延迟降低50%以上
    - 适用于低复杂度问题

    使用场景:
    - 简单问答
    - 批量推理任务
    - 资源受限环境
    """

    # CoD提示模板 - 简短推理
    COD_TEMPLATE = """使用简短草稿模式推理:

问题: {prompt}

要求:
- 每个推理步骤 <50 tokens
- 使用草稿标记: [D1] 步骤1, [D2] 步骤2, ...
- 最终答案用 [ANSWER] 标记
- 保持简洁，直接
"""

    @staticmethod
    def format_cod_prompt(prompt: str) -> str:
        """格式化CoD提示"""
        return ChainOfDraftAdapter.COD_TEMPLATE.format(prompt=prompt)

    @staticmethod
    def parse_cod_response(response: str) -> Tuple[str, str]:
        """
        解析CoD响应

        Returns:
            (draft_steps, final_answer)
        """
        draft_steps = ""
        final_answer = response

        # 提取草稿步骤
        draft_parts = []
        for match in re.finditer(r'\[D(\d+)\]\s*(.+?)(?=\[D\d+\]|\[ANSWER\]|$)', response, re.DOTALL):
            draft_parts.append(f"[D{match.group(1)}] {match.group(2).strip()}")

        if draft_parts:
            draft_steps = "\n".join(draft_parts)

        # 提取最终答案
        answer_match = re.search(r'\[ANSWER\]\s*(.+?)$', response, re.DOTALL)
        if answer_match:
            final_answer = answer_match.group(1).strip()

        return draft_steps, final_answer


class DeepSeekAdapter(BaseAdapter):
    """
    DeepSeek-R1适配器

    DeepSeek-R1是最强的开源推理模型，采用强化学习训练，
    思维链质量接近OpenAI o1。
    """

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=180.0)

    async def think(
        self,
        prompt: str,
        system_prompt: str = "你是一个专业的AI助手，擅长深度推理分析。",
        max_tokens: int = 8192,
        temperature: float = 0.6
    ) -> ReasoningResult:
        """
        执行DeepSeek-R1推理

        Args:
            prompt: 用户输入
            system_prompt: 系统提示
            max_tokens: 最大生成长度
            temperature: 温度参数
        """
        import time
        start_time = time.time()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": "deepseek-reasoner",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }

        try:
            response = await self.client.post(
                f"{self.config.endpoint}/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            result = response.json()

            content = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {}).get("total_tokens", 0)

            # DeepSeek-R1自动输出思维链，用</think>分割
            thinking_process = ""
            if "</think>" in content:
                parts = content.split("</think>", 1)
                if len(parts) == 2:
                    thinking_process = parts[0].replace("<think>", "").strip()
                    content = parts[1].strip()

            return ReasoningResult(
                content=content,
                thinking_process=thinking_process,
                model_used="DeepSeek-R1",
                complexity="extreme",
                tokens_used=tokens,
                latency_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return ReasoningResult(
                content=f"DeepSeek推理出错: {str(e)}",
                model_used="DeepSeek-R1",
                complexity="extreme"
            )

    async def analyze_paper(self, paper_text: str) -> PaperAnalysis:
        """分析论文"""
        prompt = f"""请深入分析以下学术论文:

{paper_text[:6000]}

请进行以下分析并返回JSON格式结果:
{{
    "research_gaps": [
        {{
            "id": "gap-1",
            "category": "methodology|dataset|evaluation|theory|application",
            "description": "研究空白描述",
            "evidence": ["支撑证据"],
            "opportunity": "研究机会",
            "priority": "high|medium|low"
        }}
    ],
    "innovation_score": 0.0-1.0,
    "summary": "论文摘要",
    "key_contributions": ["贡献1", "贡献2"],
    "methodology_quality": "excellent|good|fair|poor"
}}

请只返回JSON，不要有其他内容。"""

        result = await self.think(prompt)

        try:
            json_match = re.search(r'\{.*\}', result.content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return PaperAnalysis(
                    paper_id="",
                    research_gaps=data.get("research_gaps", []),
                    innovation_score=data.get("innovation_score", 0.0),
                    summary=data.get("summary", ""),
                    key_contributions=data.get("key_contributions", []),
                    methodology_quality=data.get("methodology_quality", "")
                )
        except:
            pass

        return PaperAnalysis(
            paper_id="",
            summary=result.content[:500],
            innovation_score=0.5
        )


class ReasoningEngine:
    """
    推理引擎 - 统一入口

    根据问题复杂度自动选择合适的模型:
    - LOW: Qwen fast模式 (快速响应)
    - MEDIUM: Qwen thinking模式 (逐步推理)
    - HIGH: Qwen thinking模式 (深度推理)
    - EXTREME: DeepSeek-R1 (最强推理)

    支持LRU内存缓存，减少重复API调用
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        cache_max_size: int = 100,
        cache_ttl_seconds: int = 3600
    ):
        """
        初始化推理引擎

        Args:
            cache_enabled: 是否启用缓存，默认True
            cache_max_size: 缓存最大条目数，默认100
            cache_ttl_seconds: 缓存有效期（秒），默认3600
        """
        self.qwen: Optional[QwenAdapter] = None
        self.deepseek: Optional[DeepSeekAdapter] = None
        self.ollama: Optional[OllamaAdapter] = None
        self._config: Dict[str, ModelConfig] = {}

        # 缓存配置
        self.cache_enabled = cache_enabled
        self._cache = LRUCache(max_size=cache_max_size, ttl_seconds=cache_ttl_seconds) if cache_enabled else None

    async def configure(
        self,
        qwen_config: Optional[ModelConfig] = None,
        deepseek_config: Optional[ModelConfig] = None,
        ollama_config: Optional[ModelConfig] = None
    ):
        """
        配置推理引擎

        Args:
            qwen_config: Qwen配置 (默认为本地Ollama)
            deepseek_config: DeepSeek配置 (需要API Key)
            ollama_config: Ollama配置 (本地模型)
        """
        if qwen_config:
            self.qwen = QwenAdapter(qwen_config)
            self._config["qwen"] = qwen_config

        if deepseek_config:
            self.deepseek = DeepSeekAdapter(deepseek_config)
            self._config["deepseek"] = deepseek_config

        if ollama_config:
            self.ollama = OllamaAdapter(ollama_config)
            self._config["ollama"] = ollama_config

    def _estimate_complexity(self, prompt: str) -> Complexity:
        """根据提示词估计复杂度"""
        prompt_lower = prompt.lower()

        # 极复杂指示
        extreme_indicators = [
            "证明", "证明过程", "数学证明", "严格推导",
            "复杂系统", "多变量", "非凸优化",
            "颠覆性", "突破性", "革命性"
        ]

        # 复杂指示
        high_indicators = [
            "分析", "深入分析", "详细分析",
            "比较", "对比", "评估",
            "推理", "逻辑", "推导",
            "研究现状", "文献综述", "gap",
            "假说", "假设", "验证"
        ]

        for indicator in extreme_indicators:
            if indicator in prompt_lower:
                return Complexity.EXTREME

        for indicator in high_indicators:
            if indicator in prompt_lower:
                return Complexity.HIGH

        # 检查长度
        if len(prompt) > 1000:
            return Complexity.MEDIUM

        return Complexity.LOW

    async def think(
        self,
        prompt: str,
        complexity: Optional[str] = None,
        force_model: Optional[str] = None,
        use_cache: Optional[bool] = None,
        reasoning_mode: Optional[str] = None
    ) -> ReasoningResult:
        """
        执行推理 - 主入口

        Args:
            prompt: 输入提示
            complexity: 强制复杂度 (low/medium/high/extreme)
            force_model: 强制使用模型 (qwen/deepseek/ollama)
            use_cache: 是否使用缓存，默认使用缓存(True)，传入False可禁用
            reasoning_mode: 推理模式 ("cot" | "cod" | None=auto)
                - cot: Chain of Thought，完整思维链，200+ tokens/step
                - cod: Chain of Draft，简短草稿，<50 tokens/step

        Returns:
            ReasoningResult: 推理结果

        CoD vs CoT 选择原则:
            - LOW复杂度: 自动使用CoD
            - MEDIUM: 默认CoT，可选CoD
            - HIGH/EXTREME: 使用CoT
        """
        # 确定复杂度
        if complexity:
            comp = Complexity(complexity.lower())
        else:
            comp = self._estimate_complexity(prompt)

        # 确定推理模式
        if reasoning_mode:
            mode = ReasoningMode(reasoning_mode.lower())
        elif comp == Complexity.LOW:
            # 低复杂度自动使用CoD
            mode = ReasoningMode.COD
        else:
            # 中高复杂度使用CoT
            mode = ReasoningMode.COT

        # 缓存查找（当use_cache不为False且缓存启用时）
        effective_use_cache = use_cache if use_cache is not None else self.cache_enabled
        if effective_use_cache and self._cache:
            cached_result = self._cache.get(prompt, comp.value, force_model or "")
            if cached_result:
                return cached_result

        # 处理CoD模式
        if mode == ReasoningMode.COD:
            result = await self._think_cod(prompt, force_model)
        else:
            # 强制模型
            if force_model:
                if force_model == "deepseek" and self.deepseek:
                    result = await self.deepseek.think(prompt)
                elif force_model == "qwen" and self.qwen:
                    result = await self.qwen.think(prompt, thinking=True)
                elif force_model == "ollama" and self.ollama:
                    result = await self.ollama.think(prompt)
                else:
                    result = ReasoningResult(content="错误: 未配置指定模型")
            else:
                # 根据复杂度选择
                if comp == Complexity.EXTREME:
                    if self.deepseek:
                        result = await self.deepseek.think(prompt)
                    elif self.qwen:
                        result = await self.qwen.think(prompt, thinking=True)
                    elif self.ollama:
                        result = await self.ollama.think(prompt, thinking=True)
                    else:
                        result = ReasoningResult(content="错误: 未配置任何模型")

                elif comp in (Complexity.HIGH, Complexity.MEDIUM):
                    if self.qwen:
                        result = await self.qwen.think(prompt, thinking=True)
                    elif self.ollama:
                        result = await self.ollama.think(prompt, thinking=True)
                    elif self.deepseek:
                        result = await self.deepseek.think(prompt)
                    else:
                        result = ReasoningResult(content="错误: 未配置任何模型")

                else:  # LOW
                    # 优先使用本地Ollama (低延迟低成本)
                    if self.ollama:
                        result = await self.ollama.think(prompt, thinking=False)
                    elif self.qwen:
                        result = await self.qwen.think(prompt, thinking=False)
                    else:
                        result = ReasoningResult(content="错误: 未配置任何模型")

        # 缓存结果（当use_cache不为False且缓存启用时）
        if effective_use_cache and self._cache and result:
            self._cache.put(prompt, result, comp.value, force_model or "")

        return result

    async def _think_cod(
        self,
        prompt: str,
        force_model: Optional[str] = None
    ) -> ReasoningResult:
        """
        Chain of Draft 推理模式

        使用简短草稿标记进行快速推理，token消耗降低60-80%

        Args:
            prompt: 输入提示
            force_model: 强制模型

        Returns:
            ReasoningResult: 推理结果
        """
        import time
        start_time = time.time()

        # 格式化CoD提示
        cod_prompt = ChainOfDraftAdapter.format_cod_prompt(prompt)

        # 选择模型 (优先Ollama)
        if force_model == "ollama" and self.ollama:
            adapter = self.ollama
        elif force_model == "qwen" and self.qwen:
            adapter = self.qwen
        elif self.ollama:
            adapter = self.ollama
        elif self.qwen:
            adapter = self.qwen
        else:
            return ReasoningResult(
                content="错误: CoD模式需要配置Ollama或Qwen",
                model_used="CoD",
                complexity="low"
            )

        # 执行推理 (不启用thinking模式，因为CoD本身包含推理标记)
        result = await adapter.think(cod_prompt, thinking=False, max_tokens=512)

        # 解析CoD响应
        draft_steps, final_answer = ChainOfDraftAdapter.parse_cod_response(result.content)

        return ReasoningResult(
            content=final_answer,
            thinking_process=draft_steps,
            model_used=f"{result.model_used} (CoD)",
            complexity="low",
            tokens_used=result.tokens_used,
            latency_ms=(time.time() - start_time) * 1000
        )

    async def analyze_paper(
        self,
        paper_text: str,
        use_deepseek: bool = True
    ) -> PaperAnalysis:
        """
        分析论文

        Args:
            paper_text: 论文文本
            use_deepseek: 是否使用DeepSeek (更准确)

        Returns:
            PaperAnalysis: 论文分析结果
        """
        if use_deepseek and self.deepseek:
            return await self.deepseek.analyze_paper(paper_text)
        elif self.qwen:
            result = await self.qwen.analyze(paper_text)
            return PaperAnalysis(
                paper_id="",
                summary=str(result)
            )
        else:
            return PaperAnalysis(paper_id="", summary="错误: 未配置任何模型")

    async def generate_hypothesis(
        self,
        research_gaps: List[Any],
        topic: str = ""
    ) -> List[Dict]:
        """
        从研究空白生成假说

        Args:
            research_gaps: ResearchGap对象列表 (来自literature_researcher.py)
            topic: 研究主题

        Returns:
            List[Dict]: 结构化假说列表
        """
        if not research_gaps:
            return []

        # 构建提示
        gaps_text = []
        for i, gap in enumerate(research_gaps, 1):
            gaps_text.append(f"""
Gap {i}:
- 类别: {gap.category if hasattr(gap, 'category') else 'unknown'}
- 描述: {gap.description if hasattr(gap, 'description') else str(gap)}
- 证据: {', '.join(gap.evidence) if hasattr(gap, 'evidence') else ''}
- 机会: {gap.opportunity if hasattr(gap, 'opportunity') else ''}
""")

        prompt = f"""基于以下研究空白，生成可验证的假说:

{''.join(gaps_text)}

主题: {topic}

请为每个高优先级Gap生成一个结构化假说，格式如下:
{{
    "hypotheses": [
        {{
            "id": "hypo-1",
            "statement": "如果...那么...",
            "premises": ["前提1", "前提2"],
            "predictions": ["预测1", "预测2"],
            "verification_method": "验证方法",
            "confidence": 0.0-1.0,
            "related_gap": "gap-1"
        }}
    ]
}}

请只返回JSON格式。"""

        result = await self.think(prompt, complexity="high")

        try:
            json_match = re.search(r'\{.*\}', result.content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("hypotheses", [])
        except:
            pass

        return []

    def get_status(self) -> Dict:
        """获取引擎状态"""
        status = {
            "qwen_configured": self.qwen is not None,
            "deepseek_configured": self.deepseek is not None,
            "ollama_configured": self.ollama is not None,
            "available_models": list(self._config.keys()),
            "cache_enabled": self.cache_enabled
        }
        if self._cache:
            status["cache"] = self._cache.get_stats()
        return status

    def clear_cache(self):
        """清空推理缓存"""
        if self._cache:
            self._cache.clear()


# ============ 便捷函数 ============

async def quick_think(prompt: str, model: str = "auto") -> str:
    """
    快速推理 - 便捷入口

    Args:
        prompt: 输入提示
        model: 模型选择 (auto/qwen/deepseek)

    Returns:
        str: 推理结果
    """
    engine = ReasoningEngine()

    # 尝试自动配置
    try:
        await engine.configure(
            qwen_config=ModelConfig.qwen_local(),
            deepseek_config=None  # 需要用户自己配置API Key
        )
    except:
        pass

    if model == "qwen":
        result = await engine.think(prompt, force_model="qwen")
    elif model == "deepseek":
        result = await engine.think(prompt, force_model="deepseek")
    else:
        result = await engine.think(prompt)

    return result.content


async def analyze_research_state(state: Any) -> Dict:
    """
    分析研究状态 - 与literature_researcher.py集成

    Args:
        state: LiteratureResearcher.research() 返回的 ResearchState

    Returns:
        Dict: 分析结果
    """
    engine = ReasoningEngine()

    # 尝试配置
    try:
        await engine.configure(
            qwen_config=ModelConfig.qwen_local(),
            deepseek_config=ModelConfig.deepseek_api("")  # 需要API Key
        )
    except:
        pass

    # 生成假说
    hypotheses = await engine.generate_hypothesis(
        state.research_gaps if hasattr(state, 'research_gaps') else [],
        topic=state.query if hasattr(state, 'query') else ""
    )

    return {
        "query": state.query if hasattr(state, 'query') else "",
        "total_papers": state.total_results if hasattr(state, 'total_results') else 0,
        "key_themes": state.key_themes if hasattr(state, 'key_themes') else [],
        "gaps_identified": len(state.research_gaps) if hasattr(state, 'research_gaps') else 0,
        "hypotheses_generated": len(hypotheses),
        "hypotheses": hypotheses
    }


# ============ 示例用法 ============

async def demo():
    """演示推理引擎用法"""
    print("=" * 60)
    print("天问-AGI 推理引擎演示")
    print("=" * 60)

    # 创建引擎
    engine = ReasoningEngine()

    # 配置模型
    print("\n[1] 配置模型...")
    try:
        # 优先使用本地Ollama (无需网络，低延迟)
        await engine.configure(
            ollama_config=ModelConfig.ollama("llama2", "http://localhost:11434"),
            qwen_config=ModelConfig.qwen_local("http://localhost:8000"),
        )
        print("  ✅ Ollama配置成功 (llama2)")
    except Exception as e:
        print(f"  ⚠️ 模型配置失败: {e}")

    print(f"\n[2] 引擎状态: {engine.get_status()}")

    # 简单问题 - 优先使用Ollama
    print("\n[3] 测试简单问题 (LOW复杂度)...")
    result = await engine.think("太阳系有几个行星？", complexity="low")
    print(f"  问题: 太阳系有几个行星？")
    print(f"  答案: {result.content[:100]}...")
    print(f"  模型: {result.model_used}, 复杂度: {result.complexity}")

    # 复杂推理
    print("\n[4] 测试复杂推理 (HIGH复杂度)...")
    result = await engine.think(
        "分析人工智能对天文学研究的潜在影响，包括机遇和挑战",
        complexity="high"
    )
    print(f"  问题: 分析AI对天文学的影响")
    print(f"  思维链: {result.thinking_process[:100] if result.thinking_process else 'N/A'}...")
    print(f"  模型: {result.model_used}")

    # 列出Ollama可用模型
    print("\n[5] Ollama可用模型...")
    models = OllamaAdapter.list_models("http://localhost:11434")
    for m in models:
        print(f"  - {m.get('name', 'unknown')}")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
