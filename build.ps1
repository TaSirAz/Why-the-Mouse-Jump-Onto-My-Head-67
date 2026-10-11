$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
    }
    & '.venv/Scripts/python.exe' -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & '.venv/Scripts/python.exe' -m PyInstaller --noconfirm --workpath build/package packaging/Naiwa.spec
    if ($LASTEXITCODE -ne 0) { throw 'Why-the-Mouse-Jump-Onto-My-Head-67 packaging failed.' }
    & './verify_build.ps1'
    Compress-Archive -LiteralPath 'dist/Why-the-Mouse-Jump-Onto-My-Head-67.exe', 'README.md', 'LICENSE', 'THIRD_PARTY.md' -DestinationPath 'dist/Why-the-Mouse-Jump-Onto-My-Head-67-Windows-x64.zip' -Force
    Write-Host 'Ready: dist/Why-the-Mouse-Jump-Onto-My-Head-67.exe and dist/Why-the-Mouse-Jump-Onto-My-Head-67-Windows-x64.zip'
} finally {
    Pop-Location
}

