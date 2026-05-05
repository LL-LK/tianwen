"""
Hermes-AGI Skill Testing Framework
技能测试框架 - 验证技能输出质量
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# ============ 测试结果 ============

class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    description: str
    input_data: Dict[str, Any]
    expected_output: Any
    validation_fn: Optional[Callable] = None  # 自定义验证函数

@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_name: str
    status: TestStatus
    execution_time: float
    actual_output: Any = None
    expected_output: Any = None
    error_message: str = ""
    suggestions: List[str] = field(default_factory=list)

@dataclass
class SkillTestReport:
    """技能测试报告"""
    skill_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    results: List[TestResult]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# ============ 验证器 ============

class OutputValidator:
    """输出验证器"""

    @staticmethod
    def validate_code_syntax(code: str, language: str = "python") -> tuple[bool, str]:
        """验证代码语法"""
        if not code or len(code.strip()) < 10:
            return False, "代码太短或为空"

        # 基本语法检查
        if language == "python":
            # 检查基本缩进
            if "def " in code or "class " in code:
                lines = code.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                        if i > 0 and lines[i-1].strip():
                            return False, f"缩进错误在第{i+1}行"
            return True, "语法检查通过"

        elif language == "javascript":
            # 检查基本括号匹配
            if code.count('{') != code.count('}'):
                return False, "花括号不匹配"
            if code.count('(') != code.count(')'):
                return False, "圆括号不匹配"
            return True, "语法检查通过"

        return True, "无需验证"

    @staticmethod
    def validate_json_structure(data: str) -> tuple[bool, str]:
        """验证JSON结构"""
        try:
            parsed = json.loads(data)
            return True, f"有效JSON，包含{len(parsed) if isinstance(parsed, (dict, list)) else 0}个键"
        except json.JSONDecodeError as e:
            return False, f"无效JSON: {str(e)}"

    @staticmethod
    def validate_api_spec(spec: str) -> tuple[bool, str]:
        """验证API规范"""
        required_fields = ['path', 'method']
        try:
            spec_data = json.loads(spec)
            for field in required_fields:
                if field not in spec_data:
                    return False, f"缺少必需字段: {field}"
            return True, "API规范有效"
        except (json.JSONDecodeError, ValueError):
            return False, "无法解析API规范"

    @staticmethod
    def validate_ddl(sql: str) -> tuple[bool, str]:
        """验证DDL语句"""
        sql_upper = sql.upper()
        if not any(keyword in sql_upper for keyword in ['CREATE', 'TABLE', 'ALTER', 'DROP']):
            return False, "不是有效的DDL语句"
        if 'CREATE' in sql_upper and 'TABLE' not in sql_upper:
            return False, "CREATE语句缺少TABLE关键字"
        return True, "DDL验证通过"

    @staticmethod
    def validate_markdown_structure(md: str) -> tuple[bool, str]:
        """验证Markdown结构"""
        if not md:
            return False, "文档为空"

        lines = md.split('\n')
        has_headers = any(line.startswith('#') for line in lines)
        has_sections = any('##' in line for line in lines)

        if not has_headers:
            return False, "缺少标题"
        if not has_sections:
            return False, "缺少二级章节"

        return True, "结构完整"

# ============ 预定义测试用例 ============

class SkillTestCases:
    """技能测试用例库"""

    @staticmethod
    def get_frontend_tests() -> List[TestCase]:
        return [
            TestCase(
                id="FE-001",
                name="React组件生成",
                description="生成一个React用户列表组件",
                input_data={
                    "component": "UserList",
                    "props": ["users", "onSelect"],
                    "features": ["分页", "搜索"]
                },
                expected_output={
                    "has_react_import": True,
                    "has_component_function": True,
                    "has_props": True
                }
            ),
            TestCase(
                id="FE-002",
                name="CSS样式生成",
                description="生成响应式卡片样式",
                input_data={
                    "element": "card",
                    "responsive": True
                },
                expected_output={
                    "has_flexbox_or_grid": True,
                    "has_media_queries": True
                }
            ),
        ]

    @staticmethod
    def get_backend_tests() -> List[TestCase]:
        return [
            TestCase(
                id="BE-001",
                name="FastAPI路由生成",
                description="生成用户CRUD API",
                input_data={
                    "model": "User",
                    "endpoints": ["create", "read", "update", "delete"]
                },
                expected_output={
                    "has_fastapi_imports": True,
                    "has_decorators": True,
                    "endpoint_count": 4
                }
            ),
            TestCase(
                id="BE-002",
                name="数据库模型",
                description="生成SQLAlchemy模型",
                input_data={
                    "table": "users",
                    "columns": ["id", "name", "email", "password"]
                },
                expected_output={
                    "has_class": True,
                    "has_column_definitions": True
                }
            ),
        ]

    @staticmethod
    def get_database_tests() -> List[TestCase]:
        return [
            TestCase(
                id="DB-001",
                name="ER图生成",
                description="生成电商系统ER图",
                input_data={
                    "entities": ["User", "Product", "Order", "Payment"]
                },
                expected_output={
                    "entity_count": 4,
                    "has_relationships": True
                }
            ),
            TestCase(
                id="DB-002",
                name="DDL生成",
                description="生成用户表DDL",
                input_data={
                    "table": "users",
                    "columns": [
                        {"name": "id", "type": "INT", "pk": True},
                        {"name": "email", "type": "VARCHAR(255)", "unique": True},
                        {"name": "password_hash", "type": "VARCHAR(255)"}
                    ]
                },
                expected_output={
                    "has_create_table": True,
                    "has_primary_key": True
                }
            ),
        ]

    @staticmethod
    def get_architecture_tests() -> List[TestCase]:
        return [
            TestCase(
                id="ARCH-001",
                name="微服务架构设计",
                description="设计电商微服务架构",
                input_data={
                    "system": "ecommerce",
                    "scale": "large"
                },
                expected_output={
                    "has_service_mesh": True,
                    "service_count": 5,
                    "has_caching": True
                }
            ),
        ]

    @staticmethod
    def get_testing_tests() -> List[TestCase]:
        return [
            TestCase(
                id="TEST-001",
                name="单元测试生成",
                description="生成加法函数测试",
                input_data={
                    "function": "add",
                    "params": ["a", "b"],
                    "test_cases": ["positive", "negative", "zero"]
                },
                expected_output={
                    "has_test_class": True,
                    "has_assertions": True,
                    "test_count": 3
                }
            ),
        ]

    @staticmethod
    def get_all_tests() -> Dict[str, List[TestCase]]:
        return {
            "Frontend": SkillTestCases.get_frontend_tests(),
            "Backend": SkillTestCases.get_backend_tests(),
            "Database": SkillTestCases.get_database_tests(),
            "Architecture": SkillTestCases.get_architecture_tests(),
            "Testing": SkillTestCases.get_testing_tests(),
        }

# ============ 技能测试器 ============

class SkillTester:
    """技能测试器"""

    def __init__(self):
        self.validator = OutputValidator()
        self.test_cases = SkillTestCases.get_all_tests()
        self.results_history: List[SkillTestReport] = []

    def run_test(self, test_case: TestCase, actual_output: str, output_type: str = "code") -> TestResult:
        """运行单个测试"""
        start_time = datetime.now()

        try:
            # 根据输出类型选择验证方法
            if output_type == "code":
                is_valid, msg = self.validator.validate_code_syntax(actual_output)
            elif output_type == "json":
                is_valid, msg = self.validator.validate_json_structure(actual_output)
            elif output_type == "api":
                is_valid, msg = self.validator.validate_api_spec(actual_output)
            elif output_type == "ddl":
                is_valid, msg = self.validator.validate_ddl(actual_output)
            elif output_type == "markdown":
                is_valid, msg = self.validator.validate_markdown_structure(actual_output)
            else:
                is_valid, msg = True, "跳过验证"

            execution_time = (datetime.now() - start_time).total_seconds()

            if is_valid:
                return TestResult(
                    test_id=test_case.id,
                    test_name=test_case.name,
                    status=TestStatus.PASSED,
                    execution_time=execution_time,
                    actual_output=actual_output[:200],
                    suggestions=[msg]
                )
            else:
                return TestResult(
                    test_id=test_case.id,
                    test_name=test_case.name,
                    status=TestStatus.FAILED,
                    execution_time=execution_time,
                    actual_output=actual_output[:200],
                    error_message=msg,
                    suggestions=[f"修复: {msg}"]
                )

        except Exception as e:
            return TestResult(
                test_id=test_case.id,
                test_name=test_case.name,
                status=TestStatus.ERROR,
                execution_time=(datetime.now() - start_time).total_seconds(),
                error_message=str(e),
                suggestions=["检查输出格式是否正确"]
            )

    def test_skill(self, skill_name: str, mock_output_provider: Callable) -> SkillTestReport:
        """测试指定技能的所有用例"""
        test_cases = self.test_cases.get(skill_name, [])
        results = []

        for test_case in test_cases:
            # 模拟获取技能输出
            actual_output = mock_output_provider(test_case)
            result = self.run_test(test_case, actual_output)
            results.append(result)

        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        report = SkillTestReport(
            skill_name=skill_name,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            results=results
        )

        self.results_history.append(report)
        return report

    def get_summary_report(self) -> Dict:
        """获取汇总报告"""
        total = len(self.results_history)
        if total == 0:
            return {"message": "No tests run yet"}

        total_tests = sum(r.total_tests for r in self.results_history)
        total_passed = sum(r.passed for r in self.results_history)
        total_failed = sum(r.failed for r in self.results_history)

        return {
            "total_skill_reports": total,
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "success_rate": total_passed / total_tests if total_tests > 0 else 0,
            "skills_tested": [r.skill_name for r in self.results_history]
        }

# ============ 示例用法 ============

def demo():
    """演示技能测试"""
    print("=" * 50)
    print("Hermes-AGI Skill Testing Framework Demo")
    print("=" * 50)

    tester = SkillTester()

    # 模拟输出提供者
    def mock_provider(test_case: TestCase) -> str:
        outputs = {
            "FE-001": """import React from 'react';

