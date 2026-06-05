---
name: sshfs-remote-dev
description: Work in SSHFS-mounted remote Linux projects from a local Windows Codex session. Use for Jetson, ROS, ROS 2, colcon, launch, device, or remote-Linux workflows where files are edited through SSHFS but commands must run on the remote host.
---

# SSHFS Remote Dev

Use the mounted workspace for file reads and edits. Run Linux, ROS, ROS 2, colcon, launch, git, logs, TF, device, apt, and systemctl commands on the remote host.

Detailed GUI usage, examples, and troubleshooting notes belong in `references/`.

## Priority

Always prefer workspace-specific context over this generic skill.

Resolution order:

1. Current workspace `AGENTS.md`.
2. Current workspace `.codex-remote-dev.yaml`.
3. Declared and verified workspace helper scripts, such as `tools/remote_ros2.cmd` and `tools/remote_ros2.ps1`.
4. This skill's generic helper: `scripts/sshfs_exec.py`.
5. Saved profiles or workspace bindings.
6. SSHFS mount-path inference through the generic helper.

Direct `ssh user@host ...` is not part of the routine execution strategy. Use it only when the user explicitly asks for raw SSH or when all helper-based entries are unavailable and the user approves that exception.

Do not infer helper paths from old sessions, permission history, or unrelated workspaces.

## Core Rules

- Edit files through the mounted workspace, preferably the UNC path.
- Execute ROS, colcon, launch, bash, source, git status, logs, TF, and device commands on the remote host.
- Do not run Linux or ROS commands directly in local Windows PowerShell unless the user explicitly configured them locally.
- Prefer UNC paths over mapped drive letters when both are available.
- Use `apply_patch` for source edits.
- Do not overwrite unrelated user changes.
- Do not perform destructive cleanup without verifying the resolved remote path is inside the configured remote workspace and getting user approval.

## Workspace Helper First

If `.codex-remote-dev.yaml` or `AGENTS.md` declares helper scripts, treat those declared helper paths as the preferred entry before attempting direct SSH approval.

Do not require a separate local `Test-Path`, `Get-Content`, or directory scan before using a declared helper. In SSHFS workspaces with unstable Windows sandboxing, the first helper invocation is the validation. If the helper command itself returns "file not found", a PowerShell command-not-found error, or a configuration mismatch, then classify the helper as unavailable.

If a local helper existence check fails before execution with `windows sandbox: spawn setup refresh`, do not mark the helper missing and do not loop on local checks. Try the declared helper entry once with the simplest useful command for the task.

Typical helper calls:

```powershell
.\tools\remote_ros2.cmd "ros2 topic list"
.\tools\remote_ros2.cmd "ros2 launch <package> <launch_file>"
```

Treat `.cmd` helpers as the simple-command entry. When a remote command contains `cmd.exe` metacharacters such as `|`, `&`, `>`, or `<`, complex regular expressions, nested quotes, or multi-step shell logic, prefer the `.ps1` helper directly or put the logic in a remote `.sh` script and invoke that script through the helper. Do not misclassify local Windows command parsing failures as ROS, SSH, or remote-host failures.

For configured helper workspaces, do not start with direct `ssh user@host ...`, even for probes such as `hostname`, `pwd`, ROS checks, launch tests, or log checks. Run those through the helper.

Use direct SSH only when:

- no helper is declared;
- the declared helper files are missing;
- the helper is inconsistent with `.codex-remote-dev.yaml`;
- the generic helper is unavailable or unsuitable;
- the task explicitly requires raw SSH;
- the user approves that exception.

If direct SSH approval times out, do not retry it when a verified helper is available. Continue through the helper. If no helper-based path is available, stop and report that the approval layer blocked raw SSH; provide the exact helper/config issue that prevented normal execution.

## Helper Contract

Workspace helpers should only:

1. connect to the configured remote host;
2. `cd` into the configured remote workspace;
3. source the ROS setup file;
4. source the workspace setup file if present;
5. execute the provided command.

