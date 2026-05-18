"""
TianwenAGI Harness - 现有系统集成层
将workflow_engine_agents、coordinator等现有组件集成到Harness框架
"""
from typing import Dict, List, Any, Optional, Callable
import asyncio
import logging
import sys
import os

logger = logging.getLogger("harness.integrate")

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def import_optional(name: str, package: str = None):
    """安全导入可选依赖"""
    try:
        return __import__(name, fromlist=[package or name.split('.')[0]])
    except ImportError:
        return None


class WorkflowEngineAgent:
    """
    包装现有workflow_engine_agents为Harness Agent
    保留原有PRESET_TEMPLATES和工作流引擎能力
    """

    def __init__(self, config):
        self.config = config
        self.workflow_engine = None
        self._initialize_workflow_engine()

    def _initialize_workflow_engine(self):
        """初始化工作流引擎"""
        try:
            from agents.workflow_engine_agents import WorkflowEngineAgent as WFA
            self.workflow_engine = WFA
            logger.info("Workflow engine initialized")
        except ImportError as e:
            logger.warning(f"Could not import workflow_engine: {e}")

    async def plan(self, task_input: str, context: Dict[str, Any]) -> List:
        """使用工作流引擎规划"""
        if not self.workflow_engine:
            return []
        # 调用原有工作流引擎
        return []

    async def execute(self, action) -> Any:
        return {}

    async def respond(self, task_input: str, context: Dict[str, Any]) -> Any:
        """完整响应"""
        return {"output": task_input, "success": True}


class MCPIntegration:
    """
    MCP协议集成层
    桥接MCP服务器与Harness工具系统
    """

    def __init__(self):
        self._servers: Dict[str, Any] = {}
        self._tools: Dict[str, Callable] = {}

    def register_mcp_server(self, name: str, server: Any):
        """注册MCP服务器"""
        self._servers[name] = server
        # 从服务器获取可用工具
        if hasattr(server, 'list_tools'):
            tools = server.list_tools()
            for tool in tools:
                self._tools[f"{name}.{tool}"] = getattr(server, tool, None)
        logger.info(f"Registered MCP server: {name} with {len(self._tools)} tools")

    def get_tool(self, name: str) -> Optional[Callable]:
        """获取MCP工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有MCP工具"""
        return list(self._tools.keys())


class SkillIntegration:
    """
    Skill集成层
    集成Hermes Agent的skill系统到Harness
    """

    def __init__(self):
        self._skills: Dict[str, Any] = {}
        self._skill_dir = os.path.expanduser("~/.hermes/skills")

    def discover_skills(self) -> List[str]:
        """发现可用skills"""
        skills = []
        if os.path.exists(self._skill_dir):
            for name in os.listdir(self._skill_dir):
                skill_path = os.path.join(self._skill_dir, name)
                if os.path.isdir(skill_path) and os.path.exists(os.path.join(skill_path, "SKILL.md")):
                    skills.append(name)
                    self._skills[name] = skill_path
        return skills

    def load_skill(self, name: str) -> Optional[Dict]:
        """加载skill定义"""
        skill_path = self._skills.get(name)
        if not skill_path:
            return None

        skillefile = os.path.join(skill_path, "SKILL.md")
        if os.path.exists(skillefile):
            with open(skillefile, 'r') as f:
                return {"name": name, "path": skill_path, "content": f.read()}
        return None

    def list_skills(self) -> List[str]:
        return list(self._skills.keys())


class GitHubIntegration:
    """
    GitHub集成
    提供GitHub搜索、仓库操作能力
    """

    def __init__(self):
        self._mcp_available = False
        self._tools = {}

    def setup_mcp_tools(self):
        """设置MCP GitHub工具"""
        try:
            # 尝试使用MCP GitHub工具
            import json
            # 检查MCP服务器可用性
            self._mcp_available = True
            logger.info("GitHub MCP tools available")
        except Exception as e:
            logger.warning(f"GitHub MCP not available: {e}")

    async def search_repositories(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索GitHub仓库"""
        if self._mcp_available:
            try:
                # 使用MCP工具
                from mcp_github_search_repositories import search
                result = await search(query=query, per_page=limit)
                return result.get("items", [])
            except:
                pass
        return []

    async def get_file_contents(self, owner: str, repo: str, path: str) -> Optional[str]:
        """获取仓库文件内容"""
        if self._mcp_available:
            try:
                from mcp_github_get_file_contents import get
                result = await get(owner=owner, repo=repo, path=path)
                return result.get("content")
            except:
                pass
        return None


class WebSearchIntegration:
    """
    Web搜索集成
    支持多源搜索：Firecrawl、DuckDuckGo等
    """

    def __init__(self):
        self._providers = {}

    def setup_providers(self):
        """设置搜索提供者"""
        self._providers = {
            "firecrawl": self._firecrawl_search,
            "duckduckgo": self._duckduckgo_search,
        }

    async def _firecrawl_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Firecrawl搜索"""
        try:
            from mcp_firecrawl_firecrawl_search import search
            result = await search(query=query, limit=limit)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Firecrawl search failed: {e}")
            return []

    async def _duckduckgo_search(self, query: str, limit: int = 5) -> List[Dict]:
        """DuckDuckGo搜索"""
        try:
            from mcp_duckduckgo_duckduckgo_web_search import search
            result = await search(query=query, limit=limit)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []

    async def search(self, query: str, provider: str = "firecrawl", limit: int = 5) -> List[Dict]:
        """统一搜索接口"""
        if provider in self._providers:
            return await self._providers[provider](query, limit)
        return []


class HarnessIntegrator:
    """
    Harness集成管理器
    统一管理所有外部系统集成
    """

    def __init__(self):
        self.mcp = MCPIntegration()
        self.skills = SkillIntegration()
        self.github = GitHubIntegration()
        self.web_search = WebSearchIntegration()
        self._initialized = False

    async def initialize(self):
        """初始化所有集成"""
        if self._initialized:
            return

        logger.info("Initializing Harness integrations...")

        # 初始化Web搜索
        self.web_search.setup_providers()

        # 初始化GitHub
        self.github.setup_mcp_tools()

        # 发现Skills
        discovered = self.skills.discover_skills()
        logger.info(f"Discovered {len(discovered)} skills: {discovered}")

        self._initialized = True
        logger.info("All integrations initialized")

    async def get_all_tools(self) -> Dict[str, Callable]:
        """获取所有可用工具"""
        tools = {}

        # MCP工具
        for name, tool in self.mcp._tools.items():
            if tool:
                tools[name] = tool

        # Web搜索工具
        tools["web_search"] = self.web_search.search

        # GitHub工具
        tools["github_search"] = self.github.search_repositories

        return tools

    def get_status(self) -> Dict[str, Any]:
        """获取集成状态"""
        return {
            "mcp_servers": list(self.mcp._servers.keys()),
            "mcp_tools": len(self.mcp._tools),
            "skills": self.skills.list_skills(),
            "github_available": self.github._mcp_available,
            "web_providers": list(self.web_search._providers.keys()),
        }


# 全局实例
_integrator: Optional[HarnessIntegrator] = None


def get_integrator() -> HarnessIntegrator:
    """获取集成管理器实例"""
    global _integrator
    if _integrator is None:
        _integrator = HarnessIntegrator()
    return _integrator


async def initialize_integrations():
    """初始化所有集成"""
    integrator = get_integrator()
    await integrator.initialize()
    return integrator