function UserList({ users, onSelect }) {
    return (
        <div className="user-list">
            {users.map(user => (
                <div key={user.id} onClick={() => onSelect(user)}>
                    {user.name}
                </div>
            ))}
        </div>
    );
}""",
            "BE-001": """from fastapi import FastAPI
app = FastAPI()

@app.post("/users")
def create_user(user: User):
    return user

@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"id": user_id}""",
            "DB-001": """CREATE TABLE users (
    id INT PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255)
);""",
        }
        return outputs.get(test_case.id, "# Code output")

    # 测试 Frontend 技能
    print("\n测试 Frontend 技能...")
    report = tester.test_skill("Frontend", mock_provider)
    print(f"\n{report.skill_name} 测试报告:")
    print(f"  总计: {report.total_tests}")
    print(f"  通过: {report.passed}")
    print(f"  失败: {report.failed}")
    print(f"  跳过: {report.skipped}")

    for result in report.results:
        status_icon = "✅" if result.status == TestStatus.PASSED else "❌" if result.status == TestStatus.FAILED else "⏭️"
        print(f"  {status_icon} {result.test_id}: {result.test_name}")
        if result.error_message:
            print(f"     错误: {result.error_message}")

    # 测试 Backend 技能
    print("\n测试 Backend 技能...")
    report = tester.test_skill("Backend", mock_provider)
    print(f"\n{report.skill_name} 测试报告:")
    print(f"  通过率: {report.passed}/{report.total_tests}")

    # 汇总报告
    print("\n" + "=" * 50)
    print("汇总报告:")
    summary = tester.get_summary_report()
    print(f"  总测试数: {summary.get('total_tests', 0)}")
    print(f"  通过率: {summary.get('success_rate', 0)*100:.1f}%")

if __name__ == "__main__":
    demo()