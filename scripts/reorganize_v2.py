#!/usr/bin/env python3
"""按 README.md 目录结构重组所有文件"""
import shutil
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"
RUNTIME = ROOT / "runtime"

FILE_MOVES = {
    # === 核心入口 ===
    "runtime/main.py": "src/main.py",
    "runtime/server.py": "src/server.py",

    # === core/ 核心引擎 ===
    "runtime/reasoning_engine.py": "src/core/reasoning.py",
    "runtime/dream_engine.py": "src/core/dream.py",

    # === agents/ 智能体 ===
    "runtime/data_miner.py": "src/agents/data_miner.py",
    "runtime/literature_researcher.py": "src/agents/literature.py",
    "runtime/hypothesis_generator.py": "src/agents/hypothesis_gen.py",
    "runtime/hypothesis_tester.py": "src/agents/hypothesis_test.py",
    "runtime/observation_executor.py": "src/agents/observation.py",
    "runtime/discovery_tracker.py": "src/agents/discovery.py",
    "runtime/self_review.py": "src/agents/self_review.py",
    "runtime/multi_agent_coordinator.py": "src/agents/coordinator.py",
    "runtime/browser_agent.py": "src/agents/browser.py",
    "runtime/tri_agent_system.py": "src/agents/tri_agent.py",

    # === telescope/ 望远镜控制 ===
    "runtime/telescope_simulator.py": "src/telescope/simulator.py",
    "runtime/seestar_mcp_client.py": "src/telescope/seestar_client.py",
    "runtime/observation_scheduler.py": "src/telescope/scheduler.py",
    "runtime/enhanced_observation_scheduler.py": "src/telescope/enhanced_scheduler.py",
    "runtime/mqtt_telescope_bridge.py": "src/telescope/mqtt_bridge.py",

    # === astronomy/ 天文算法 ===
    "runtime/astronomy_algorithms.py": "src/astronomy/algorithms.py",
    "runtime/star_recognizer.py": "src/astronomy/star_recognizer.py",
    "runtime/astropy_fits_processor.py": "src/astronomy/fits_processor.py",
    "runtime/platesolver_wrapper.py": "src/astronomy/platesolver.py",
    "runtime/astro_analyzer.py": "src/astronomy/analyzer.py",
    "runtime/real_bogus_classifier.py": "src/astronomy/classifier.py",
    "runtime/star_catalog_manager.py": "src/astronomy/catalog_manager.py",
    "runtime/sextractor_wrapper.py": "src/astronomy/sextractor.py",

    # === observation/ 观测工作流 ===
    "runtime/embodied_observation_workflow.py": "src/observation/workflow.py",
    "runtime/realtime_observation_workflow.py": "src/observation/realtime.py",
    "runtime/realtime_data_processor.py": "src/observation/data_processor.py",
    "runtime/realtime_sky_chart.py": "src/observation/sky_chart.py",
    "runtime/auto_observatory.py": "src/observation/auto.py",
    "runtime/observation_app2.py": "src/observation/app.py",

    # === research/ 研究工具 ===
    "runtime/research_loop.py": "src/research/loop.py",
    "runtime/research_observatory_linker.py": "src/research/linker.py",

    # === data/ 数据处理 ===
    "runtime/data_models.py": "src/data/models.py",
    "runtime/data_pipeline.py": "src/data/pipeline.py",
    "runtime/data_analysis_pipeline.py": "src/data/analysis.py",
    "runtime/kepler_exoplanet_client.py": "src/data/kepler_client.py",
    "runtime/astro_data_collector.py": "src/data/collector.py",
    "runtime/astro_pipeline.py": "src/data/astro_pipeline.py",
    "runtime/weather_data_collector.py": "src/data/weather.py",

    # === memory/ 记忆系统 ===
    "runtime/vector_memory.py": "src/memory/vector.py",
    "runtime/vector_store.py": "src/memory/vector_store.py",
    "runtime/memory_persistence.py": "src/memory/persistence.py",
    "runtime/scenario_memory.py": "src/memory/scenario.py",
    "runtime/vector_rag.py": "src/memory/rag.py",

    # === learning/ 学习与进化 ===
    "runtime/rl_observation_scheduler.py": "src/learning/rl_scheduler.py",
    "runtime/overfit_self_correction.py": "src/learning/overfit_correction.py",
    "runtime/skill_tester.py": "src/learning/skill_tester.py",
    "runtime/skill_integration.py": "src/learning/skill_integration.py",

    # === web/ Web 服务 ===
    "runtime/cycle_statistics_dashboard.py": "src/web/dashboard.py",
    "runtime/realtime_bridge.py": "src/web/bridge.py",
    "runtime/session_store.py": "src/web/session.py",

    # === utils/ 工具 ===
    "runtime/runtime_logger.py": "src/utils/logger.py",
    "runtime/sandbox.py": "src/utils/sandbox.py",
    "runtime/mcp_protocol.py": "src/utils/mcp.py",
    "runtime/production_config.py": "src/utils/production.py",
    "runtime/visualization.py": "src/utils/visualization.py",
}

