"""
Hermes-AGI Skill Integration System
技能集成系统 - 实现技能间调用协议和数据传递
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

# ============ 技能接口定义 ============

class SkillStatus(Enum):
    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    EXECUTING = "executing"
    ERROR = "error"

@dataclass
class SkillInput:
    """技能输入 schema"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None

@dataclass
class SkillOutput:
    """技能输出 schema"""
    name: str
    type: str
    description: str

@dataclass
class SkillInterface:
    """技能接口定义"""
    name: str
    description: str
    version: str
    input_schema: List[SkillInput] = field(default_factory=list)
    output_schema: List[SkillOutput] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # 前置技能
    next_skills: List[str] = field(default_factory=list)   # 后续技能

@dataclass
class SkillExecution:
    """技能执行上下文"""
    skill_name: str
    task_id: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    status: SkillStatus = SkillStatus.IDLE
    error: Optional[str] = None
    execution_time: float = 0

# ============ 技能注册表 ============

class SkillRegistry:
    """技能注册表 - 管理所有技能的元数据"""

    def __init__(self):
        self.skills: Dict[str, SkillInterface] = {}
        self._register_builtin_skills()

    def _register_builtin_skills(self):
        """注册内置技能接口"""
        builtin_skills = [
            SkillInterface(
                name="Product",
                description="产品需求分析",
                version="1.0",
                input_schema=[
                    SkillInput("user_request", "string", "用户原始需求", True),
                    SkillInput("constraints", "dict", "约束条件", False, {}),
                ],
                output_schema=[
                    SkillOutput("prd", "string", "产品需求文档"),
                    SkillOutput("scope", "list", "需求范围"),
                ],
                next_skills=["Architecture", "Database", "Frontend", "Backend"]
            ),
            SkillInterface(
                name="Architecture",
                description="系统架构设计",
                version="1.0",
                input_schema=[
                    SkillInput("requirements", "string", "需求说明", True),
                    SkillInput("scale", "string", "系统规模", False, "medium"),
                ],
                output_schema=[
                    SkillOutput("architecture_diagram", "string", "架构图描述"),
                    SkillOutput("tech_stack", "list", "技术栈选择"),
                    SkillOutput("components", "list", "组件列表"),
                ],
                dependencies=["Product"],
                next_skills=["Database", "API-Design", "DevOps"]
            ),
            SkillInterface(
                name="Database",
                description="数据库设计",
                version="1.0",
                input_schema=[
                    SkillInput("entities", "list", "实体列表", True),
                    SkillInput("relationships", "list", "关系列表", False, []),
                ],
                output_schema=[
                    SkillOutput("er_diagram", "string", "ER图描述"),
                    SkillOutput("ddl", "string", "建表SQL"),
                    SkillOutput("tables", "list", "表结构"),
                ],
                dependencies=["Architecture", "Product"],
                next_skills=["Backend", "API-Design"]
            ),
            SkillInterface(
                name="API-Design",
                description="API接口设计",
                version="1.0",
                input_schema=[
                    SkillInput("endpoints", "list", "端点列表", True),
                    SkillInput("data_models", "list", "数据模型", False, []),
                ],
                output_schema=[
                    SkillOutput("openapi_spec", "string", "OpenAPI规范"),
                    SkillOutput("endpoints", "list", "端点定义"),
                ],
                dependencies=["Architecture", "Database"],
                next_skills=["Backend", "Frontend"]
            ),
            SkillInterface(
                name="Backend",
                description="后端开发",
                version="1.0",
                input_schema=[
                    SkillInput("api_spec", "string", "API规范", True),
                    SkillInput("language", "string", "编程语言", False, "python"),
                ],
                output_schema=[
                    SkillOutput("code", "string", "代码"),
                    SkillOutput("tests", "string", "测试代码"),
                ],
                dependencies=["API-Design", "Database"],
                next_skills=["Testing", "Security"]
            ),
            SkillInterface(
                name="Frontend",
                description="前端开发",
                version="1.0",
                input_schema=[
                    SkillInput("design", "string", "UI设计", True),
                    SkillInput("api_spec", "string", "API规范", False, ""),
                ],
                output_schema=[
                    SkillOutput("components", "string", "组件代码"),
                    SkillOutput("styles", "string", "样式代码"),
                ],
                dependencies=["API-Design", "UI-Visual"],
                next_skills=["Testing", "Code-Review"]
            ),
            SkillInterface(
                name="Testing",
                description="测试",
                version="1.0",
                input_schema=[
                    SkillInput("code", "string", "待测代码", True),
                    SkillInput("test_type", "string", "测试类型", False, "unit"),
                ],
                output_schema=[
                    SkillOutput("test_cases", "string", "测试用例"),
                    SkillOutput("coverage", "number", "覆盖率"),
                ],
                dependencies=["Backend", "Frontend"]
            ),
            SkillInterface(
                name="Security",
                description="安全审查",
                version="1.0",
                input_schema=[
                    SkillInput("code", "string", "待审代码", True),
                    SkillInput("language", "string", "语言", False, "python"),
                ],
                output_schema=[
                    SkillOutput("vulnerabilities", "list", "漏洞列表"),
                    SkillOutput("severity", "string", "严重程度"),
                ],
                dependencies=["Backend", "Frontend"]
            ),
            SkillInterface(
                name="AstroPipeline",
                description="天文图像分析管道 - 点源检测、恒星/星系分类、目标检测",
                version="1.0",
                input_schema=[
                    SkillInput("image_data", "object", "天文图像数据", True),
                ],
                output_schema=[
                    SkillOutput("sources", "list", "检测到的点源列表"),
                    SkillOutput("detections", "list", "检测结果(STAR/GALAXY/QSO/nebula/galaxy)"),
                    SkillOutput("summary", "dict", "分析摘要"),
                ],
                dependencies=[],
                next_skills=[]
            ),
        ]

        for skill in builtin_skills:
            self.register(skill)

    def register(self, skill: SkillInterface):
        """注册技能"""
        self.skills[skill.name] = skill

    def get(self, name: str) -> Optional[SkillInterface]:
        """获取技能接口"""
        return self.skills.get(name)

    def get_workflow(self, skill_names: List[str]) -> List[SkillInterface]:
        """获取技能工作流（按依赖排序）"""
        result = []
        visited = set()

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            skill = self.get(name)
            if skill:
                for dep in skill.dependencies:
                    visit(dep)
                if name not in [s.name for s in result]:
                    result.append(skill)

        for name in skill_names:
            visit(name)

        return result

    def suggest_next(self, current_skill: str) -> List[str]:
        """建议后续技能"""
        skill = self.get(current_skill)
        if not skill:
            return []
        return skill.next_skills

