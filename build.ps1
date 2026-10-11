$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
    }
    & '.venv/Scripts/python.exe' -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & '.venv/Scripts/python.exe' -m PyInstaller --noconfirm --clean --onefile --windowed --name Naiwa --icon assets/naiwa.ico --add-data 'assets;assets' naiwa.py
    if ($LASTEXITCODE -ne 0) { throw 'Naiwa packaging failed.' }
    Compress-Archive -LiteralPath 'dist/Naiwa.exe', 'README.md', 'LICENSE', 'THIRD_PARTY.md' -DestinationPath 'dist/Naiwa-Windows-x64.zip' -Force
    Write-Host 'Ready: dist/Naiwa.exe and dist/Naiwa-Windows-x64.zip'
} finally {
    Pop-Location
}