TEST_MOVES = {
    "runtime/tests/__init__.py": "tests/__init__.py",
    "runtime/tests/integration_test.py": "tests/integration_test.py",
    "runtime/tests/test_runtime_modules.py": "tests/test_runtime_modules.py",
    "runtime/tests/test_embodied_observation_integration.py": "tests/test_embodied.py",
    "runtime/tests/test_observation_loop_integration.py": "tests/test_observation_loop.py",
    "runtime/tests/test_nasa_tap_issue63.py": "tests/test_nasa_tap.py",
    "runtime/tests/test_ollama_integration.py": "tests/test_ollama.py",
}

DATA_MOVES = {
    "runtime/data/star_catalogs.db": "data/star_catalogs.db",
}

MODEL_MOVES = {
    "runtime/models/resnet50_astro_classifier.pth": "src/models/resnet50_astro_classifier.pth",
    "runtime/models/yolo11s_astro_detection.pt": "src/models/yolo11s_astro_detection.pt",
}

SCRIPT_MOVES = {
    "tools/browser_search.py": "scripts/tools/browser_search.py",
    "tools/download_models.sh": "scripts/tools/download_models.sh",
    "tools/multi_agent_search.py": "scripts/tools/multi_agent_search.py",
    "tools/reproduction_experiment.py": "scripts/tools/reproduction.py",
    "tools/verify_models.py": "scripts/tools/verify_models.py",
    "start_ollama_network.bat": "scripts/start_ollama_network.bat",
}

SKILL_MOVES = {
    "skills/AI-Agent.md": "docs/skills/AI-Agent.md",
    "skills/API-Design.md": "docs/skills/API-Design.md",
    "skills/Active-Learning.md": "docs/skills/Active-Learning.md",
    "skills/Architecture.md": "docs/skills/Architecture.md",
    "skills/AstroPipeline.md": "docs/skills/AstroPipeline.md",
    "skills/Backend.md": "docs/skills/Backend.md",
    "skills/CLAUDE.md": "docs/skills/CLAUDE.md",
    "skills/Cloud-Deployment.md": "docs/skills/Cloud-Deployment.md",
    "skills/Code-Review.md": "docs/skills/Code-Review.md",
    "skills/Cognitive-Engine.md": "docs/skills/Cognitive-Engine.md",
    "skills/DSA.md": "docs/skills/DSA.md",
    "skills/Data-Analysis.md": "docs/skills/Data-Analysis.md",
    "skills/Database.md": "docs/skills/Database.md",
    "skills/Debugging.md": "docs/skills/Debugging.md",
    "skills/Demo-Script.md": "docs/skills/Demo-Script.md",
    "skills/DevOps.md": "docs/skills/DevOps.md",
    "skills/Emotional-Understanding.md": "docs/skills/Emotional-Understanding.md",
    "skills/Execution-Engine.md": "docs/skills/Execution-Engine.md",
    "skills/Frontend.md": "docs/skills/Frontend.md",
    "skills/Git-Workflow.md": "docs/skills/Git-Workflow.md",
    "skills/Hermes-AGI.md": "docs/skills/Hermes-AGI.md",
    "skills/Interview-Preparation.md": "docs/skills/Interview-Preparation.md",
    "skills/Linux-Operations.md": "docs/skills/Linux-Operations.md",
    "skills/Long-Term-Memory.md": "docs/skills/Long-Term-Memory.md",
    "skills/Multimodal.md": "docs/skills/Multimodal.md",
    "skills/NodeJS-Backend.md": "docs/skills/NodeJS-Backend.md",
    "skills/PROJECT-JOURNEY.md": "docs/skills/PROJECT-JOURNEY.md",
    "skills/Planning-Engine.md": "docs/skills/Planning-Engine.md",
    "skills/Product-Manager.md": "docs/skills/Product-Manager.md",
    "skills/Product.md": "docs/skills/Product.md",
    "skills/Project-Management.md": "docs/skills/Project-Management.md",
    "skills/Prompt-Engineering.md": "docs/skills/Prompt-Engineering.md",
    "skills/Python-Backend.md": "docs/skills/Python-Backend.md",
    "skills/React.md": "docs/skills/React.md",
    "skills/Reasoning.md": "docs/skills/Reasoning.md",
    "skills/Refactoring.md": "docs/skills/Refactoring.md",
    "skills/Resume-Optimization.md": "docs/skills/Resume-Optimization.md",
    "skills/Security.md": "docs/skills/Security.md",
    "skills/Self-Evolution.md": "docs/skills/Self-Evolution.md",
    "skills/Skill-Creation-Guide.md": "docs/skills/Skill-Creation-Guide.md",
    "skills/Tester.md": "docs/skills/Tester.md",
    "skills/Testing.md": "docs/skills/Testing.md",
    "skills/Tianwen-AGI.md": "docs/skills/Tianwen-AGI.md",
    "skills/Tool-Usage.md": "docs/skills/Tool-Usage.md",
    "skills/UI-Visual.md": "docs/skills/UI-Visual.md",
    "skills/WeChat-MiniProgram.md": "docs/skills/WeChat-MiniProgram.md",
}

