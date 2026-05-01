"""
Ollama集成测试脚本
测试Tianwen-AGI与本地Ollama的集成
"""
import os
import sys
import asyncio
import httpx

# Ollama配置
OLLAMA_PATH = r"C:\Users\22140\AppData\Local\Programs\Ollama"
OLLAMA_ENDPOINT = "http://localhost:11434"

def check_ollama_server():
    """检查Ollama服务是否运行"""
    try:
        response = httpx.get(f"{OLLAMA_ENDPOINT}/", timeout=5.0)
        return response.status_code == 200
    except:
        return False

def check_ollama_executable():
    """检查Ollama可执行文件是否存在"""
    ollama_exe = os.path.join(OLLAMA_PATH, "ollama.exe")
    return os.path.exists(ollama_exe)

async def test_ollama_chat(model_name: str, prompt: str):
    """测试Ollama chat API"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_ENDPOINT}/api/generate",
                json={"model": model_name, "prompt": prompt, "stream": False}
            )
            if response.status_code == 200:
                return response.json().get("response", "No response")
            else:
                return f"Error: {response.status_code}"
    except Exception as e:
        return f"Exception: {str(e)}"

async def main():
    print("=" * 50)
    print("Tianwen-AGI Ollama集成测试")
    print("=" * 50)

    # 1. 检查Ollama可执行文件
    print("\n[1] 检查Ollama安装...")
    if check_ollama_executable():
        print(f"    ✓ Ollama已安装在: {OLLAMA_PATH}")
    else:
        print(f"    ✗ Ollama未找到: {OLLAMA_PATH}")
        return

    # 2. 检查Ollama服务
    print("\n[2] 检查Ollama服务...")
    if check_ollama_server():
        print("    ✓ Ollama服务正在运行 (http://localhost:11434)")
    else:
        print("    ✗ Ollama服务未运行，尝试启动...")
        # 尝试启动Ollama服务
        os.system(f'start "" "{OLLAMA_PATH}\\ollama.exe" "serve"')
        await asyncio.sleep(3)
        if check_ollama_server():
            print("    ✓ Ollama服务已启动")
        else:
            print("    ✗ 无法启动Ollama服务")
            return

    # 3. 检查已安装的模型
    print("\n[3] 检查已安装的模型...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_ENDPOINT}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                if models:
                    print(f"    已安装 {len(models)} 个模型:")
                    for m in models:
                        print(f"      - {m.get('name', 'unknown')} ({m.get('size', 0)//1024//1024}MB)")
                else:
                    print("    ⚠ 没有已安装的模型")
                    print("    请运行: ollama pull llama3.2:1b")
            else:
                print(f"    ✗ 获取模型列表失败: {response.status_code}")
    except Exception as e:
        print(f"    ✗ 错误: {e}")

    # 4. 测试模型推理
    print("\n[4] 测试模型推理...")
    test_models = ["llama3.2:1b", "llama3.2:3b", "llama3:1b", "qwen2.5:3b", "mistral"]
    for model in test_models:
        print(f"\n    测试 {model}...")
        result = await test_ollama_chat(model, "What is 2+2? Keep it brief.")
        if "Error" in result or "Exception" in result:
            print(f"      ✗ {model} 不可用")
        else:
            print(f"      ✓ {model} 响应: {result[:80]}...")

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())