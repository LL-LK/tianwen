$ErrorActionPreference = "Stop"
$root = "f:\tianwen-agi"
$proDir = "$root\docs\PRO"

Write-Host "=== 1. 移动根目录 PRO_*.md 到 docs/PRO/ 子目录 ==="

$rootProMoves = @{
    "03-audit-review" = @(
        "PRO_ACCEPTANCE_CRITIQUE_REPORT_20260501.md",
        "PRO_AUDIT_P0_ASTRONOMICAL_AGI.md",
        "PRO_AUDIT_P0_EMBODIED_AI_OBSERVATORY.md",
        "PRO_AUDIT_V381_20260501.md",
        "PRO_SUGGESTION_CHECK_REPORT_20260501.md"
    )
    "01-strategic-analysis" = @(
        "PRO_ASTRONOMICAL_THEATER_DEEPTHINK_20260501.md"
    )
    "05-issue-replies" = @(
        "PRO_HERMES_P0_AUDIT_REPLY_ISSUE15_20260501.md",
        "PRO_HERMES_REPLY_ISSUE13_20260501.md",
        "PRO_HERMES_REPLY_ISSUE17_20260501.md",
        "PRO_HERMES_REPLY_ISSUE22_20260501.md"
    )
    "04-hermes-pm" = @(
        "PRO_HERMES_PM_REVIEW_20260501_225812.md",
        "PRO_HERMES_PM_REVIEW_ISSUE_23_26_27_28_29_30_20260501_2207_CST.md",
        "PRO_HERMES_REVIEW_ISSUE13_20260501_1547.md",
        "PRO_HERMES_REVIEW_ISSUE16_20260501_1548.md",
        "PRO_HERMES_REVIEW_ISSUE17_20260501_1550.md",
        "PRO_HERMES_REVIEW_ISSUE30_20260501_1604.md",
        "PRO_HERMES_REVIEW_ISSUE35_20260501_1608.md",
        "PRO_HERMES_REVIEW_ISSUE38_20260501_1628.md"
    )
    "06-project-management" = @(
        "PRO_ISSUE36_THEATER_OPTIMIZATION_20260501.md",
        "PRO_SYNC_V371_OPTIMIZATION_20260501.md",
        "PRO_SYNC_V372_COMPLETION_20260501.md",
        "PRO_SYNC_V373_ENV_FIX_20260501.md"
    )
    "08-work-report" = @(
        "PRO_LOOP_COMPLETION_REPORT_20260503.md",
        "PRO_WORK_COMPLETION_REPORT_V385_20260503.md",
        "PRO_WORK_REPORT_20260501.md",
        "PRO_WORK_REPORT_20260503_2000.md",
        "PRO_WORK_REPORT_ISSUE_ANALYSIS_20260503.md",
        "PRO_WORK_REPORT_V383_TRAE_20260503.md",
        "PRO_WORK_STATUS_SUMMARY_ISSUE30_20260501.md"
    )
    "07-tech-analysis" = @(
        "PRO_RAG_MCP_OPTIMIZATION_20260503.md"
    )
    "09-version-report" = @(
        "PRO_V380_COMPLETION_20260501.md",
        "PRO_V382_OLLAMA_20260501.md"
    )
}

foreach ($subdir in $rootProMoves.Keys) {
    $dest = "$proDir\$subdir"
    if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
    foreach ($file in $rootProMoves[$subdir]) {
        $src = "$root\$file"
        if (Test-Path $src) {
            Move-Item -Path $src -Destination "$dest\$file" -Force
            Write-Host "  Moved: $file -> docs/PRO/$subdir/"
        }
    }
}

Write-Host ""
Write-Host "=== 2. 移动根目录研究文档到 docs/ ==="

$rootDocMoves = @(
    "LLM_MODEL_ARCHITECTURE_RESEARCH.md",
    "MCP_SERVER_ORCHESTRATION.md",
    "MULTI_AGENT_ROLE_SYSTEMS.md",
    "OPTIMIZATION_WORK_REPORT_20260503.md",
    "PRECOMMIT_GUIDE.md",
    "PROJECT_ANALYSIS_REPORT_20260503.md",
    "QWEN3_THEATRICAL_AI_RESEARCH.md",
    "STARWHISPER_HARDWARE_REPORT.md",
    "STARWHISPER_NINA_CODEBASE_ANALYSIS.md",
    "STARWHISPER_REPRODUCTION_PLAN.md"
)

