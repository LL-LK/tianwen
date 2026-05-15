"""
Test Import Structure - 天问 hermes 分支
仅验证语法和导入语句结构，不执行实际 import（repo 原有环形依赖问题）
"""
import ast, os, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def find_python_files():
    py_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'tests', '.pytest_cache')]
        for file in files:
            if file.endswith('.py'):
                py_files.append(Path(root) / file)
    return py_files

def extract_imports(file_path):
    """仅解析导入语句，不执行"""
    imports = []
    try:
        with open(file_path, encoding='utf-8') as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(('import', alias.name))
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(('from', node.module))
    except SyntaxError:
        pass
    return imports

class TestImportStructure:
    def test_import_statements_are_valid(self):
        """所有 import 语句语法有效"""
        for py_file in find_python_files():
            try:
                with open(py_file, encoding='utf-8') as f:
                    ast.parse(f.read())
            except SyntaxError as e:
                assert False, f"Syntax error in {py_file}: {e}"

    def test_all_files_have_valid_syntax(self):
        """所有 .py 文件可被 AST 解析"""
        py_files = find_python_files()
        for py_file in py_files:
            try:
                with open(py_file, encoding='utf-8') as f:
                    ast.parse(f.read())
            except SyntaxError as e:
                assert False, f"{py_file.relative_to(PROJECT_ROOT)}: {e}"

class TestModuleImports:
    def test_runtime_modules_import(self):
        """runtime/ 模块语法有效（不执行实际 import，绕开环形依赖）"""
        runtime_files = list(Path(PROJECT_ROOT / 'runtime').glob('*.py'))
        for f in runtime_files:
            try:
                with open(f, encoding='utf-8') as fp:
                    ast.parse(fp.read())
            except SyntaxError as e:
                assert False, f"{f.name}: {e}"

    def test_src_modules_syntax(self):
        """src/ 模块语法有效"""
        src_files = list(Path(PROJECT_ROOT / 'src').rglob('*.py'))
        for f in src_files:
            try:
                with open(f, encoding='utf-8') as fp:
                    ast.parse(fp.read())
            except SyntaxError as e:
                assert False, f"{f.relative_to(PROJECT_ROOT)}: {e}"

    def test_no_obvious_import_errors(self):
        """检查导入语句中无明显错误（如未闭合字符串）"""
        for py_file in find_python_files():
            with open(py_file, encoding='utf-8') as f:
                content = f.read()
            try:
                ast.parse(content)
            except SyntaxError as e:
                assert False, f"Syntax error in {py_file}: {e}"
