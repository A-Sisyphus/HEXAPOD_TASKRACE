# AGENTS.md

## 会话规则

- 每次新对话开头固定说：hello world。
- 本文件是当前工作区最高优先级规则。只有本文件信息不够时，才读取外部 skill。
- 不要把读取 `C:\Users\tuheyuan\.codex\skills\sshfs-remote-dev\SKILL.md` 当作启动流程的必需步骤。
- 不要根据历史权限配置、旧会话输出或旧目录结构推断当前 helper 路径；只使用当前配置、已经确认存在的文件，或者询问用户。

## 当前环境

- Windows UNC 工作区：`\\sshfs.r\jetson@172.20.10.14\home\jetson\task_race_ws`
- Jetson SSH：`jetson@172.20.10.14`
- 远端 Linux 工作区：`/home/jetson/task_race_ws`
- Windows 侧访问工作区时优先使用 UNC 路径，尽量避免依赖 `Z:\` 映射盘。

## 执行入口优先级

1. 如果 `.codex-remote-dev.yaml` 声明了 helper，优先直接尝试当前工作区 helper：
   - `.\tools\remote_ros2.cmd "<command>"`
   - `.\tools\remote_ros2.ps1 "<command>"`
2. 不要为了确认 helper 是否存在而反复运行本地 `Test-Path`、`Get-Content` 或目录扫描；helper 的首次调用本身就是验证。
3. 如果 helper 调用返回文件不存在、PowerShell command-not-found 或配置不一致，再判定 helper 不可用。
4. 当前工作区已声明 helper 时，不要用外部 skill 的 generic helper 执行 routine ROS、colcon、launch、topic、node、日志、TF 或 git 命令。
5. helper 不存在、未声明或配置不一致时，才考虑外部 skill 的通用 helper 或让用户确认下一步。
6. 不要默认先运行 direct SSH 探测命令，例如 `ssh jetson@172.20.10.14 hostname`。
7. direct SSH 只在用户明确要求，或 helper 不可用且用户同意时使用。
8. helper 可用时，不要因为 direct SSH 审批超时而卡住任务。

## ROS/Jetson 规则

- ROS 2、colcon、launch、topic、node、TF、日志检查必须在 Jetson 远端执行。
- 不要在 Windows PowerShell 本地直接运行 ROS/Linux 命令。
- 查找 package、launch 文件或源码状态时，在 `/home/jetson/task_race_ws` 远端执行 `find`、`rg`、`git`、`ros2 pkg` 等命令。
- 启动 launch 后，必须另行检查 node、topic、log，必要时检查 TF 或 lifecycle；不要只根据启动输出判断系统状态。
- 长时间运行的 launch 应使用远端后台进程、日志文件和明确的终止方式，避免让本地工具调用一直阻塞。
- 测试结束后，必须清理由本次启动的后台进程，并刷新/复查 ROS daemon，避免残留节点影响后续检查。

## Helper 规则

- helper 只负责：
  - SSH 到当前设备；
  - `cd` 到远端工作区；
  - source ROS 环境；
  - source workspace install 环境；
  - 执行传入命令。
- helper 不写复杂业务逻辑。
- 复杂 launch、后台 PID、日志重定向、多步骤诊断、TF 检查组合等逻辑应放到远端 `.sh` 脚本，再用 helper 调用。
- GUI 生成的固定 helper 路径为 `tools/remote_ros2.cmd` 和 `tools/remote_ros2.ps1`；其中 `.cmd` 只负责调用同目录 `.ps1`。

## 交互式节点

- 对 `teleop_twist_keyboard` 等需要 TTY 的节点，不要直接用 `nohup ros2 run ... &` 测试。
- 需要测试交互式节点时，使用远端伪终端方式，例如 `script -q -f -c '<command>' <logfile>`。
- 如果日志出现 `termios.error: (25, 'Inappropriate ioctl for device')`，优先判断为缺少 TTY，而不是 ROS 包本身不可用。

## 故障处理

- `windows sandbox: spawn setup refresh` 是本地 Codex/Windows/SSHFS 兼容性问题，不代表 Jetson、SSH、网络、密码或 ROS 失败。
- 遇到该错误时，不要反复重试同一个本地 PowerShell 入口。
- 如果该错误发生在 helper 存在性检查阶段，不要把 helper 标记为缺失；直接尝试已声明的 helper 调用。
- SSH 审批超时不代表 SSH 主机不可达、密码错误或 ROS 环境坏，除非已经有远端输出证明。
- helper 可用时，优先继续通过 helper 完成任务。
- 如果 helper 不可用且 direct SSH 审批也超时，停止并向用户给出可手动运行的命令。
- 如果 helper 与 `.codex-remote-dev.yaml` 不一致，以当前配置和已确认存在的文件为准，不使用历史路径。

## GUI 生成物

- GUI 应生成或维护：
  - `.codex-remote-dev.yaml`
  - `.codex-context.md`
  - `AGENTS.md`
  - `tools/remote_ros2.cmd`
  - `tools/remote_ros2.ps1`
- `.codex-remote-dev.yaml` 是机器可读配置，应声明远端用户、主机、Linux 工作区、Windows UNC 工作区和 helper 路径。
- `.codex-context.md` 是人类可读上下文。
- `AGENTS.md` 是当前工作区规则来源，应优先于外部 skill 的通用说明。
- GUI 生成的 helper 只绑定当前设备和当前工作区，不混入历史设备或旧目录。

## 报告要求

- 完成远端任务后，说明使用的执行入口、远端工作区、关键命令、关键输出、话题/节点列表、日志位置和后台进程状态。
- 区分 Windows/SSHFS 路径和 Jetson/Linux 路径。
- 如果没有运行某项检查，说明原因。
