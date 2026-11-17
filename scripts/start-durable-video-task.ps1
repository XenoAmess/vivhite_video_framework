param(
    [Parameter(Mandatory = $true)]
    [string]$Configuration,
    [switch]$UpdateOwnedTask
)

$ErrorActionPreference = 'Stop'
$configurationFile = (Resolve-Path -LiteralPath $Configuration).Path
$videoConfiguration = Get-Content -LiteralPath $configurationFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($videoConfiguration.schedulerTask -notmatch '^[A-Za-z0-9_.-]{1,180}$') {
    throw 'Invalid task name'
}
foreach ($videoPath in @($videoConfiguration.pythonw, $videoConfiguration.controller, $videoConfiguration.root)) {
    if (-not (Test-Path -LiteralPath $videoPath)) { throw "Missing runtime path: $videoPath" }
    if ($videoPath.Contains('"')) { throw 'Runtime path contains a quote' }
}
if ($configurationFile.Contains('"')) { throw 'Configuration path contains a quote' }
if ((Get-FileHash -LiteralPath $videoConfiguration.plan -Algorithm SHA256).Hash.ToLowerInvariant() -ne $videoConfiguration.planSha256) {
    throw 'Submitted production plan changed'
}
$videoArguments = '-X utf8 "' + $videoConfiguration.controller + '" --config "' + $configurationFile + '"'
$videoAction = New-ScheduledTaskAction -Execute $videoConfiguration.pythonw -Argument $videoArguments -WorkingDirectory $videoConfiguration.root
$videoSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$videoWatchdog = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
$existingVideoTask = Get-ScheduledTask -TaskName $videoConfiguration.schedulerTask -TaskPath '\' -ErrorAction SilentlyContinue
if ($existingVideoTask) {
    $ownedVideoConfigurationSuffix = ' --config "' + $configurationFile + '"'
    $ownedVideoTask = $existingVideoTask.Actions.Count -eq 1 -and
        $existingVideoTask.Actions[0].Execute -eq $videoConfiguration.pythonw -and
        $existingVideoTask.Actions[0].Arguments.EndsWith($ownedVideoConfigurationSuffix) -and
        $existingVideoTask.Actions[0].WorkingDirectory -eq $videoConfiguration.root
    if (-not $ownedVideoTask -or
        ($existingVideoTask.Actions[0].Arguments -ne $videoArguments -and -not $UpdateOwnedTask)) {
        throw 'An unrelated task already uses this name; it was not changed'
    }
    if ($UpdateOwnedTask -or $existingVideoTask.Triggers.Count -eq 0) {
        Set-ScheduledTask -TaskName $videoConfiguration.schedulerTask -TaskPath '\' -Action $videoAction -Settings $videoSettings -Trigger $videoWatchdog | Out-Null
    }
    if (-not $existingVideoTask.Settings.Enabled) {
        Enable-ScheduledTask -TaskName $videoConfiguration.schedulerTask -TaskPath '\' | Out-Null
    }
} else {
    $videoPrincipal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value) -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $videoConfiguration.schedulerTask -TaskPath '\' -Action $videoAction -Settings $videoSettings -Trigger $videoWatchdog -Principal $videoPrincipal -Description 'Native UHD rendering with a one-minute singleton watchdog, independent of the chat terminal; disabled when complete.' | Out-Null
}
Start-ScheduledTask -TaskName $videoConfiguration.schedulerTask -TaskPath '\'
Export-ScheduledTask -TaskName $videoConfiguration.schedulerTask -TaskPath '\' | Set-Content -LiteralPath (Join-Path $videoConfiguration.directory 'metadata/scheduled-task.xml') -Encoding UTF8
Get-ScheduledTask -TaskName $videoConfiguration.schedulerTask -TaskPath '\' | Select-Object TaskName, State, @{Name = 'ExecutionTimeLimit'; Expression = { $_.Settings.ExecutionTimeLimit }}, @{Name = 'TriggerCount'; Expression = { $_.Triggers.Count }}