Helpers should not contain project business logic. Put complex multi-step logic in a remote `.sh` script and invoke that script through the helper.

## Generic Helper

Use `scripts/sshfs_exec.py` when no workspace helper exists or when profile/path mapping features are needed.

If `AGENTS.md` or `.codex-remote-dev.yaml` declares a workspace helper, do not use the generic helper for routine ROS, colcon, launch, topic, node, log, TF, or git commands. Use the declared workspace helper for those commands. The generic helper is allowed only when the workspace helper is undeclared, unavailable, being repaired, or when its profile/path-mapping features are specifically needed.

Common forms:

```powershell
python <skill_dir>\scripts\sshfs_exec.py --workspace <UNC workspace> --preflight quick
python <skill_dir>\scripts\sshfs_exec.py --workspace <UNC workspace> --preflight ros
python <skill_dir>\scripts\sshfs_exec.py --workspace <UNC workspace> --preflight full
python <skill_dir>\scripts\sshfs_exec.py --workspace <UNC workspace> -- ros2 topic list
python <skill_dir>\scripts\sshfs_exec.py --workspace <UNC workspace> -- colcon build --symlink-install
python <skill_dir>\scripts\sshfs_exec.py --workspace <UNC workspace> --shell "ros2 topic list | sort"
```

Use `--shell` only when shell operators, pipes, redirection, variables, or multiple commands are required.

If the generic helper itself requires raw SSH approval and approval times out, do not loop on approval requests. Report that helper-based execution could not be established and ask the user to fix the active workspace helper or approve raw SSH explicitly.

## GUI Role

The GUI is a remote development environment manager. It may manage devices, profiles, SSH tests, path mapping tests, ROS tests, workspace tests, active environment selection, and context generation.

The GUI may generate or update:

```text
.codex-remote-dev.yaml
.codex-context.md
AGENTS.md
tools/remote_ros2.cmd
tools/remote_ros2.ps1
```

The GUI should not modify project source code, compile projects, run normal development workflows, or control the Codex conversation.

Use the GUI for setup or repair, not for routine ROS command execution.

When the GUI updates `AGENTS.md`, it should write or replace only a marked sshfs-remote-dev generated block and preserve user-authored project rules outside that block.

## Configuration Files

`.codex-remote-dev.yaml` should contain the active remote development environment:

- remote user;
- remote host;
- optional port;
- remote workspace path;
- local UNC workspace path;
- ROS setup path;
- workspace setup path;
- helper script paths;
- ROS distro if known.

`.codex-context.md` is human-readable context.

`AGENTS.md` is the workspace-level rule source and may override this skill for the current project.

## Windows Sandbox Stability

If local commands fail before execution with:

```text
windows sandbox: spawn setup refresh
```

treat it as a local Windows/Codex sandbox and mounted-drive compatibility issue.

Do not keep retrying the same mapped-drive command. Prefer the configured UNC workspace path and use a verified workspace helper or `sshfs_exec.py --workspace <UNC path>`.

Do not describe this failure as a Jetson, ROS, SSH, password, or network problem unless remote command output proves it.

## First Pass

For ROS/Jetson/SSHFS tasks, do not start with broad local scans.

First decide the execution entry:

1. read current `AGENTS.md` if already available in context;
2. check `.codex-remote-dev.yaml` when needed;
3. confirm declared helper files only if not already confirmed;
4. use the helper for remote checks.

Use remote `rg`, `find`, `git status`, `colcon list`, and ROS commands inside the remote workspace. Use Windows/SSHFS only for targeted file reads and edits.

## Command Strategy

Use simple helper commands for simple tasks.

Use a remote `.sh` script when a task needs:

- background processes;
- PID capture;
- log files;
- redirection;
- traps;
- multiple ROS checks;
- launch plus status verification;
- quoting-sensitive shell logic.

Avoid packing complex logic through PowerShell, cmd, ssh, and bash at the same time.