$docsDir = "$root\docs"
foreach ($file in $rootDocMoves) {
    $src = "$root\$file"
    if (Test-Path $src) {
        Move-Item -Path $src -Destination "$docsDir\$file" -Force
        Write-Host "  Moved: $file -> docs/"
    }
}

Write-Host ""
Write-Host "=== 3. 删除 docs/PRO/ 根目录重复文件（已在子目录中） ==="

$proRootDuplicates = @(
    "PRO_AGI_EMBODIED_JINWU_RESEARCH_20260501.md",
    "PRO_ALL_ISSUES_REPLIES_20260501.md",
    "PRO_ALL_ISSUES_SUMMARY_20260501.md",
    "PRO_ASTRONOMICAL_AI_COMPARISON.md",
    "PRO_ASTRONOMICAL_LLM_COMPLETENESS_20260501.md",
    "PRO_AUDIT_P0_1_DATA_MINER_KEPLER.md",
    "PRO_AUDIT_P0_2_OBSERVATORY_LINKER_SEESTAR.md",
    "PRO_AUDIT_P0_3_OLLAMA_LOCAL_LLM.md",
    "PRO_AUDIT_P1_1_4AGENT_TO_3AGENT.md",
    "PRO_AUDIT_P1_2_CHROMADB_RAG.md",
    "PRO_AUDIT_P1_3_ASTROPT_INTEGRATION.md",
    "PRO_AUDIT_P2_1_VLLM_INFERENCE.md",
    "PRO_AUDIT_P2_2_ASCOM_VOXPOSER.md",
    "PRO_AUTO_OBSERVATORY_FRONTEND_BACKEND_ANALYSIS_20260502.md",
    "PRO_BROWSER_SIMULATION_MULTIAGENT_20260501.md",
    "PRO_CLAUDE_AUDIT_ISSUE30.md",
    "PRO_CLAUDE_DEEPTHINK_ISSUE18.md",
    "PRO_CLAUDE_DEEPTHINK_ISSUE20.md",
    "PRO_CLAUDE_DEEPTHINK_ISSUE21.md",
    "PRO_CLAUDE_DEEPTHINK_ISSUE29.md",
    "PRO_CLAUDE_DEEPTHINK_ISSUE31.md",
    "PRO_CLAUDE_RESEARCH_ISSUE26.md",
    "PRO_CLAUDE_RESEARCH_ISSUE27.md",
    "PRO_CLAUDE_RESEARCH_ISSUE28.md",
    "PRO_COMPETITION_ANALYSIS.md",
    "PRO_DATA_ANALYSIS_FULL_STACK.md",
    "PRO_DEEPTHINK_EMBODIED_AI_RELIABILITY_20260501.md",
    "PRO_DEEPTHINK_INDEPENDENT_LOOP_20260501.md",
    "PRO_DISCUSSION42_FIX_REPORT_20260501.md",
    "PRO_EMBODIED_AI_ANALYSIS_20260501.md",
    "PRO_HERMES_AUDIT_20260501_1246.md",
    "PRO_HERMES_PM_REVIEW_ISSUE50_20260501_2311.md",
    "PRO_HERMES_REPLY_ISSUE33_20260501_2211.md",
    "PRO_HERMES_REPLY_ISSUE34_20260501_2211.md",
    "PRO_HERMES_REPLY_ISSUE36_20260501_2211.md",
    "PRO_HERMES_REPLY_ISSUE36_20260502_2258.md",
    "PRO_HERMES_REPLY_ISSUE37_20260501_2211.md",
    "PRO_HERMES_REPLY_ISSUE38_20260501_2211.md",
    "PRO_HERMES_REPLY_ISSUE38_20260502_2258.md",
    "PRO_HERMES_REPLY_ISSUE39_20260501_2211.md",
    "PRO_HERMES_REPLY_ISSUE39_20260502_2258.md",
    "PRO_HERMES_REPLY_ISSUE40_20260501_2211.md",
    "PRO_HERMES_REPLY_SUMMARY_20260501.md",
    "PRO_HERMES_REVIEW_20260501.md",
    "PRO_HERMES_REVIEW_20260501_1017.md",
    "PRO_HERMES_REVIEW_20260501_1031.md",
    "PRO_HERMES_REVIEW_20260501_1205.md",
    "PRO_HERMES_REVIEW_ISSUE25_REPLY_20260501.md",
    "PRO_HERMES_REVIEW_ISSUE32_20260501_1625.md",
    "PRO_HERMES_REVIEW_ISSUE39_20260502_0037.md",
    "PRO_HERMES_SUMMARY_20260501.md",
    "PRO_INCOMPLETE_WORK_EVALUATION_V2.md",
    "PRO_INTEGRATION_ANALYSIS_20260501.md",
    "PRO_ISSUE11_HERMES_REPLY_20260501.md",
    "PRO_ISSUE14_HERMES_REPLY_20260501.md",
    "PRO_ISSUE19_HERMES_REPLY_20260501.md",
    "PRO_ISSUE22_HERMES_REPLY_20260501.md",
    "PRO_ISSUE4_HERMES_REPLY_20260501.md",
    "PRO_KEPLER_NASA_TAP_20260501.md",
    "PRO_LITERATURE_OBSERVATION_LOOP_20260501.md",
    "PRO_MULTI_MODEL_BALL_INTERACTION_20260501.md",
    "PRO_OLLAMA_INTEGRATION_20260501.md",
    "PRO_OPTIMIZE_AGENT_RUNTIME_20260501.md",
    "PRO_OPTIMIZE_DATA_MINING_20260501.md",
    "PRO_OPTIMIZE_MULTI_AGENT_20260501.md",
    "PRO_OPTIMIZE_SELF_EVOLUTION_20260501.md",
    "PRO_OVERFITTING_MULTIAGENT_ANALYSIS.md",
    "PRO_REPOSITORY_FILE_ORGANIZATION_20260501.md",
    "PRO_V360_COMPLETION_20260501.md",
    "PRO_V370_PLANNING_20260501.md",
    "PRO_WORK_REPORT_ALL_ISSUES_20260501_2258.md",
    "PRO_WORK_REPORT_ALL_ISSUES_20260501_2320.md"
)

