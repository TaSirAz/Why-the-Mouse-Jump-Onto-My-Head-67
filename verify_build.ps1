param([string]$Executable = 'dist/Why-the-Mouse-Jump-Onto-My-Head-67.exe')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $naiwaExecutable = (Resolve-Path -LiteralPath $Executable).Path
    $naiwaReportDir = Join-Path $PSScriptRoot 'verification'
    New-Item -ItemType Directory -Path $naiwaReportDir -Force | Out-Null
    $naiwaReport = Join-Path $naiwaReportDir ('startup-' + [guid]::NewGuid().ToString('N') + '.json')
    $naiwaProcess = Start-Process -FilePath $naiwaExecutable -ArgumentList ('--verify-startup-report "' + $naiwaReport + '"') -WindowStyle Hidden -PassThru
    if (-not $naiwaProcess.WaitForExit(25000)) {
        & taskkill.exe /PID $naiwaProcess.Id /T /F *> $null
        throw 'Packaged application did not finish its startup check within 25 seconds.'
    }
    if (-not (Test-Path -LiteralPath $naiwaReport)) {
        throw 'Packaged application failed before writing its startup report.'
    }
    $naiwaResult = Get-Content -LiteralPath $naiwaReport -Raw | ConvertFrom-Json
    if (-not $naiwaResult.ok -or $naiwaProcess.ExitCode -ne 0) {
        throw ('Packaged application startup failed: ' + $naiwaResult.error)
    }
    Write-Host ('Packaged startup passed: Qt ' + $naiwaResult.qt + ', pet rendering, control room and window detection.')
} finally {
    Pop-Location
}

