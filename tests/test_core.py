"""
tianwen-agi Core Tests
测试核心模块: _safe_eval, workflow_engine, coordinator_core, mcp_agents
"""
import pytest
import ast
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.workflow_engine_agents import _safe_eval as wf_safe_eval, WorkflowEngine, WorkflowNode, NodeType
from agents.agent_enhancements import _safe_eval as ae_safe_eval
from agents.mcp_agents import Tool, ToolCall, ToolResult, ToolStatus


class TestSafeEval:
    """测试 _safe_eval AST白名单"""

    def test_simple_comparisons(self):
        """测试简单比较运算"""
        vars = {"a": 5, "b": 3, "c": 0}
        assert wf_safe_eval("a > b", vars) is True
        assert wf_safe_eval("a < b", vars) is False
        assert wf_safe_eval("a == 5", vars) is True
        assert wf_safe_eval("a != b", vars) is True
        assert wf_safe_eval("a >= 5", vars) is True
        assert wf_safe_eval("b <= 3", vars) is True

    def test_boolean_operators(self):
        """测试布尔运算符"""
        vars = {"a": 5, "b": 3, "c": True}
        assert wf_safe_eval("a > b and c", vars) is True
        assert wf_safe_eval("a > b or False", vars) is True
        assert wf_safe_eval("not False", vars) is True
        assert wf_safe_eval("a > b and not False", vars) is True

    def test_in_notin_operators(self):
        """测试 in/not in 运算符"""
        vars = {"items": [1, 2, 3], "name": "test", "text": "hello world"}
        assert wf_safe_eval("1 in items", vars) is True
        assert wf_safe_eval("4 not in items", vars) is True
        assert wf_safe_eval("'test' in name", vars) is True
        assert wf_safe_eval("'world' in text", vars) is True

    def test_is_isnot_operators(self):
        """测试 is/is not 运算符"""
        vars = {"a": None, "b": None, "c": 5}
        assert wf_safe_eval("a is None", vars) is True
        assert wf_safe_eval("a is not None", vars) is False
        assert wf_safe_eval("b is None", vars) is True
        assert wf_safe_eval("c is not None", vars) is True

    def test_arithmetic_comparison(self):
        """测试算术表达式在比较上下文中"""
        # Note: _safe_eval returns bool(), so pure arithmetic needs comparison
        vars = {"a": 10, "b": 3}
        # These work because they're comparisons with arithmetic
        assert wf_safe_eval("a + b > 12", vars) is True
        assert wf_safe_eval("a + b < 12", vars) is False
        assert wf_safe_eval("a * b == 30", vars) is True

    def test_complex_expressions(self):
        """测试复杂表达式"""
        vars = {"anomaly_count": 3, "loop_count": 2, "pattern_count": 5}
        assert wf_safe_eval("anomaly_count > 0", vars) is True
        assert wf_safe_eval("loop_count < 10 and pattern_count >= 3", vars) is True
        assert wf_safe_eval("anomaly_count > 10 or pattern_count < 3", vars) is False

    def test_unsafe_expressions_blocked(self):
        """测试危险表达式被阻止"""
        vars = {"a": 5}
        dangerous = [
            "exec('print(1)')",
            "__import__('os').system('ls')",
            "[].__class__.__bases__[0].__subclasses__()",
        ]
        for expr in dangerous:
            with pytest.raises((ValueError, SyntaxError)):
                wf_safe_eval(expr, vars)

    def test_agent_enhancements_safe_eval(self):
        """测试 agent_enhancements 的 _safe_eval"""
        vars = {"a": 5, "b": 3}
        assert ae_safe_eval("a > b", vars) is True
        assert ae_safe_eval("a in [3, 5, 7]", vars) is True


class TestWorkflowEngine:
    """测试工作流引擎"""

    def test_workflow_engine_initialization(self):
        """测试工作流引擎初始化"""
        engine = WorkflowEngine()
        assert engine is not None
        assert isinstance(engine.definitions, dict)

    def test_workflow_node_creation(self):
        """测试工作流节点创建"""
        node = WorkflowNode(
            id="test_node",
            type=NodeType.LITERATURE_SEARCH,
            label="Test Node",
            config={"query": "test"}
        )
        assert node.id == "test_node"
        assert node.type == NodeType.LITERATURE_SEARCH
        assert node.label == "Test Node"

    def test_workflow_engine_get_templates(self):
        """测试获取模板"""
        engine = WorkflowEngine()
        templates = engine.get_templates()
        assert "full_research_cycle" in templates
        assert "quick_observation" in templates
        assert "literature_deep_dive" in templates
        assert "starwhisper_ngss" in templates  # 新增: StarWhisper论文模板


class TestMCPAgents:
    """测试MCP Agent工具"""

    def test_tool_definition(self):
        """测试工具定义"""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            category="test"
        )
        assert tool.name == "test_tool"
        assert tool.status == ToolStatus.AVAILABLE

    def test_tool_call_creation(self):
        """测试工具调用创建"""
        call = ToolCall(
            tool_name="test_tool",
            parameters={"arg1": "value1"}
        )
        assert call.tool_name == "test_tool"
        assert call.parameters["arg1"] == "value1"

    def test_tool_result(self):
        """测试工具结果"""
        result = ToolResult(
            tool_name="test_tool",
            call_id="call_123",
            success=True,
            result={"output": "success"}
        )
        assert result.success is True
        assert result.result["output"] == "success"


class TestNodeTypes:
    """测试节点类型枚举"""

    def test_all_node_types_exist(self):
        """测试所有节点类型都存在"""
        expected_types = [
            "TRIGGER", "LITERATURE_SEARCH", "HYPOTHESIS_GENERATE",
            "HYPOTHESIS_TEST", "OBSERVATION_SCHEDULE", "TELESCOPE_GOTO",
            "TELESCOPE_EXPOSE", "DATA_MINING", "ANOMALY_DETECTION",
            "FEATURE_EXTRACTION", "RESULT_ANALYSIS", "GUIDE_OBSERVATION",
            "REPORT_GENERATE", "CONDITION", "PARALLEL", "MERGE",
            "HUMAN_APPROVAL", "WEBHOOK", "CUSTOM"
        ]
        for type_name in expected_types:
            assert hasattr(NodeType, type_name), f"NodeType.{type_name} missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
