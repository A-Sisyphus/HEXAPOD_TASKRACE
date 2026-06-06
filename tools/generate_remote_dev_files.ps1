param(
    [string]$RemoteUser = "jetson",
    [string]$RemoteHost = "172.20.10.14",
    [string]$RemoteWorkspace = "/home/jetson/task_race_ws",
    [string]$RosDistro = "humble",
    [string]$RosSetup = "",
    [string]$WindowsUncWorkspace = "",
    [string]$WorkspaceRoot = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

if (-not $WorkspaceRoot) {
    $WorkspaceRoot = Split-Path -Parent $PSScriptRoot
}

if (-not $RosSetup) {
    $RosSetup = "/opt/ros/$RosDistro/setup.bash"
}

if (-not $WindowsUncWorkspace) {
    $WindowsPathSuffix = $RemoteWorkspace -replace "/", "\"
    $WindowsUncWorkspace = "\\sshfs.r\$RemoteUser@$RemoteHost$WindowsPathSuffix"
}

$WorkspaceSetup = "$RemoteWorkspace/install/setup.bash"
$SshTarget = "$RemoteUser@$RemoteHost"

function Join-WorkspacePath {
    param([string]$RelativePath)
    if ([System.IO.Path]::IsPathRooted($RelativePath)) {
        return $RelativePath
    }
    return Join-Path $WorkspaceRoot $RelativePath
}

function Write-GeneratedFile {
    param(
        [string]$RelativePath,
        [string]$Content
    )

    $Path = Join-WorkspacePath $RelativePath
    if ((Test-Path -LiteralPath $Path) -and -not $Force) {
        Write-Host "skip existing $RelativePath"
        return
    }

    $Parent = Split-Path -Parent $Path
    if ($Parent -and -not (Test-Path -LiteralPath $Parent)) {
        New-Item -ItemType Directory -Force -Path $Parent | Out-Null
    }

    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
    Write-Host "wrote $RelativePath"
}

$RemoteDevYaml = @"
remote:
  user: $RemoteUser
  host: $RemoteHost
  target: $SshTarget
  workspace: $RemoteWorkspace
  ros_distro: $RosDistro
  ros_setup: $RosSetup
  workspace_setup: $WorkspaceSetup

windows:
  unc_workspace: "$($WindowsUncWorkspace -replace "\\", "\\")"

helper:
  windows_cmd: tools/remote_ros2.cmd
  windows_ps1: tools/remote_ros2.ps1
  ssh_prefix_rule:
    - ssh
    - $SshTarget

agents:
  file: AGENTS.md
  generated: true
"@

$CodexContext = @"
# Codex Remote Development Context

- Remote target: `$SshTarget`
- Remote workspace: `$RemoteWorkspace`
- Windows UNC workspace: `$WindowsUncWorkspace`
- ROS distro: `$RosDistro`
- ROS setup: `$RosSetup`
- Workspace setup: `$WorkspaceSetup`
- Fixed helper: `tools/remote_ros2.cmd`

## Command policy

Windows VSCode is used for editing files in the SSHFS-mounted workspace.
ROS 2, colcon, launch, topic, TF, and log commands should run on the Jetson remote host.
"@

$AgentsMd = @"
# 1 新的对话，优先遵守本文件内的 SSHFS/ROS 远程开发规则；不要为了启动流程强制读取 C:\Users\tuheyuan\.codex\skills\sshfs-remote-dev\SKILL.md。只有当本文件信息不够、且确实需要 skill 细节时，才尝试读取该 skill。

# 2 每次新对话，开头固定加一句“hello world”

# 2.1 新会话启动策略
- 不要把读取外部 skill 当作必需前置步骤。
- 如果本文件已经覆盖当前任务所需规则，直接执行任务。
- 如果本地 PowerShell 报 `windows sandbox: spawn setup refresh`，最多重试一次；之后切换到远端执行流程，不要继续反复重试本地 PowerShell。
- 不要根据历史权限配置或旧目录结构推断 helper script 路径；只使用当前配置、已经确认存在的文件，或者询问用户。

# 2.2 ROS/SSHFS 命令执行策略
- Windows 侧访问工作区优先使用 UNC 路径：`$WindowsUncWorkspace`。
- ROS 2、colcon、launch、ros2 topic、日志和 TF 检查应在 Jetson 远端执行，使用 Linux 路径：`$RemoteWorkspace`。
- 不要临时创建 wrapper 脚本，除非用户明确要求或当前配置已经定义。
- 避免让复杂命令同时经过 PowerShell、cmd、ssh、bash 多层解析；复杂逻辑应放到 Jetson 远端 `.sh` 脚本里，本地只通过简单 SSH 调用。

# 2.3 SSH 持久允许策略
- 当需要连接 `.codex-remote-dev.yaml` 中声明过的 SSH 设备时，首次执行远端命令应自动发起精确的持久允许申请。
- 申请的 `prefix_rule` 必须只覆盖当前设备，例如：`["ssh", "$SshTarget"]`。
- 不要申请宽泛规则，例如 `["ssh"]`，也不要让 skill 尝试绕过 Codex 权限审批或自行写入权限白名单。
- 用户批准该前缀后，后续同一设备的 ROS 2、colcon、launch、ros2 topic 等远端命令可直接使用该 SSH 入口。

# 2.4 GUI 生成物约定
- GUI 在录入远端开发基本信息后，应尽量同时生成以下文件：`.codex-remote-dev.yaml`、`.codex-context.md`、`AGENTS.md`、`tools/remote_ros2.cmd`、`tools/remote_ros2.ps1`。
- `.codex-remote-dev.yaml` 应声明远端用户、主机、Linux 工作区、Windows UNC 工作区，以及 helper 脚本路径。
- `AGENTS.md` 是工作区级规则来源，应优先于外部 skill 的通用说明。
- GUI 生成的 helper 脚本必须只封装当前声明的设备和工作区，不要写入多个历史设备或旧目录。

# 2.5 helper 脚本使用策略
- 只有在 `.codex-remote-dev.yaml` 已声明 helper 路径，且文件已确认存在时，Codex 才能使用 helper。
- 不要因为权限上下文、历史批准规则或旧会话中出现过 `tools/remote_ros2.cmd` / `tools/remote_ros2.ps1`，就推断当前工作区仍然存在这些文件。
- helper 只负责进入远端工作区、source ROS 环境、source 工作区环境并执行传入命令。
- GUI 生成的固定 helper 路径为 `tools/remote_ros2.cmd` 和 `tools/remote_ros2.ps1`；其中 `.cmd` 只负责调用同目录 `.ps1`。
- GUI 应把当前设备信息写入 `tools/remote_ros2.ps1`：远端用户、主机、Linux 工作区、ROS setup 路径和工作区 setup 路径。
- 典型调用形式为：`.\tools\remote_ros2.cmd "ros2 topic list"` 或 `.\tools\remote_ros2.cmd "ros2 launch <package> navigation2.launch"`。
- helper 不应包含复杂业务逻辑；复杂的多步骤检查应写成远端 `.sh` 脚本，再通过 helper 或 SSH 简单调用。
- 如果 helper 不存在或配置未声明，优先对 `.codex-remote-dev.yaml` 中的当前 SSH 设备发起精确 `prefix_rule` 申请。

# 2.6 远端任务执行流程
- 执行 ROS 2 任务前，先确认命令应该运行在 Jetson 远端，而不是 Windows/SSHFS 本地路径。
- 需要查找 launch/package 时，在远端 `$RemoteWorkspace` 中执行 `find`、`ros2 pkg` 等命令。
- 启动 launch 后，应另开一次远端命令检查节点、话题、TF 或日志；不要只根据启动输出判断系统状态。
- 长时间运行的 launch 应使用远端后台进程、日志文件或明确的终止方式，避免让本地工具调用一直阻塞。
- 完成检查后，应向用户说明启动命令、关键输出、话题列表以及是否仍有后台进程在运行。

# 2.7 失败处理
- 如果本地 PowerShell 报 `windows sandbox: spawn setup refresh`，最多重试一次；再次失败后不要继续反复读取本地文件。
- 如果 SSH 权限申请自动审核超时，最多重试一次同样的精确申请；再次超时后说明权限层阻塞，并给出可执行的替代方案。
- 不要把自动审核超时解释为 SSH 主机不可达、密码错误或 ROS 环境错误，除非已经有远端命令输出证明。
- 如果 helper 与配置不一致，以 `.codex-remote-dev.yaml` 和当前已确认存在的文件为准，不使用历史路径。

# 3 Windows/SSHFS 路径约定
- 在 Windows 侧访问本工作区时，优先使用 UNC 路径：`$WindowsUncWorkspace`
- 尽量避免把本地命令的工作目录设为 `Z:\`，因为 Codex/PowerShell 沙箱有时无法稳定解析映射盘。
- ROS 2、colcon、launch、ros2 topic 等命令仍然应该在 Jetson 远端执行，使用 Linux 路径：`$RemoteWorkspace`
"@

$RemoteRos2Cmd = @'
@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0remote_ros2.ps1" %*
'@

$RemoteRos2Ps1 = @'
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Command
)

$ErrorActionPreference = "Stop"

$RemoteUser = "__REMOTE_USER__"
$RemoteHost = "__REMOTE_HOST__"
$RemoteWorkspace = "__REMOTE_WORKSPACE__"
$RosSetup = "__ROS_SETUP__"
$WorkspaceSetup = "__WORKSPACE_SETUP__"

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
'@

$RemoteRos2Ps1 = $RemoteRos2Ps1.Replace("__REMOTE_USER__", $RemoteUser)
$RemoteRos2Ps1 = $RemoteRos2Ps1.Replace("__REMOTE_HOST__", $RemoteHost)
$RemoteRos2Ps1 = $RemoteRos2Ps1.Replace("__REMOTE_WORKSPACE__", $RemoteWorkspace)
$RemoteRos2Ps1 = $RemoteRos2Ps1.Replace("__ROS_SETUP__", $RosSetup)
$RemoteRos2Ps1 = $RemoteRos2Ps1.Replace("__WORKSPACE_SETUP__", $WorkspaceSetup)

Write-GeneratedFile ".codex-remote-dev.yaml" $RemoteDevYaml
Write-GeneratedFile ".codex-context.md" $CodexContext
Write-GeneratedFile "AGENTS.md" $AgentsMd
Write-GeneratedFile "tools/remote_ros2.cmd" $RemoteRos2Cmd
Write-GeneratedFile "tools/remote_ros2.ps1" $RemoteRos2Ps1
