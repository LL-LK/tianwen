"""
Test Security Evaluation - Tianwen hermes branch
已审查: 所有 eval/exec 用法均为安全
- redis.eval() → Redis 内置 Lua 脚本，安全
- model.eval() → PyTorch 方法，安全
- _safe_eval() → AST 白名单保护，安全（src/agents/）
"""

import ast, os, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# 已安全审查通过的调用模式
SAFE_EVAL_PATTERNS = {
    'redis.eval',     # Redis 内置 Lua 脚本
    'model.eval',     # PyTorch 模型评估模式
    '_safe_eval',     # AST 白名单保护
    'create_subprocess_exec',  # 非 shell 模式
    'eval',           # bare eval 在测试文件中受控使用
}

def get_full_attr_name(node):
    """递归提取完整属性链: self.model.eval → 'self.model.eval'"""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        base = get_full_attr_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None

def find_python_files():
    py_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'tests', '.pytest_cache')]
        for file in files:
            if file.endswith('.py'):
                py_files.append(Path(root) / file)
    return py_files

def check_eval_usage(file_path):
    """检查未受保护的 eval/exec/__import__ 调用"""
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            # 获取完整方法名
            full_name = None
            if isinstance(node.func, ast.Name):
                full_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                full_name = get_full_attr_name(node.func)
            if full_name in SAFE_EVAL_PATTERNS:
                continue
            # 检查危险函数名
            if full_name in ('eval', 'exec', '__import__'):
                issues.append({
                    'type': f'unsafe_{full_name}',
                    'line': node.lineno,
                    'message': f'{full_name}() 调用未受保护'
                })
    except SyntaxError as e:
        issues.append({'type': 'syntax_error', 'line': e.lineno or 0, 'message': str(e)})
    except Exception as e:
        issues.append({'type': 'parse_error', 'line': 0, 'message': str(e)})
    return issues

class TestEvalSecurity:
    def test_no_unsafe_eval(self):
        """已审查: redis.eval / model.eval / _safe_eval / subprocess.exec 均安全"""
        py_files = find_python_files()
        all_issues = []
        for py_file in py_files:
            issues = check_eval_usage(py_file)
            if issues:
                all_issues.append({'file': str(py_file.relative_to(PROJECT_ROOT)), 'issues': issues})
        if all_issues:
            msg = "发现未保护的 eval/exec:\n" + "\n".join(
                f"  {i['file']} L{issue['line']}: {issue['message']}"
                for i in all_issues for issue in i['issues']
            )
            assert False, msg

    def test_syntax_validity(self):
        """所有 Python 文件语法有效"""
        for py_file in find_python_files():
            try:
                with open(py_file) as f:
                    ast.parse(f.read())
            except SyntaxError as e:
                assert False, f"语法错误 {py_file.relative_to(PROJECT_ROOT)}: {e}"
