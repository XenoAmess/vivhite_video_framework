param(
    [string]$CaseDirectory = (Join-Path $PSScriptRoot '../../vivhite-analysis-output/puzzle-restyle'),
    [string]$OutputDirectory = '',
    [string]$Presenter = 'C:/Users/xenoa/Pictures/718c36bc01a173d0c42c0d1131f67e31055244c7.jpg',
    [string]$Python = '',
    [string]$Voice = 'zh-CN-XiaoxiaoNeural',
    [ValidatePattern('^[+-]\d{1,2}%$')][string]$Rate = '+8%',
    [ValidateSet('libx264', 'h264_nvenc')][string]$VideoCodec = 'libx264',
    [string]$TtsCacheDirectory = '',
    [switch]$Build,
    [switch]$PreviewOnly,
    [switch]$OfflineTts
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $CaseDirectory 'production-v2-cued' }
if (-not $Python) { $Python = Join-Path $repoRoot 'video-maker/.venv/Scripts/python.exe' }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
$CaseDirectory = [IO.Path]::GetFullPath($CaseDirectory)
$Python = [IO.Path]::GetFullPath($Python)
$Presenter = [IO.Path]::GetFullPath($Presenter)
if (-not (Test-Path -LiteralPath $Presenter -PathType Leaf)) { throw "Missing presenter: $Presenter" }
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Install video-maker/.venv and tools/requirements-lock.txt first.' }

Push-Location -LiteralPath $repoRoot
$previousOffline = $env:MAKER_OFFLINE_TTS
$previousCache = $env:MAKER_TTS_CACHE
try {
    if ($Build) {
        & (Join-Path $repoRoot 'mvnw.cmd') -pl video-maker -am verify
        if ($LASTEXITCODE -ne 0) { throw 'Maker build failed' }
    }
    $jar = Join-Path $repoRoot 'video-maker/target/video-maker-0.1.0-SNAPSHOT.jar'
    if (-not (Test-Path -LiteralPath $jar)) { throw 'Run with -Build first' }
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $planFile = Join-Path $OutputDirectory 'authored-plan.json'
    & $Python video-maker/examples/puzzle-restyle/compose_production.py `
        (Join-Path $CaseDirectory 'analysis-report.json') (Join-Path $CaseDirectory 'math-verification.json') $planFile `
        --voice $Voice "--rate=$Rate" --video-codec $VideoCodec
    if ($LASTEXITCODE -ne 0) { throw 'Case evidence binding failed' }
    if ($TtsCacheDirectory) { $env:MAKER_TTS_CACHE = [IO.Path]::GetFullPath($TtsCacheDirectory) }
    if ($OfflineTts) { $env:MAKER_OFFLINE_TTS = '1' }
    if ($PreviewOnly) {
        & java -jar $jar preview $planFile (Join-Path $OutputDirectory 'preview') $Presenter
    } else {
        & java -jar $jar produce $planFile $OutputDirectory $Presenter $Python
    }
    if ($LASTEXITCODE -ne 0) { throw 'Video production failed; inspect retained attempt and partial outputs.' }
} finally {
    $env:MAKER_OFFLINE_TTS = $previousOffline
    $env:MAKER_TTS_CACHE = $previousCache
    Pop-Location
}
