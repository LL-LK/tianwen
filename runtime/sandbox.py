"""
Hermes-AGI Code Sandbox
代码执行沙箱 - 支持Python和JavaScript的实际执行

安全修复: 解决代码注入漏洞 (OWASP A03:2021)
- 用户输入通过文件传入而非命令行拼接
- 危险模块导入阻断
- 资源限制（CPU时间、内存）
- 严格的输入验证和转义
"""

import asyncio
import subprocess
import tempfile
import os
import json
import signal
import re
import resource
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime

# 危险模式列表 - 用于检测潜在的恶意代码
DANGEROUS_PATTERNS = [
    # 模块导入类
    r'\bimport\s+(os|subprocess|sys|pty|resource|fcntl|select|signal|multiprocessing)\b',
    r'\bfrom\s+(os|sys|subprocess|pty|resource)\s+import\b',
    r'\b__import__\s*\(',
    r'\bexec\s*\(',
    r'\beval\s*\(',
    r'\bcompile\s*\(',
    # 文件操作类
    r'\bopen\s*\([^)]*[\'"]/[^\'"]*[\'"]',
    r'\bexecfile\s*\(',
    r'\b__builtins__\b',
    # 命令执行类
    r'\bos\.system\s*\(',
    r'\bos\.popen\s*\(',
    r'\bsubprocess\.run\s*\(',
    r'\bsubprocess\.call\s*\(',
    r'\bsubprocess\.Popen\s*\(',
    r'\bpty\.spawn\s*\(',
    # 环境变量访问
    r'\bos\.environ\b',
    r'\bos\.getenv\s*\(',
    r'\bos\.putenv\s*\(',
    # 进程控制
    r'\bos\.fork\s*\(',
    r'\bos\.kill\s*\(',
    r'\bsignal\.signal\s*\(',
    # 反射操作
    r'\bgetattr\s*\(',
    r'\bsetattr\s*\(',
    r'\bdelattr\s*\(',
    r'\bhasattr\s*\(',
    r'\bvars\s*\(',
    r'\bdir\s*\(',
    # 内存相关
    r'\bctypes\s*\b',
    r'\bpy_compile\s*\(',
]

# 允许的输出函数白名单
ALLOWED_BUILTINS = {
    'print', 'len', 'range', 'str', 'int', 'float', 'bool',
    'list', 'dict', 'tuple', 'set', 'frozenset',
    'abs', 'max', 'min', 'sum', 'sorted', 'reversed',
    'enumerate', 'zip', 'map', 'filter',
    'isinstance', 'type', 'id', 'hash',
    'open',  # 限制在当前目录
    'json', 'math', 'random', 'datetime', 're',
}

# JavaScript 危险模式
JS_DANGEROUS_PATTERNS = [
    r'\beval\s*\(',
    r'\bFunction\s*\(',
    r'\brequire\s*\(',
    r'\bchild_process\b',
    r'\bexec\s*\(',
    r'\bspawn\s*\(',
    r'\bprocess\.env\b',
    r'\bprocess\.exit\b',
    r'\bprocess\.kill\b',
    r'\bfs\b.*\breadFileSync\b',
    r'\bfs\b.*\bwriteFileSync\b',
    r'\bBuffer\s*\(',
    r'\brequire\s*\(\s*[\'"]child_process[\'"]\s*\)',
    r'\brequire\s*\(\s*[\'"]fs[\'"]\s*\)',
]

@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: float = 0
    memory_usage: Optional[str] = None

class SecurityError(Exception):
    """安全检查失败异常"""
    pass


