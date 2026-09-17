param(
    [Parameter(Mandatory=$true)][string]$JobDir,
    [Parameter(Mandatory=$true)][ValidateSet('inspect','trace','rebuild','structure','compose','export','verify','live')][string]$Stage,
    [switch]$Start,
    [ValidateRange(0,2147483647)][int]$MaxBatches = 0
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This launcher requires Windows with desktop Illustrator.' }
$jobPath = (Resolve-Path -LiteralPath $JobDir).Path
$scriptPath = Join-Path $jobPath ($Stage + '.jsx')
if (-not (Test-Path -LiteralPath $scriptPath)) { throw "Prepare the job first. Missing: $scriptPath" }
$logPath = Join-Path $jobPath ($Stage + '.log')
$started = Get-Date
$config = Get-Content -LiteralPath (Join-Path $jobPath 'job.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$mutex = New-Object System.Threading.Mutex($false, ('LooonIllustrator-' + $config.fingerprint))
if (-not $mutex.WaitOne(0)) { $mutex.Dispose(); throw 'Another runner owns this job.' }
# Illustrator must be installed for this user in an interactive desktop session.
$illustratorApp = $null
try {
    $illustratorApp = New-Object -ComObject Illustrator.Application
    $illustratorApp.DoJavaScriptFile($scriptPath)
    if (-not (Test-Path -LiteralPath $logPath)) { throw 'Illustrator did not produce a stage log.' }
    if ((Get-Item -LiteralPath $logPath).LastWriteTime -lt $started.AddSeconds(-2)) { throw 'Stage log is stale.' }
    $result = Get-Content -LiteralPath $logPath -Encoding UTF8
    $result | Write-Output
    if ($result -match '^ERROR:') { throw 'Illustrator stage failed; inspect the log.' }
    if ($Stage -eq 'live') {
        if ($result[-1] -eq 'DONE') { return }
        if (-not ($result -match '^READY')) { throw 'Live controller did not become ready.' }
        $planPath = Join-Path $jobPath 'live-plan.txt'
        $cursorPath = Join-Path $jobPath 'live-cursor.txt'
        $commandPath = Join-Path $jobPath 'live-command.txt'
        $batchFiles = @(Get-Content -LiteralPath $planPath -Encoding UTF8)
        Write-Output 'Ready. In Illustrator click Start / Resume; Pause and Step remain available.'
        if ($Start) { Set-Content -LiteralPath $commandPath -Value 'play' -Encoding ASCII -NoNewline }
        $completedThisRun = 0
        while ($true) {
            $batchIndex = [int](Get-Content -LiteralPath $cursorPath -Raw)
            if ($batchIndex -eq $batchFiles.Count) {
                if (-not ((Get-Content -LiteralPath $logPath) -contains 'DONE')) { throw 'Missing final DONE.' }
                Write-Output 'DONE'
                break
            }
            $command = (Get-Content -LiteralPath $commandPath -Raw).Trim()
            if ($command -eq 'stop') { Write-Output 'Stopped; partial document remains open.'; break }
            if ($command -ne 'play' -and $command -ne 'step') { Start-Sleep -Milliseconds 100; continue }
            if ($command -eq 'step') { Set-Content -LiteralPath $commandPath -Value 'pause' -Encoding ASCII -NoNewline }
            $batchPath = [Uri]::UnescapeDataString($batchFiles[$batchIndex])
            $illustratorApp.DoJavaScriptFile($batchPath)
            if ([int](Get-Content -LiteralPath $cursorPath -Raw) -ne ($batchIndex + 1)) { throw 'Batch interrupted; restart live to reconcile completed objects.' }
            Write-Output ('Batch {0}/{1}' -f ($batchIndex + 1), $batchFiles.Count)
            # Wait outside Illustrator so its native event loop can paint and respond.
            $completedThisRun++
            if ($MaxBatches -gt 0 -and $completedThisRun -ge $MaxBatches) { Set-Content -LiteralPath $commandPath -Value 'pause' -Encoding ASCII -NoNewline; break }
            Start-Sleep -Milliseconds $config.playback.delay_ms
        }
    } elseif ($result[-1] -ne 'DONE') { throw 'Illustrator stage incomplete; inspect the log.' }
} catch {
    if ($Stage -eq 'live' -and (Test-Path -LiteralPath (Join-Path $jobPath 'live-command.txt'))) {
        Set-Content -LiteralPath (Join-Path $jobPath 'live-command.txt') -Value 'pause' -Encoding ASCII -NoNewline
        Add-Content -LiteralPath $logPath -Value 'ERROR: External runner stopped; inspect the command error before retrying.' -Encoding UTF8
    }
    throw
} finally {
    # Release this COM handle; keep Illustrator and all user documents open.
    if ($null -ne $illustratorApp) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($illustratorApp) }
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
