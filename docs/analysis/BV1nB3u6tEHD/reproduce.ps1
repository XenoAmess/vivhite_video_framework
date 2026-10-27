#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceVideo,
    [string]$WorkDirectory,
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$sourcePath = (Resolve-Path -LiteralPath $SourceVideo).Path
$expectedHash = 'bcff1a458229576af244e527e0b014fcb11ea4faa0cca04f2238f41da86a98cf'
if ((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
    throw 'Source fingerprint differs from the reviewed video. Do not reuse this review for another file.'
}
if (-not $WorkDirectory) {
    $WorkDirectory = Join-Path $repositoryRoot '../vivhite-analysis-output/arknights-lime-letter-BV1nB3u6tEHD'
}
$analysisWork = [System.IO.Path]::GetFullPath($WorkDirectory)
if ($analysisWork.Equals($repositoryRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
        $analysisWork.StartsWith($repositoryRoot + [System.IO.Path]::DirectorySeparatorChar,
            [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Keep media evidence outside the Git repository.'
}

function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command"
    }
}

$previousPythonUtf8 = $env:PYTHONUTF8
$previousDisableXet = $env:HF_HUB_DISABLE_XET
Push-Location $repositoryRoot
try {
    $env:PYTHONUTF8 = '1'
    $env:HF_HUB_DISABLE_XET = '1'
    if ($Build) {
        Invoke-Checked -Command './mvnw.cmd' -Arguments @('-pl', 'video-analyzer', '-am', 'verify')
    }
    $python = Join-Path $repositoryRoot 'video-analyzer/.venv/Scripts/python.exe'
    $worker = Join-Path $repositoryRoot 'video-analyzer/tools/media_worker.py'
    $jar = Join-Path $repositoryRoot 'video-analyzer/target/video-analyzer-0.1.0-SNAPSHOT.jar'
    foreach ($requiredPath in @($python, $worker, $jar)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "Missing analyzer prerequisite: $requiredPath"
        }
    }
    $contentDirectory = Join-Path $analysisWork 'content'
    $styleDirectory = Join-Path $analysisWork 'style'
    New-Item -ItemType Directory -Path $contentDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $styleDirectory -Force | Out-Null

    Invoke-Checked -Command $python -Arguments @($worker, 'transcribe', '--input', $sourcePath,
        '--output', $contentDirectory, '--model', 'large-v3-turbo', '--language', 'en',
        '--device', 'cpu', '--compute-type', 'int8', '--threads', '12')
    Invoke-Checked -Command $python -Arguments @($worker, 'vision', '--input', $sourcePath,
        '--output', $contentDirectory, '--sample-seconds', '1', '--ocr',
        '--subtitle-box', '0', '0.92', '1', '1')
    Invoke-Checked -Command $python -Arguments @($worker, 'audio', '--input', $sourcePath,
        '--output', $contentDirectory)

    # Both analysis roles intentionally use the same source and inference settings.
    Get-ChildItem -LiteralPath $contentDirectory |
        Copy-Item -Destination $styleDirectory -Recurse -Force
    $config = [ordered]@{
        schemaVersion = '1.0'
        caseId = 'arknights-lime-letter-BV1nB3u6tEHD'
        contentVideo = $sourcePath
        styleVideo = $sourcePath
        python = $python
        worker = $worker
        asrModel = 'large-v3-turbo'
        asrLanguage = 'en'
        device = 'cpu'
        computeType = 'int8'
        threads = 12
        windowSeconds = 30
        frameSampleSeconds = 1
        contentOcr = $true
        styleOcr = $true
        contentSubtitleBox = @(0, 0.92, 1, 1)
        styleSubtitleBox = @(0, 0.92, 1, 1)
    }
    $configPath = Join-Path $analysisWork 'case.json'
    [System.IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 10) + "`n",
        [System.Text.UTF8Encoding]::new($false))
    Invoke-Checked -Command 'java' -Arguments @('-jar', $jar, 'prepare', $configPath, $analysisWork, '--reuse')
    Invoke-Checked -Command 'java' -Arguments @('-jar', $jar, 'import-review', $analysisWork,
        (Join-Path $PSScriptRoot 'review-bundle.json'))
    Write-Output "Evidence and validated report: $analysisWork"
} finally {
    $env:PYTHONUTF8 = $previousPythonUtf8
    $env:HF_HUB_DISABLE_XET = $previousDisableXet
    Pop-Location
}
