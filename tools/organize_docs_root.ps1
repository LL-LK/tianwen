$docs = "f:\tianwen-agi\docs"
$pro = "$docs\PRO"

$moves = @{
    "05-issue-replies" = @("PRO_ISSUE11_HERMES_REPLY_20260501.md","PRO_ISSUE12_HERMES_REPLY_20260501.md","PRO_ISSUE17_HERMES_REPLY_20260501.md","PRO_ISSUE18_HERMES_REPLY_20260501.md","PRO_ISSUE1_HERMES_REPLY_20260501.md","PRO_ISSUE20_HERMES_REPLY_20260501.md","PRO_ISSUE9_HERMES_REPLY_20260501.md")
    "07-tech-analysis" = @("PRO_CLOSED_LOOP_ANALYSIS_20260503.md","PRO_TECH_ROUTE_COMPARISON_20260503.md")
}

foreach ($subdir in $moves.Keys) {
    foreach ($file in $moves[$subdir]) {
        $src = Join-Path $docs $file
        $dest = Join-Path $pro "$subdir\$file"
        if (Test-Path $src) {
            Move-Item -Path $src -Destination $dest -Force
            Write-Host "Moved: $file -> docs/PRO/$subdir/"
        }
    }
}
Write-Host "Done."
