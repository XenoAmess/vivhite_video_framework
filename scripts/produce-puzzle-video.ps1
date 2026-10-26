param(
    [string]$CaseDirectory = (Join-Path $PSScriptRoot '../../vivhite-analysis-output/puzzle-restyle'),
    [string]$OutputDirectory = '',
    [string]$Presenter = 'C:/Users/xenoa/Pictures/718c36bc01a173d0c42c0d1131f67e31055244c7.jpg',
    [string]$Python = '',
    [string]$Voice = 'zh-CN-XiaoxiaoNeural',
    [ValidateSet(2, 3)][int]$Revision = 3,
    [ValidatePattern('^[+-]\d{1,2}%$')][string]$Rate = '+8%',
    [ValidateSet('libx264', 'h264_nvenc')][string]$VideoCodec = 'libx264',
    [string]$TtsCacheDirectory = '',
    [switch]$Build,
    [switch]$PreviewOnly,
    [switch]$OfflineTts
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $OutputDirectory) {
    $OutputDirectory = if ($Revision -eq 3) {
        Join-Path $repoRoot '../vivhite-analysis-output/math-education/inversion-count/01-sliding-puzzle/production-v3'
    } else { Join-Path $CaseDirectory 'production-v2-cued' }
}
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
$previousWorker = $env:MAKER_WORKER
try {
    if ($Build) {
        & (Join-Path $repoRoot 'mvnw.cmd') -pl video-maker -am verify
        if ($LASTEXITCODE -ne 0) { throw 'Maker build failed' }
    }
    $jar = Join-Path $repoRoot 'video-maker/target/video-maker-0.1.0-SNAPSHOT.jar'
    if (-not (Test-Path -LiteralPath $jar)) { throw 'Run with -Build first' }
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    # Every episode uses immutable runtime bytes even while other tasks rebuild the maker.
    $runtimeDirectory = Join-Path $OutputDirectory 'runtime'
    New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
    $workerFile = if ($previousWorker) { [IO.Path]::GetFullPath($previousWorker) }
        else { Join-Path $repoRoot 'video-maker/tools/production_worker.py' }
    $jarHash = (Get-FileHash -LiteralPath $jar -Algorithm SHA256).Hash.ToLowerInvariant()
    $workerHash = (Get-FileHash -LiteralPath $workerFile -Algorithm SHA256).Hash.ToLowerInvariant()
    $runtimeJar = Join-Path $runtimeDirectory "video-maker-$jarHash.jar"
    $runtimeWorker = Join-Path $runtimeDirectory "production-worker-$workerHash.py"
    if (-not (Test-Path -LiteralPath $runtimeJar)) { Copy-Item -LiteralPath $jar -Destination $runtimeJar }
    if (-not (Test-Path -LiteralPath $runtimeWorker)) { Copy-Item -LiteralPath $workerFile -Destination $runtimeWorker }
    $jar = $runtimeJar
    $env:MAKER_WORKER = $runtimeWorker
    $planFile = Join-Path $OutputDirectory 'authored-plan.json'
    $composerName = if ($Revision -eq 2) { 'compose_production.py' } else { 'compose_production_v3.py' }
    $composerFile = Join-Path $repoRoot "series/math-education/inversion-count/episodes/01-sliding-puzzle/authoring/$composerName"
    & $Python $composerFile `
        (Join-Path $CaseDirectory 'analysis-report.json') (Join-Path $CaseDirectory 'math-verification.json') $planFile `
        --voice $Voice "--rate=$Rate" --video-codec $VideoCodec
    if ($LASTEXITCODE -ne 0) { throw 'Case evidence binding failed' }
    if ($TtsCacheDirectory) { $env:MAKER_TTS_CACHE = [IO.Path]::GetFullPath($TtsCacheDirectory) }
    else { $env:MAKER_TTS_CACHE = Join-Path $OutputDirectory 'tts-cache' }
    if ($OfflineTts) { $env:MAKER_OFFLINE_TTS = '1' }
    if ($PreviewOnly) {
        & java -jar $jar preview $planFile (Join-Path $OutputDirectory 'preview') $Presenter
    } else {
        & $Python (Join-Path $repoRoot 'scripts/character_review.py') check `
            --episode (Join-Path $repoRoot 'series/math-education/inversion-count/episodes/01-sliding-puzzle/episode.json') `
            --document $planFile --asset $Presenter
        if ($LASTEXITCODE -ne 0) { throw 'Complete both semantic character reviews for the retained authored-plan.json before production.' }
        & java -jar $jar produce $planFile $OutputDirectory $Presenter $Python
    }
    if ($LASTEXITCODE -ne 0) { throw 'Video production failed; inspect retained attempt and partial outputs.' }
} finally {
    $env:MAKER_OFFLINE_TTS = $previousOffline
    $env:MAKER_TTS_CACHE = $previousCache
    $env:MAKER_WORKER = $previousWorker
    Pop-Location
}