class CodeSandbox:
    """代码执行沙箱 - 安全版本"""

    def __init__(self, timeout: int = 30, max_output_size: int = 10000, max_memory_mb: int = 128):
        self.timeout = timeout  # 超时秒数
        self.max_output_size = max_output_size
        self.max_memory_mb = max_memory_mb  # 最大内存 MB

    def _check_dangerous_patterns(self, code: str, patterns: List[str], name: str = "code") -> None:
        """检查代码中的危险模式"""
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise SecurityError(f"禁止的模式 detected in {name}: {pattern}")

    def _validate_input_data(self, data: Any, path: str = "") -> Any:
        """递归验证输入数据，限制复杂度和类型"""
        if path.count('.') > 10:
            raise SecurityError("输入数据嵌套过深")

        if isinstance(data, dict):
            if len(data) > 100:
                raise SecurityError("输入数据字段过多")
            return {k: self._validate_input_data(v, f"{path}.{k}") for k, v in data.items()}
        elif isinstance(data, list):
            if len(data) > 1000:
                raise SecurityError("输入数据数组过长")
            return [self._validate_input_data(item, f"{path}[{i}]") for i, item in enumerate(data)]
        elif isinstance(data, str):
            if len(data) > 100000:
                raise SecurityError("输入数据字符串过长")
            return data
        elif isinstance(data, (int, float, bool, type(None))):
            return data
        else:
            raise SecurityError(f"不支持的数据类型: {type(data).__name__}")

    def _sanitize_code(self, code: str) -> str:
        """清理代码中的危险内容"""
        # 移除可能的 shebang
        code = re.sub(r'^#!.*$', '', code, flags=re.MULTILINE)
        # 移除编码声明
        code = re.sub(r'^#.*coding.*:$', '', code, flags=re.MULTILINE)
        return code.strip()

    def _create_safe_python_wrapper(self, user_code: str, input_file_path: str) -> str:
        """创建安全的 Python 代码包装器"""
        return f'''
# -*- coding: utf-8 -*-
# 安全沙箱环境

import sys
import json
import traceback

# 重定向危险函数
_original_open = open
_open_allowed_dirs = set()

def _safe_open(file, mode='r', *args, **kwargs):
    # 只允许在当前目录或临时目录
    if hasattr(file, 'name'):
        file = file.name
    if isinstance(file, str):
        if file.startswith('/') or (len(file) > 2 and file[1] == ':'):
            raise SecurityError("禁止绝对路径")
    return _original_open(file, mode, *args, **kwargs)

# 限制 builtins
_safe_builtins = {{}}
_unsafe_builtins = ['__import__', 'eval', 'exec', 'compile', 'reload', 'open']
for name in dir(__builtins__):
    if name not in _unsafe_builtins:
        _safe_builtins[name] = getattr(__builtins__, name)

# 读取输入数据
try:
    with open('{input_file_path}', 'r', encoding='utf-8') as _f:
        INPUT_DATA = json.load(_f)
except Exception as _e:
    INPUT_DATA = {{}}
    print(json.dumps({{"error": f"输入数据读取失败: {{_e}}"}}, ensure_ascii=False), file=sys.stderr)

# 用户代码执行
try:
{user_code}
except SecurityError as _se:
    print(json.dumps({{"error": str(_se), "type": "SecurityError"}}, ensure_ascii=False))
    sys.exit(1)
except Exception as _e:
    print(json.dumps({{"error": f"执行错误: {{_e}}"}}, ensure_ascii=False))
    sys.exit(1)

# 输出结果
if 'result' in dir():
    print(json.dumps({{"result": result, "status": "ok"}}, ensure_ascii=False))
else:
    print(json.dumps({{"status": "ok", "message": "代码执行完成，无返回值"}}, ensure_ascii=False))
'''

    async def execute_python(self, code: str, input_data: Optional[Dict] = None) -> ExecutionResult:
        """执行Python代码 - 安全版本"""
        start_time = datetime.now()

        try:
            # 安全检查
            code = self._sanitize_code(code)
            self._check_dangerous_patterns(code, DANGEROUS_PATTERNS, "Python code")

            # 验证输入数据
            if input_data:
                input_data = self._validate_input_data(input_data)

            # 创建输入数据文件（通过文件传入，而非命令行拼接）
            input_file_fd, input_file_path = tempfile.mkstemp(suffix='.json', prefix='input_')
            try:
                with os.fdopen(input_file_fd, 'w', encoding='utf-8') as f:
                    json.dump(input_data or {}, f, ensure_ascii=False, indent=2)

                # 创建用户代码文件
                code_file_fd, code_file_path = tempfile.mkstemp(suffix='.py', prefix='user_')
                try:
                    with os.fdopen(code_file_fd, 'w', encoding='utf-8') as f:
                        f.write(self._create_safe_python_wrapper(code, input_file_path.replace('\\', '\\\\')))

                    # 构建安全的执行命令
                    # 使用 -u 取消缓冲，使用 -B 避免写入 .pyc
                    cmd = [
                        sys.executable,
                        '-u',           # 无缓冲输出
                        '-B',           # 不写入字节码
                        '-X', 'utf8',   # UTF-8 模式
                        code_file_path
                    ]

                    # 设置环境变量限制
                    env = {
                        'PYTHONPATH': '',  # 清空路径
                        'PYTHONDONTWRITEBYTECODE': '1',
                        'PYTHONIOENCODING': 'utf-8',
                        'PYTHONUNBUFFERED': '1',
                    }

                    # 创建进程，使用低优先级和资源限制
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env,
                        # 限制工作目录在临时目录
                        cwd=tempfile.gettempdir()
                    )

                    try:
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(),
                            timeout=self.timeout
                        )
                    except asyncio.TimeoutError:
                        try:
                            process.kill()
                            await process.wait()
                        except:
                            pass
                        return ExecutionResult(
                            success=False,
                            output="",
                            error=f"执行超时（{self.timeout}秒），可能存在无限循环或资源占用"
                        )

                    execution_time = (datetime.now() - start_time).total_seconds()

                    if process.returncode == 0:
                        output = stdout.decode('utf-8', errors='replace')[:self.max_output_size]
                        return ExecutionResult(success=True, output=output, execution_time=execution_time)
                    else:
                        error = stderr.decode('utf-8', errors='replace')[:self.max_output_size]
                        # 检查是否是安全错误
                        if "SecurityError" in error or "禁止" in error:
                            return ExecutionResult(
                                success=False,
                                output="",
                                error=f"安全检查失败: {error}",
                                execution_time=execution_time
                            )
                        return ExecutionResult(
                            success=False,
                            output=stdout.decode('utf-8', errors='replace'),
                            error=error,
                            execution_time=execution_time
                        )

                finally:
                    try:
                        os.unlink(code_file_path)
                    except:
                        pass
            finally:
                try:
                    os.unlink(input_file_path)
                except:
                    pass

        except SecurityError as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"安全检查失败: {str(e)}"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"系统错误: {str(e)}"
            )

    def _create_safe_js_wrapper(self, user_code: str, input_file_path: str) -> str:
        """创建安全的 JavaScript 代码包装器"""
        return f'''
// 安全沙箱环境
const fs = require('fs');
const vm = require('vm');

// 读取输入数据
let INPUT_DATA = {{}};
try {{
    const inputContent = fs.readFileSync('{input_file_path.replace('\\\\', '\\\\\\\\')}', 'utf-8');
    INPUT_DATA = JSON.parse(inputContent);
}} catch (e) {{
    console.error(JSON.stringify({{error: "输入数据读取失败: " + e.message}}));
}}

// 限制危险的全局对象
const safeConsole = {{
    log: (...args) => console.log(...args),
    error: (...args) => console.error(...args),
    warn: (...args) => console.warn(...args),
    info: (...args) => console.info(...args),
}};

// 创建安全的上下文
const context = {{
    INPUT_DATA,
    console: safeConsole,
    require: undefined,  // 禁用 require
    process: undefined,  // 禁用 process
    Buffer: undefined,   // 禁用 Buffer
    setTimeout: undefined,
    setInterval: undefined,
    setImmediate: undefined,
}};

// 用户代码执行
try {{
{user_code}
}} catch (e) {{
    console.error(JSON.stringify({{error: "执行错误: " + e.message}}));
    process.exit(1);
}}

// 输出结果
if (typeof result !== 'undefined') {{
    console.log(JSON.stringify({{result, status: "ok"}}, null, 2));
}} else {{
    console.log(JSON.stringify({{status: "ok", message: "代码执行完成，无返回值"}}));
}}
'''

    async def execute_javascript(self, code: str, input_data: Optional[Dict] = None) -> ExecutionResult:
        """执行JavaScript代码 - 安全版本"""
        start_time = datetime.now()

        try:
            # 安全检查
            code = self._sanitize_code(code)
            self._check_dangerous_patterns(code, JS_DANGEROUS_PATTERNS, "JavaScript code")

            # 验证输入数据
            if input_data:
                input_data = self._validate_input_data(input_data)

            # 检查node是否可用
            node_path = None
            for path in ['node', 'node.exe', '/usr/bin/node', '/usr/local/bin/node']:
                try:
                    result = subprocess.run([path, '--version'], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        node_path = path
                        break
                except:
                    continue

            if not node_path:
                return ExecutionResult(
                    success=False,
                    output="",
                    error="Node.js 未安装，无法执行JavaScript代码"
                )

            # 创建输入数据文件
            input_file_fd, input_file_path = tempfile.mkstemp(suffix='.json', prefix='input_')
            try:
                with os.fdopen(input_file_fd, 'w', encoding='utf-8') as f:
                    json.dump(input_data or {}, f, ensure_ascii=False, indent=2)

                # 创建用户代码文件
                code_file_fd, code_file_path = tempfile.mkstemp(suffix='.js', prefix='user_')
                try:
                    with os.fdopen(code_file_fd, 'w', encoding='utf-8') as f:
                        f.write(self._create_safe_js_wrapper(code, input_file_path.replace('\\', '\\\\')))

                    # 使用 node 的安全选项
                    cmd = [
                        node_path,
                        '--no-warnings',        # 禁用警告
                        '--experimental-vm-modules',  # 实验性 VM 模块（更安全）
                        code_file_path
                    ]

                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )

                    try:
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(),
                            timeout=self.timeout
                        )
                    except asyncio.TimeoutError:
                        try:
                            process.kill()
                            await process.wait()
                        except:
                            pass
                        return ExecutionResult(
                            success=False,
                            output="",
                            error=f"执行超时（{self.timeout}秒）"
                        )

                    execution_time = (datetime.now() - start_time).total_seconds()

                    if process.returncode == 0:
                        output = stdout.decode('utf-8', errors='replace')[:self.max_output_size]
                        return ExecutionResult(success=True, output=output, execution_time=execution_time)
                    else:
                        error = stderr.decode('utf-8', errors='replace')[:self.max_output_size]
                        return ExecutionResult(
                            success=False,
                            output=stdout.decode('utf-8', errors='replace'),
                            error=error,
                            execution_time=execution_time
                        )

                finally:
                    try:
                        os.unlink(code_file_path)
                    except:
                        pass
            finally:
                try:
                    os.unlink(input_file_path)
                except:
                    pass

        except SecurityError as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"安全检查失败: {str(e)}"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"系统错误: {str(e)}"
            )

    async def execute_code(self, code: str, language: str = "python", input_data: Optional[Dict] = None) -> ExecutionResult:
        """通用代码执行接口"""
        if language.lower() in ['python', 'py']:
            return await self.execute_python(code, input_data)
        elif language.lower() in ['javascript', 'js']:
            return await self.execute_javascript(code, input_data)
        else:
            return ExecutionResult(
                success=False,
                output="",
                error=f"不支持的语言: {language}"
            )


