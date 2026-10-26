param(
    [string]$OutputDirectory = 'D:/workspace/vivhite-analysis-output/math-education/inversion-count/03-wilson-theorem/production-v1',
    [string]$Presenter = 'C:/Users/xenoa/Pictures/718c36bc01a173d0c42c0d1131f67e31055244c7.jpg',
    [string]$Voice = 'zh-CN-XiaoxiaoNeural',
    [string]$Rate = '+8%',
    [ValidateSet('h264_nvenc', 'libx264')]
    [string]$VideoCodec = 'h264_nvenc',
    [string]$PythonPath,
    [string]$MakerJar,
    [string]$WorkerPath,
    [switch]$PreviewOnly
)
$ErrorActionPreference = 'Stop'
$episodeDirectory = Split-Path $PSScriptRoot -Parent
$candidateDirectory = Get-Item $episodeDirectory
while (-not (Test-Path -LiteralPath (Join-Path $candidateDirectory.FullName 'video-maker/pom.xml'))) {
    if ($null -eq $candidateDirectory.Parent) { throw 'Cannot locate the framework root.' }
    $candidateDirectory = $candidateDirectory.Parent
}
$frameworkRoot = $candidateDirectory.FullName
if (-not $PythonPath) { $PythonPath = Join-Path $frameworkRoot 'video-maker/.venv/Scripts/python.exe' }
if (-not $MakerJar) { $MakerJar = Join-Path $frameworkRoot 'video-maker/target/video-maker-0.1.0-SNAPSHOT.jar' }
if (-not $WorkerPath) { $WorkerPath = Join-Path $frameworkRoot 'video-maker/tools/production_worker.py' }
foreach ($requiredPath in @($PythonPath, $MakerJar, $WorkerPath, $Presenter)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Missing production input: $requiredPath. Build video-maker with the Maven Wrapper and install its runtime first."
    }
}
$outputPath = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
$plan = Join-Path $outputPath 'authored-plan.json'
& $PythonPath (Join-Path $PSScriptRoot 'compose_production.py') --output $plan --voice $Voice "--rate=$Rate" --codec $VideoCodec
if ($LASTEXITCODE -ne 0) { throw 'Episode production compilation failed.' }
& $PythonPath (Join-Path $PSScriptRoot 'verify_production.py') --plan $plan
if ($LASTEXITCODE -ne 0) { throw 'Authored mathematical operations failed independent verification.' }
$planHash = (Get-FileHash -LiteralPath $plan -Algorithm SHA256).Hash.ToLowerInvariant()
$presenterHash = (Get-FileHash -LiteralPath $Presenter -Algorithm SHA256).Hash.ToLowerInvariant()
$reportPath = Join-Path $outputPath 'production-report.json'
if ((Test-Path -LiteralPath (Join-Path $outputPath 'film.mp4')) -and (Test-Path -LiteralPath $reportPath)) {
    $priorReport = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($priorReport.planSha256 -ne $planHash -or $priorReport.presenterSha256 -ne $presenterHash) {
        throw 'Existing film uses different inputs. Select a new output directory to preserve that version.'
    }
}

# Content-addressed snapshots isolate this run from concurrent Maven builds.
$runtimeDirectory = Join-Path $outputPath 'runtime'
New-Item -ItemType Directory -Force -Path $runtimeDirectory | Out-Null
$jarHash = (Get-FileHash -LiteralPath $MakerJar -Algorithm SHA256).Hash.ToLowerInvariant()
$workerHash = (Get-FileHash -LiteralPath $WorkerPath -Algorithm SHA256).Hash.ToLowerInvariant()
$runtimeJar = Join-Path $runtimeDirectory "video-maker-$jarHash.jar"
$runtimeWorker = Join-Path $runtimeDirectory "production-worker-$workerHash.py"
if (-not (Test-Path -LiteralPath $runtimeJar)) { Copy-Item -LiteralPath $MakerJar -Destination $runtimeJar }
if (-not (Test-Path -LiteralPath $runtimeWorker)) { Copy-Item -LiteralPath $WorkerPath -Destination $runtimeWorker }
if ((Get-FileHash -LiteralPath $runtimeJar -Algorithm SHA256).Hash.ToLowerInvariant() -ne $jarHash -or
    (Get-FileHash -LiteralPath $runtimeWorker -Algorithm SHA256).Hash.ToLowerInvariant() -ne $workerHash) {
    throw 'A frozen runtime snapshot does not match its content hash.'
}
$runtimeRecord = [ordered]@{
    schemaVersion = 'vivhite-frozen-production-runtime-1'
    makerJarSha256 = $jarHash
    workerSha256 = $workerHash
    productionPlanSha256 = $planHash
    presenterSha256 = $presenterHash
    cacheIsolation = 'episode-output/tts-cache'
}
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText((Join-Path $runtimeDirectory "contract-$planHash.json"), ($runtimeRecord | ConvertTo-Json) + "`n", $utf8NoBom)
& java -XX:ActiveProcessorCount=4 -jar $runtimeJar validate-production $plan
if ($LASTEXITCODE -ne 0) { throw 'Executable production plan validation failed.' }
if ($PreviewOnly) {
    & java -XX:ActiveProcessorCount=4 -jar $runtimeJar preview $plan (Join-Path $outputPath 'preview') $Presenter
    if ($LASTEXITCODE -ne 0) { throw 'Technical preview failed.' }
    return
}
& $PythonPath (Join-Path $frameworkRoot 'scripts/character_review.py') check --episode (Join-Path $episodeDirectory 'episode.json') --document $plan --asset $Presenter
if ($LASTEXITCODE -ne 0) {
    throw 'Complete both semantic reviews for this exact plan and actual presenter before production.'
}
$priorWorker = $env:MAKER_WORKER
$priorCache = $env:MAKER_TTS_CACHE
try {
    $env:MAKER_WORKER = $runtimeWorker
    $env:MAKER_TTS_CACHE = Join-Path $outputPath 'tts-cache'
    & java -XX:ActiveProcessorCount=4 -jar $runtimeJar produce $plan $outputPath $Presenter $PythonPath
    if ($LASTEXITCODE -ne 0) { throw 'Production failed; matching audio and segment caches remain available.' }
} finally {
    $env:MAKER_WORKER = $priorWorker
    $env:MAKER_TTS_CACHE = $priorCache
}
