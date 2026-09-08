param(
    [Parameter(Mandatory=$true)][string]$JobDir,
    [Parameter(Mandatory=$true)][ValidateSet('inspect','trace','rebuild','verify','live')][string]$Stage
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This launcher requires Windows with desktop Illustrator.' }
$jobPath = (Resolve-Path -LiteralPath $JobDir).Path
$scriptPath = Join-Path $jobPath ($Stage + '.jsx')
if (-not (Test-Path -LiteralPath $scriptPath)) { throw "Prepare the job first. Missing: $scriptPath" }
$logPath = Join-Path $jobPath ($Stage + '.log')
$started = Get-Date
# Illustrator must be installed for this user in an interactive desktop session.
$illustratorApp = New-Object -ComObject Illustrator.Application
try {
    $illustratorApp.DoJavaScriptFile($scriptPath)
    if (-not (Test-Path -LiteralPath $logPath)) { throw 'Illustrator did not produce a stage log.' }
    if ((Get-Item -LiteralPath $logPath).LastWriteTime -lt $started.AddSeconds(-2)) { throw 'Stage log is stale.' }
    $result = Get-Content -LiteralPath $logPath -Encoding UTF8
    $result | Write-Output
    if ($result -match '^ERROR:' -or $result[-1] -ne 'DONE') { throw 'Illustrator stage failed; inspect the log.' }
} finally {
    # Release this COM handle; keep Illustrator and all user documents open.
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($illustratorApp)
}
