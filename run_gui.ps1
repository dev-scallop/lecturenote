# Run GUI with repository .venv python
# Usage: PowerShell에서 이 파일을 실행하면 `.venv`에 있는 python으로 `scripts/gui_extract.py`를 실행합니다.

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
$script = Join-Path $repoRoot "scripts\gui_extract.py"

if (-not (Test-Path $py)) {
    Write-Error ".venv python을 찾을 수 없습니다. 먼저 다음을 실행하세요: `py -3.11-64 -m venv .venv` 그리고 `.venv\Scripts\python.exe -m pip install -r requirements.txt` 또는 `pip install PyMuPDF`"
    exit 1
}

Write-Output "Using: $py"
& $py $script