CLOUDFLARE_MOVES = {
    "functions/api/[[path]].js": "deploy/cloudflare/functions/api/[[path]].js",
    "workers/api-proxy.js": "deploy/cloudflare/api-proxy.js",
}


def create_dirs():
    dirs = set()
    all_moves = {}
    all_moves.update(FILE_MOVES)
    all_moves.update(TEST_MOVES)
    all_moves.update(DATA_MOVES)
    all_moves.update(MODEL_MOVES)
    all_moves.update(SCRIPT_MOVES)
    all_moves.update(SKILL_MOVES)
    all_moves.update(CLOUDFLARE_MOVES)

    for dst in all_moves.values():
        d = (ROOT / dst).parent
        dirs.add(d)

    for d in sorted(dirs):
        d.mkdir(parents=True, exist_ok=True)
        print(f"  MKDIR {d.relative_to(ROOT)}")

    print(f"  创建了 {len(dirs)} 个目录")


def move_files(moves, label):
    count = 0
    for src_rel, dst_rel in moves.items():
        src = ROOT / src_rel
        dst = ROOT / dst_rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            print(f"  MOVE {src_rel} -> {dst_rel}")
            count += 1
        else:
            print(f"  SKIP {src_rel} (不存在)")
    print(f"  [{label}] 移动了 {count} 个文件")
    return count


def main():
    print("=" * 60)
    print("  天问-AGI 按 README.md 目录结构重组")
    print("=" * 60)
    print()

    create_dirs()

    total = 0
    total += move_files(FILE_MOVES, "核心源码")
    total += move_files(TEST_MOVES, "测试文件")
    total += move_files(DATA_MOVES, "数据文件")
    total += move_files(MODEL_MOVES, "模型文件")
    total += move_files(SCRIPT_MOVES, "工具脚本")
    total += move_files(SKILL_MOVES, "技能文档")
    total += move_files(CLOUDFLARE_MOVES, "Cloudflare")

    # 移动 requirements.txt 到根目录
    req_src = RUNTIME / "requirements.txt"
    req_dst = ROOT / "requirements.txt"
    if req_src.exists():
        shutil.move(str(req_src), str(req_dst))
        print(f"  MOVE runtime/requirements.txt -> requirements.txt")
        total += 1

    print()
    print(f"  总计移动了 {total} 个文件")
    print("=" * 60)


if __name__ == "__main__":
    main()
