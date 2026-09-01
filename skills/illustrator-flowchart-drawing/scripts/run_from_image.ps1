#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InputImage,
    [Parameter(Mandatory = $true)][string]$SceneManifest,
    [Parameter(Mandatory = $true)][string]$TextManifest,
    [Parameter(Mandatory = $true)][string]$OutputRoot,
    [string]$SshTarget = "supersvg-server",
    [string]$SuperSvgRemoteRoot = "services/supersvg-eval",
    [int]$SuperSvgGpuIndex = 1,
    [int]$SuperSvgRows = 1,
    [int]$SuperSvgCols = 1,
    [int]$SuperSvgOverlap = 64,
    [int]$SuperSvgPathNum = 1600,
    [int]$SuperSvgOptimizeIter = 14,
    [int]$SuperSvgRefineBatchSize = 8,
    [int]$SuperSvgTimeout = 7200,
    [ValidateSet("center", "top-center", "left-center", "bottom-center", "bottom-right", "top-right", "bottom-left", "top-left")]
    [string]$Placement = "center",
    [double]$MaxWidthFraction = 0.72,
    [double]$MaxHeightFraction = 0.78,
    [int]$DelayMs = 0,
    [int]$MinBatchSize = 20,
    [int]$MaxBatchSize = 50,
    [int]$CheckpointBatches = 10,
    [int]$CheckpointSeconds = 30,
    [switch]$PerAsset,
    [switch]$ForceVectorizeAssets,
    [switch]$Sam3ForegroundClips,
    [switch]$NoIllustrator,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$skillRoot = Split-Path $PSScriptRoot -Parent
$managedPython = Join-Path $skillRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $managedPython -PathType Leaf)) {
    throw "ILLUSTRATOR_FLOWCHART_ENV_MISSING|Run .\setup.ps1 before first use."
}
$arguments = @(
    (Join-Path $PSScriptRoot 'run_from_image.py'),
    '--input-image', $InputImage,
    '--scene-manifest', $SceneManifest,
    '--text-manifest', $TextManifest,
    '--output-root', $OutputRoot,
    '--ssh-target', $SshTarget,
    '--supersvg-remote-root', $SuperSvgRemoteRoot,
    '--supersvg-gpu-index', [string]$SuperSvgGpuIndex,
    '--supersvg-rows', [string]$SuperSvgRows,
    '--supersvg-cols', [string]$SuperSvgCols,
    '--supersvg-overlap', [string]$SuperSvgOverlap,
    '--supersvg-path-num', [string]$SuperSvgPathNum,
    '--supersvg-optimize-iter', [string]$SuperSvgOptimizeIter,
    '--supersvg-refine-batch-size', [string]$SuperSvgRefineBatchSize,
    '--supersvg-timeout', [string]$SuperSvgTimeout,
    '--placement', $Placement,
    '--max-width-fraction', [string]$MaxWidthFraction,
    '--max-height-fraction', [string]$MaxHeightFraction,
    '--delay-ms', [string]$DelayMs,
    '--min-batch-size', [string]$MinBatchSize,
    '--max-batch-size', [string]$MaxBatchSize,
    '--checkpoint-batches', [string]$CheckpointBatches,
    '--checkpoint-seconds', [string]$CheckpointSeconds
)
if ($PerAsset) { $arguments += '--per-asset' }
if ($ForceVectorizeAssets) { $arguments += '--force-vectorize-assets' }
if ($Sam3ForegroundClips) { $arguments += '--sam3-foreground-clips' }
if ($NoIllustrator) { $arguments += '--no-illustrator' }
if ($DryRun) { $arguments += '--dry-run' }

& $managedPython @arguments
exit $LASTEXITCODE
