$ErrorActionPreference = "Continue"
$root = "f:\tianwen-agi"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Tianwen-AGI Full Reorganization" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Phase 1: Root cleanup
Write-Host ""
Write-Host "[Phase 1] Root directory cleanup" -ForegroundColor Yellow

$rootMoves = @{
    "tools" = @(
        "browser_search.py",
        "multi_agent_search.py",
        "reproduction_experiment.py",
        "verify_models.py",
        "download_models.sh"
    )
    "runtime\tests" = @(
        "test_nasa_tap_issue63.py",
        "test_ollama_integration.py"
    )
    "docs\PRO\04-hermes-pm" = @(
        "issue_26_27_pm_review.md",
        "issue_28_29_pm_review_summary.md",
        "issue_23_30_pm_review.md"
    )
}

foreach ($destDir in $rootMoves.Keys) {
    $dest = Join-Path $root $destDir
    if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
    foreach ($file in $rootMoves[$destDir]) {
        $src = Join-Path $root $file
        if (Test-Path $src) {
            Move-Item -Path $src -Destination (Join-Path $dest $file) -Force
            Write-Host "  [OK] $file -> $destDir\" -ForegroundColor Green
        } else {
            Write-Host "  [SKIP] $file (not found)" -ForegroundColor Gray
        }
    }
}

# Phase 2: docs/ root cleanup
Write-Host ""
Write-Host "[Phase 2] docs/ root file classification" -ForegroundColor Yellow

$docsMoves = @{
    "docs\models" = @(
        "LLM_MODEL_ARCHITECTURE_RESEARCH.md",
        "QWEN3_THEATRICAL_AI_RESEARCH.md"
    )
    "docs\reports" = @(
        "MCP_SERVER_ORCHESTRATION.md",
        "MULTI_AGENT_ROLE_SYSTEMS.md",
        "OPTIMIZATION_WORK_REPORT_20260503.md",
        "PROJECT_ANALYSIS_REPORT_20260503.md",
        "STARWHISPER_HARDWARE_REPORT.md",
        "STARWHISPER_NINA_CODEBASE_ANALYSIS.md",
        "STARWHISPER_REPRODUCTION_PLAN.md"
    )
    "docs\deploy" = @(
        "PRECOMMIT_GUIDE.md"
    )
    "docs\PRO\07-tech-analysis" = @(
        "vector_memory_semantic_search_PRO.md"
    )
}

foreach ($destDir in $docsMoves.Keys) {
    $dest = Join-Path $root $destDir
    if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
    foreach ($file in $docsMoves[$destDir]) {
        $src = Join-Path $root "docs\$file"
        if (Test-Path $src) {
            Move-Item -Path $src -Destination (Join-Path $dest $file) -Force
            Write-Host "  [OK] docs/$file -> $destDir\" -ForegroundColor Green
        } else {
            Write-Host "  [SKIP] docs/$file (not found)" -ForegroundColor Gray
        }
    }
}

# Phase 3: Split docs/issue-replies/ into PRO and non-PRO
Write-Host ""
Write-Host "[Phase 3] Split docs/issue-replies/" -ForegroundColor Yellow

$issueDir = Join-Path $root "docs\issue-replies"
$proIssueDir = Join-Path $root "docs\PRO\05-issue-replies"
$issuesDir = Join-Path $root "docs\issues"

if (-not (Test-Path $proIssueDir)) { New-Item -ItemType Directory -Path $proIssueDir -Force | Out-Null }
if (-not (Test-Path $issuesDir)) { New-Item -ItemType Directory -Path $issuesDir -Force | Out-Null }

if (Test-Path $issueDir) {
    Get-ChildItem -Path $issueDir -File | ForEach-Object {
        $file = $_.Name
        $src = $_.FullName
        if ($file -like "PRO_*") {
            Move-Item -Path $src -Destination (Join-Path $proIssueDir $file) -Force
            Write-Host "  [PRO] $file -> docs/PRO/05-issue-replies/" -ForegroundColor Magenta
        } else {
            Move-Item -Path $src -Destination (Join-Path $issuesDir $file) -Force
            Write-Host "  [ISSUE] $file -> docs/issues/" -ForegroundColor Green
        }
    }
    $remaining = Get-ChildItem -Path $issueDir -File
    if ($remaining.Count -eq 0) {
        Remove-Item -Path $issueDir -Force -Recurse
        Write-Host "  [CLEAN] Removed empty docs/issue-replies/" -ForegroundColor Gray
    }
}

# Phase 4: Remove old organize scripts
Write-Host ""
Write-Host "[Phase 4] Remove old scripts" -ForegroundColor Yellow

$oldScripts = @("organize_all_files.ps1", "organize_docs_root.ps1")
foreach ($s in $oldScripts) {
    $sp = Join-Path $root "tools\$s"
    if (Test-Path $sp) {
        Remove-Item -Path $sp -Force
        Write-Host "  [DEL] tools/$s (replaced by this script)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Reorganization Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
