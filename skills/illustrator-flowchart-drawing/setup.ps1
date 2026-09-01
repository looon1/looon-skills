#requires -Version 5.1

[CmdletBinding()]
param(
    [switch]$VerifyServer,
    [string]$SshTarget = "supersvg-server",
    [string]$RemoteRoot = "services/supersvg-eval",
    [int]$GpuIndex = 1
)

$ErrorActionPreference = "Stop"
$skillRoot = Split-Path $MyInvocation.MyCommand.Path -Parent
$managedPython = Join-Path $skillRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $managedPython -PathType Leaf)) {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        & $launcher.Source -3 -m venv (Join-Path $skillRoot '.venv')
    } else {
        & (Get-Command python -ErrorAction Stop).Source -m venv (Join-Path $skillRoot '.venv')
    }
}
& $managedPython -m pip install --upgrade pip
& $managedPython -m pip install -r (Join-Path $skillRoot 'requirements.txt')
$doctorArguments = @((Join-Path $skillRoot 'doctor.py'), '--ssh-target', $SshTarget, '--remote-root', $RemoteRoot, '--gpu-index', [string]$GpuIndex)
if ($VerifyServer) { $doctorArguments += '--verify-server' }
& $managedPython @doctorArguments
exit $LASTEXITCODE
