"""
Hermes-AGI Code Sandbox
代码执行沙箱 - 支持Python和JavaScript的实际执行
"""

import asyncio
import subprocess
import tempfile
import os
import json
import signal
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: float = 0
    memory_usage: Optional[str] = None

class CodeSandbox:
    """代码执行沙箱"""

    def __init__(self, timeout: int = 30, max_output_size: int = 10000):
        self.timeout = timeout  # 超时秒数
        self.max_output_size = max_output_size

    async def execute_python(self, code: str, input_data: Optional[Dict] = None) -> ExecutionResult:
        """执行Python代码"""
        start_time = datetime.now()

        # 准备输入
        input_json = json.dumps(input_data or {}, ensure_ascii=False)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            # 包装代码，添加输入处理
            wrapped_code = f'''
import sys
import json
import traceback

# 输入数据
INPUT_DATA = json.loads('{input_json}')

# 用户代码
{code}

# 输出结果
if 'result' in dir():
    print(json.dumps({{"result": result, "status": "ok"}}, ensure_ascii=False, indent=2))
'''
            f.write(wrapped_code)
            temp_file = f.name

        try:
            # 执行代码
            process = await asyncio.create_subprocess_exec(
                sys.executable, temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
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
                return ExecutionResult(success=False, output=stdout.decode('utf-8', errors='replace'), error=error, execution_time=execution_time)

        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e)
            )
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass

    async def execute_javascript(self, code: str, input_data: Optional[Dict] = None) -> ExecutionResult:
        """执行JavaScript代码"""
        start_time = datetime.now()

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

        input_json = json.dumps(input_data or {}, ensure_ascii=False)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
            wrapped_code = f'''
const INPUT_DATA = JSON.parse('{input_json.replace("'", "\\'")}');

// 用户代码
{code}

// 输出结果
if (typeof result !== 'undefined') {{
    console.log(JSON.stringify({{result, status: "ok"}}, null, 2));
}}
'''
            f.write(wrapped_code)
            temp_file = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                node_path, temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
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
                return ExecutionResult(success=False, output=stdout.decode('utf-8', errors='replace'), error=error, execution_time=execution_time)

        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e)
            )
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass

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

if __name__ == "__main__":
    unittest.main()