## ROS 2 Checks

When diagnosing ROS 2, verify:

```bash
printenv ROS_DISTRO
command -v ros2
ros2 pkg list
ros2 pkg prefix <package>
ros2 node list
ros2 topic list
ros2 topic info <topic>
ros2 lifecycle nodes
ros2 run tf2_ros tf2_echo <from> <to>
```

If behavior looks stale, compare source files under `src/...` with installed files under `install/.../share/...`.

Expect GUI tools such as `rviz2` to fail on headless devices unless display forwarding is configured.

## Launch Workflow

When launching a long-running ROS process for testing:

1. start it remotely with a log file and recorded PID;
2. wait briefly for startup;
3. check nodes, topics, and logs from a separate remote command;
4. check TF or lifecycle state when relevant;
5. report the command, PID, log path, key output, and observed topics;
6. clean up processes started by this test;
7. refresh or recheck the ROS daemon when cleanup could affect later checks;
8. verify no test-started nodes remain.

Do not judge launch success only from startup output.

## Interactive Nodes

Nodes that need a TTY, such as `teleop_twist_keyboard`, should not be tested with plain `nohup ... &`.

Use a pseudo-terminal method such as remote `script -q -f -c '<command>' <logfile>` when testing them non-interactively.

If `termios.error: (25, 'Inappropriate ioctl for device')` appears, classify it as a missing TTY problem.

## Colcon Workflow

Use colcon as a remote validation/build step.

Preferred forms:

```powershell
<helper> "colcon list"
<helper> "colcon build --symlink-install"
<helper> "colcon build --symlink-install --packages-select <package>"
```

When a build fails, inspect package logs under:

```text
log/latest_build/<package>/stderr.log
log/build_*/<package>/stderr.log
```

Classify failures separately: missing dependencies, CMake/package metadata errors, compile errors, stale artifacts, install-space staleness, and environment sourcing problems.

Do not delete `build/`, `install/`, or `log/` without verified workspace-contained paths and user approval.

## Path Mapping

Use path mapping when output references the wrong side of the workspace.

Map local to remote:

```powershell
python <skill_dir>\scripts\sshfs_exec.py --workspace <UNC workspace> --map-path <local path> --to remote
```

Map remote to local:

```powershell
python <skill_dir>\scripts\sshfs_exec.py --workspace <UNC workspace> --map-path <remote path> --to local
```

If a path is outside the known workspace root, report the mismatch instead of guessing.

## SSH Authentication

Direct SSH is an explicit exception, not a default fallback.

If the user explicitly requests raw SSH, or approves raw SSH after helper-based execution is unavailable, request the narrowest approval for the current device, such as:

```text
["ssh", "user@host"]
```

Do not request broad `["ssh"]` approval.

Do not use direct SSH approval merely as an initial probe for configured helper workspaces.

If SSH reaches the host but returns `Permission denied`, stop and report missing authentication. Do not create keys, edit `authorized_keys`, change SSH config, or alter user environment unless the user explicitly asks.

## Performance

Treat SSHFS as a file view, not an execution/indexing layer.

Avoid broad Windows-side scans over SSHFS, especially:

- recursive full-workspace search;
- `git status`;
- colcon build;
- ROS commands;
- build/install/log traversal.

Run heavy search, git, build, launch, logs, topics, and TF checks on the remote host.

## Reporting

For remote tasks, report:

- execution entry used: workspace helper, generic helper, or direct SSH;
- remote workspace path;
- key command;
- relevant nodes/topics/logs;
- warnings or errors;
- whether cleanup was performed;
- whether any background process remains.

Distinguish local Windows paths from remote Linux paths.

## Maintenance

Keep project-specific device details out of this generic skill. Put hostnames, IPs, package names, launch files, and preferred helper paths in `.codex-remote-dev.yaml` or workspace `AGENTS.md`.

Keep long GUI instructions, examples, and troubleshooting details in `references/`.
