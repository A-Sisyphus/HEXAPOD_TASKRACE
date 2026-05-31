param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Command
)

$ErrorActionPreference = "Stop"

$RemoteUser = "jetson"
$RemoteHost = "172.20.10.14"
$RemoteWorkspace = "/home/jetson/task_race_ws"
$RosSetup = "/opt/ros/humble/setup.bash"
$WorkspaceSetup = "$RemoteWorkspace/install/setup.bash"

if (-not $Command -or $Command.Count -eq 0) {
    Write-Error "Usage: .\tools\remote_ros2.cmd <remote command>"
    exit 2
}

$RemoteCommand = ($Command -join " ")
$RemoteScript = @"
set -e
cd "$RemoteWorkspace"
source "$RosSetup"
if [ -f "$WorkspaceSetup" ]; then
    source "$WorkspaceSetup"
fi
$RemoteCommand
"@

$EncodedScript = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($RemoteScript))
$Runner = "printf %s $EncodedScript | base64 -d | bash"

ssh "$RemoteUser@$RemoteHost" $Runner