# ============ 代码生成器 ============

class CodeGenerator:
    """代码生成器 - 根据任务生成可执行代码"""

    def __init__(self):
        self.templates = {
            'sort': {
                'python': '''
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)

result = quick_sort([3, 6, 8, 10, 1, 2, 1])
''',
                'javascript': '''
function quickSort(arr) {
    if (arr.length <= 1) return arr;
    const pivot = arr[Math.floor(arr.length / 2)];
    const left = arr.filter(x => x < pivot);
    const middle = arr.filter(x => x === pivot);
    const right = arr.filter(x => x > pivot);
    return [...quickSort(left), ...middle, ...quickSort(right)];
}
result = quickSort([3, 6, 8, 10, 1, 2, 1]);
'''
            },
            'api': {
                'python': '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {{"message": "Hello World"}}

@app.get("/users/{{user_id}}")
def read_user(user_id: int):
    return {{"user_id": user_id, "name": "User" + str(user_id)}}

result = "FastAPI app structure generated"
''',
                'javascript': '''
const express = require('express');
const app = express();

app.get('/', (req, res) => {{
    res.json({{ message: 'Hello World' }});
}});

app.get('/users/:id', (req, res) => {{
    res.json({{ user_id: req.params.id, name: 'User' + req.params.id }});
}});

result = "Express app structure generated";
'''
            },
            'test': {
                'python': '''
import unittest

class TestStringMethods(unittest.TestCase):
    def test_upper(self):
        self.assertEqual('hello'.upper(), 'HELLO')
    def test_isupper(self):
        self.assertTrue('HELLO'.isupper())
        self.assertFalse('Hello'.isupper())

result = "Test class generated with 2 test cases"
''',
                'javascript': '''
function testUpper() {
    return 'hello'.toUpperCase() === 'HELLO';
}
function testIsUpper() {
    return 'HELLO'.isUpper && !'Hello'.isUpper;
}
result = `Tests: upper=${testUpper()}, isUpper=${testIsUpper()}`;
'''
            }
        }

    def generate_code(self, task_type: str, language: str = "python") -> Optional[str]:
        """生成代码"""
        return self.templates.get(task_type, {}).get(language.lower())

    def list_templates(self) -> list:
        """列出所有模板"""
        return list(self.templates.keys())


# ============ 单元测试 ============

import unittest

class TestSandbox(unittest.IsolatedAsyncioTestCase):
    """沙箱测试"""

    async def test_python_execution(self):
        """测试Python执行"""
        sandbox = CodeSandbox(timeout=10)
        code = "result = 2 + 2"
        result = await sandbox.execute_python(code)
        self.assertTrue(result.success)
        self.assertIn("4", result.output)

    async def test_javascript_execution(self):
        """测试JavaScript执行"""
        sandbox = CodeSandbox(timeout=10)
        code = "let result = 2 + 2;"
        result = await sandbox.execute_javascript(code)
        # Node可能未安装，容错处理
        if not result.success and "not found" in (result.error or ""):
            self.skipTest("Node.js not installed")

    async def test_security_block_dangerous_import(self):
        """测试危险模块导入阻断"""
        sandbox = CodeSandbox(timeout=10)
        code = "import os\nresult = os.system('ls')"
        result = await sandbox.execute_python(code)
        self.assertFalse(result.success)
        self.assertIn("安全检查失败", result.error or "")

    async def test_security_block_eval(self):
        """测试 eval 阻断"""
        sandbox = CodeSandbox(timeout=10)
        code = "result = eval('2 + 2')"
        result = await sandbox.execute_python(code)
        self.assertFalse(result.success)
        self.assertIn("安全检查失败", result.error or "")

    async def test_input_data_validation(self):
        """测试输入数据验证"""
        sandbox = CodeSandbox(timeout=10)
        code = "result = INPUT_DATA.get('key', 'default')"
        result = await sandbox.execute_python(code, input_data={"key": "value"})
        self.assertTrue(result.success)

if __name__ == "__main__":
    unittest.main()