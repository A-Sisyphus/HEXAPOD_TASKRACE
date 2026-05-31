@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0remote_ros2.ps1" %*