# ============ 技能执行器 ============

class SkillExecutor:
    """技能执行器 - 执行单个技能"""

    def __init__(self, skill_dir: str = "./skills"):
        self.skill_dir = Path(skill_dir)
        self.registry = SkillRegistry()
        self.execution_history: List[SkillExecution] = []

    def load_skill_content(self, skill_name: str) -> Optional[str]:
        """加载技能文档内容"""
        skill_file = self.skill_dir / f"{skill_name}.md"
        if skill_file.exists():
            return skill_file.read_text(encoding='utf-8')
        return None

    async def execute(self, skill_name: str, input_data: Dict[str, Any], task_id: str = "") -> SkillExecution:
        """执行技能"""
        execution = SkillExecution(
            skill_name=skill_name,
            task_id=task_id,
            input_data=input_data,
        )

        skill_interface = self.registry.get(skill_name)
        if not skill_interface:
            execution.status = SkillStatus.ERROR
            execution.error = f"Skill {skill_name} not found"
            return execution

        try:
            execution.status = SkillStatus.EXECUTING

            # 模拟技能执行 - 实际应该调用AI处理技能文档
            import asyncio
            await asyncio.sleep(0.1)  # 模拟处理时间

            # 生成模拟输出
            output = self._generate_mock_output(skill_name, input_data)
            execution.output_data = output
            execution.status = SkillStatus.READY

        except Exception as e:
            execution.status = SkillStatus.ERROR
            execution.error = str(e)

        self.execution_history.append(execution)
        return execution

    def _generate_mock_output(self, skill_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成模拟输出"""
        outputs = {
            "Product": {
                "prd": f"PRD文档已生成\n需求: {input_data.get('user_request', 'N/A')}",
                "scope": ["功能模块1", "功能模块2"],
            },
            "Architecture": {
                "architecture_diagram": "系统采用微服务架构",
                "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Redis"],
                "components": ["用户服务", "订单服务", "支付服务"],
            },
            "Database": {
                "er_diagram": "用户表、订单表、商品表",
                "ddl": "CREATE TABLE users (...);",
                "tables": ["users", "orders", "products"],
            },
            "API-Design": {
                "openapi_spec": "OpenAPI 3.0规范",
                "endpoints": ["/api/users", "/api/orders"],
            },
            "Backend": {
                "code": f"# {skill_name} code generated\n# Input: {input_data}",
                "tests": "# Test cases",
            },
            "Frontend": {
                "components": "# React components",
                "styles": "# CSS styles",
            },
            "Testing": {
                "test_cases": "# Unit tests",
                "coverage": 0.85,
            },
            "Security": {
                "vulnerabilities": [],
                "severity": "low",
            },
        }
        return outputs.get(skill_name, {"result": f"{skill_name} executed"})

# ============ 技能链执行器 ============

class SkillChainExecutor:
    """技能链执行器 - 按顺序执行多个技能，传递数据"""

    def __init__(self, skill_dir: str = "./skills"):
        self.executor = SkillExecutor(skill_dir)
        self.registry = self.executor.registry

    async def execute_chain(
        self,
        skill_names: List[str],
        initial_input: Dict[str, Any],
        task_id: str = ""
    ) -> List[SkillExecution]:
        """执行技能链"""
        # 获取按依赖排序的工作流
        workflow = self.registry.get_workflow(skill_names)

        if not workflow:
            # 如果没有预定义工作流，按给定顺序执行
            workflow_names = skill_names
        else:
            workflow_names = [s.name for s in workflow]

        results = []
        current_data = initial_input.copy()

        for skill_name in workflow_names:
            execution = await self.executor.execute(skill_name, current_data, task_id)
            results.append(execution)

            if execution.status == SkillStatus.ERROR:
                break

            # 将输出传递给下一个技能
            if execution.output_data:
                current_data.update(execution.output_data)

        return results

    def get_data_flow(self, skill_names: List[str]) -> List[Dict[str, Any]]:
        """获取技能之间的数据流信息"""
        workflow = self.registry.get_workflow(skill_names)
        flow = []

        for skill in workflow:
            flow.append({
                "skill": skill.name,
                "inputs": [{"name": i.name, "type": i.type} for i in skill.input_schema],
                "outputs": [{"name": o.name, "type": o.type} for o in skill.output_schema],
                "next": skill.next_skills,
            })

        return flow

# ============ 便捷函数 ============

def create_skill_executor(skill_dir: str = "./skills") -> SkillExecutor:
    """创建技能执行器"""
    return SkillExecutor(skill_dir)

def create_chain_executor(skill_dir: str = "./skills") -> SkillChainExecutor:
    """创建技能链执行器"""
    return SkillChainExecutor(skill_dir)

# ============ 示例用法 ============

async def demo():
    """演示技能链执行"""
    print("=" * 50)
    print("Hermes-AGI Skill Chain Demo")
    print("=" * 50)

    chain = create_chain_executor()

    # 定义技能链
    skills = ["Backend"]

    # 执行链
    print(f"\n执行技能链: {' -> '.join(skills)}\n")

    results = await chain.execute_chain(
        skills,
        {"user_request": "创建一个用户管理系统"},
        task_id="DEMO-001"
    )

    # 输出结果
    for result in results:
        print(f"\n{result.skill_name}:")
        print(f"  Status: {result.status.value}")
        if result.output_data:
            for k, v in result.output_data.items():
                print(f"  {k}: {v}")
        if result.error:
            print(f"  Error: {result.error}")

    # 显示数据流
    print("\n\n数据流:")
    flow = chain.get_data_flow(skills)
    for step in flow:
        print(f"  {step['skill']}:")
        print(f"    Inputs: {[i['name'] for i in step['inputs']]}")
        print(f"    Outputs: {[o['name'] for o in step['outputs']]}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())