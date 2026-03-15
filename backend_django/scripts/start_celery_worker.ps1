$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
Set-Location $ProjectDir

if (-not $env:DJANGO_ENV) {
    $env:DJANGO_ENV = "dev"
}

$CeleryBin = Join-Path $ProjectDir "..\\venv\\Scripts\\celery.exe"
if (-not (Test-Path $CeleryBin)) {
    $CeleryBin = "celery"
}

& $CeleryBin -A config worker -l info --pool=solo
