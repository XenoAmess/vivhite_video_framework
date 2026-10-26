param(
    [string]$OutputDirectory = 'D:/workspace/vivhite-analysis-output/math-education/inversion-count/02-rectangle-proof/production-v1',
    [string]$Presenter = 'C:/Users/xenoa/Pictures/718c36bc01a173d0c42c0d1131f67e31055244c7.jpg',
    [string]$Voice = 'zh-CN-XiaoxiaoNeural',
    [string]$Rate = '+8%',
    [string]$VideoCodec = 'h264_nvenc',
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
$python = Join-Path $frameworkRoot 'video-maker/.venv/Scripts/python.exe'
$jar = Join-Path $frameworkRoot 'video-maker/target/video-maker-0.1.0-SNAPSHOT.jar'
$worker = Join-Path $frameworkRoot 'video-maker/tools/production_worker.py'
$episode = Join-Path $episodeDirectory 'episode.json'
if (-not (Test-Path -LiteralPath $jar)) { throw 'Build video-maker with the Maven Wrapper first.' }
$outputPath = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
$plan = Join-Path $outputPath 'authored-plan.json'
& $python (Join-Path $PSScriptRoot 'compose_production.py') --output $plan --voice $Voice "--rate=$Rate" --video-codec $VideoCodec
if ($LASTEXITCODE -ne 0) { throw 'Episode production compilation failed.' }

# Freeze the actual backend and worker; concurrent builds cannot alter this run.
$runtimeDirectory = Join-Path $outputPath 'runtime'
New-Item -ItemType Directory -Force -Path $runtimeDirectory | Out-Null
$jarHash = (Get-FileHash -LiteralPath $jar -Algorithm SHA256).Hash.ToLowerInvariant()
$workerHash = (Get-FileHash -LiteralPath $worker -Algorithm SHA256).Hash.ToLowerInvariant()
$runtimeJar = Join-Path $runtimeDirectory "video-maker-$jarHash.jar"
$runtimeWorker = Join-Path $runtimeDirectory "production-worker-$workerHash.py"
Copy-Item -LiteralPath $jar -Destination $runtimeJar
Copy-Item -LiteralPath $worker -Destination $runtimeWorker
$runtimeRecord = [ordered]@{
    schemaVersion = 'vivhite-frozen-production-runtime-1'
    makerJarSha256 = $jarHash
    workerSha256 = $workerHash
    productionPlanSha256 = (Get-FileHash -LiteralPath $plan -Algorithm SHA256).Hash.ToLowerInvariant()
    presenterSha256 = (Get-FileHash -LiteralPath $Presenter -Algorithm SHA256).Hash.ToLowerInvariant()
    cacheIsolation = 'episode-output/tts-cache'
}
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText((Join-Path $outputPath 'runtime-contract.json'), ($runtimeRecord | ConvertTo-Json) + "`n", $utf8NoBom)
& java -jar $runtimeJar validate-production $plan
if ($LASTEXITCODE -ne 0) { throw 'Executable production plan validation failed.' }
if ($PreviewOnly) {
    & java -jar $runtimeJar preview $plan (Join-Path $outputPath 'preview') $Presenter
    if ($LASTEXITCODE -ne 0) { throw 'Technical preview failed.' }
    return
}
& $python (Join-Path $frameworkRoot 'scripts/character_review.py') check --episode $episode --document $plan --asset $Presenter
if ($LASTEXITCODE -ne 0) { throw 'Complete both semantic reviews for this exact plan and actual presenter before production.' }
$priorWorker = $env:MAKER_WORKER
$priorCache = $env:MAKER_TTS_CACHE
try {
    $env:MAKER_WORKER = $runtimeWorker
    $env:MAKER_TTS_CACHE = Join-Path $outputPath 'tts-cache'
    & java -jar $runtimeJar produce $plan $outputPath $Presenter $python
    if ($LASTEXITCODE -ne 0) { throw 'Episode production failed; matching audio and segment caches remain available.' }
} finally {
    $env:MAKER_WORKER = $priorWorker
    $env:MAKER_TTS_CACHE = $priorCache
}
