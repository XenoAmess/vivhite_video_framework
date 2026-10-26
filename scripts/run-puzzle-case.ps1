param(
    [string]$WorkDirectory,
    [switch]$Extract,
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $WorkDirectory) {
    $WorkDirectory = Join-Path (Split-Path $repositoryRoot -Parent) 'vivhite-analysis-output/puzzle-restyle'
}
$WorkDirectory = [IO.Path]::GetFullPath($WorkDirectory)

function Invoke-Checked {
    param([string]$Executable, [string[]]$CommandArguments)
    & $Executable @CommandArguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable failed with exit code $LASTEXITCODE"
    }
}

Push-Location $repositoryRoot
try {
    $env:PYTHONUTF8 = '1'
    $python = Join-Path $repositoryRoot 'video-analyzer/.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        throw 'Install the Python worker environment first; see README.md.'
    }
    if ($Build) {
        Invoke-Checked '.\mvnw.cmd' @('verify')
    }
    $analyzer = 'video-analyzer/target/video-analyzer-0.1.0-SNAPSHOT.jar'
    $maker = 'video-maker/target/video-maker-0.1.0-SNAPSHOT.jar'
    $prepareArguments = @('-jar', $analyzer, 'prepare', 'series/math-education/inversion-count/episodes/01-sliding-puzzle/case.json', $WorkDirectory)
    if (-not $Extract) { $prepareArguments += '--reuse' }
    Invoke-Checked 'java' $prepareArguments
    Invoke-Checked $python @('series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis-authoring/assemble_assisted_review.py', $WorkDirectory,
        'series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis-authoring/review-notes.json')
    Invoke-Checked 'java' @('-jar', $analyzer, 'import-review', $WorkDirectory, (Join-Path $WorkDirectory 'review-bundle.json'))
    Invoke-Checked 'java' @('-jar', $analyzer, 'verify-puzzle', (Join-Path $WorkDirectory 'math-verification.json'))
    $analysisFile = Join-Path $WorkDirectory 'analysis-report.json'
    $directorDirectory = Join-Path $WorkDirectory 'director'
    Invoke-Checked 'java' @('-jar', $maker, 'prepare', $analysisFile, $directorDirectory)
    $plan = Join-Path $directorDirectory 'director-plan.json'
    Invoke-Checked $python @('series/math-education/inversion-count/episodes/01-sliding-puzzle/authoring/bind_director.py', $analysisFile,
        'series/math-education/inversion-count/episodes/01-sliding-puzzle/authoring/director-template.json', $plan)
    Invoke-Checked 'java' @('-jar', $maker, 'render', $analysisFile, $plan, $directorDirectory)
    Write-Output "Case complete: $directorDirectory"
} finally {
    Pop-Location
}