foreach ($file in $proRootDuplicates) {
    $path = "$proDir\$file"
    if (Test-Path $path) {
        Remove-Item -Path $path -Force
        Write-Host "  Deleted duplicate: docs/PRO/$file"
    }
}

Write-Host ""
Write-Host "=== 4. 移动 docs/PRO/ 根目录新文件到子目录 ==="

$proNewMoves = @{
    "06-project-management" = @(
        "PRO_ARCH_REFACTOR_REPORT_20260503.md",
        "PRO_OFFLINE_AUTO_TELESCOPE_PLAN_20260503.md"
    )
    "01-strategic-analysis" = @(
        "PRO_DISCUSSION_DEEPTHINK_DEFICIENCY_20260503.md"
    )
    "04-hermes-pm" = @(
        "PRO_PM_REVIEW_COMPREHENSIVE_20260503_1910.md"
    )
    "03-audit-review" = @(
        "PRO_SECURITY_AUDIT_RAILWAY_20260503.md"
    )
}

foreach ($subdir in $proNewMoves.Keys) {
    $dest = "$proDir\$subdir"
    if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
    foreach ($file in $proNewMoves[$subdir]) {
        $src = "$proDir\$file"
        if (Test-Path $src) {
            Move-Item -Path $src -Destination "$dest\$file" -Force
            Write-Host "  Moved: $file -> docs/PRO/$subdir/"
        }
    }
}

Write-Host ""
Write-Host "=== 5. 移动 docs/ARCH_REFACTOR_PLAN_20260503.md 到 docs/PRO/06-project-management/ ==="

$archRefactor = "$docsDir\ARCH_REFACTOR_PLAN_20260503.md"
if (Test-Path $archRefactor) {
    Move-Item -Path $archRefactor -Destination "$proDir\06-project-management\ARCH_REFACTOR_PLAN_20260503.md" -Force
    Write-Host "  Moved: ARCH_REFACTOR_PLAN_20260503.md -> docs/PRO/06-project-management/"
}

Write-Host ""
Write-Host "=== 整理完成 ==="
