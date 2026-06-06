#!/usr/bin/env bash
set -Eeuo pipefail

WORKSPACE="/home/jetson/task_race_ws"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${WORKSPACE}/log/tf_odom_check_${RUN_ID}"
mkdir -p "${LOG_DIR}"

set +u
source /opt/ros/humble/setup.bash
source "${WORKSPACE}/install/setup.bash"
set -u

declare -a PIDS=()

start_launch() {
  local name="$1"
  shift
  setsid bash -lc "$*" >"${LOG_DIR}/${name}.log" 2>&1 &
  local pid="$!"
  PIDS+=("${pid}")
  echo "[start] ${name} pid=${pid}"
}

cleanup() {
  echo "[cleanup] stopping launched process groups"
  for pid in "${PIDS[@]:-}"; do
    kill -INT "-${pid}" 2>/dev/null || true
  done
  sleep 3
  for pid in "${PIDS[@]:-}"; do
    kill -TERM "-${pid}" 2>/dev/null || true
  done
  ros2 daemon stop >/dev/null 2>&1 || true
  ros2 daemon start >/dev/null 2>&1 || true
}
trap cleanup EXIT

capture() {
  local name="$1"
  shift
  {
    echo "$ $*"
    "$@"
  } >"${LOG_DIR}/${name}.txt" 2>&1 || true
}

echo "LOG_DIR=${LOG_DIR}"
ros2 daemon stop >/dev/null 2>&1 || true
ros2 daemon start >/dev/null 2>&1 || true

start_launch lidar "ros2 launch lslidar_driver lsn10_launch.py"
sleep 7
start_launch ekf "ros2 launch hexapod_navigation2 laser_imu_ekf.launch.py"
sleep 25

capture node_list ros2 node list
capture topic_list ros2 topic list
capture scan_info ros2 topic info /scan -v
capture odom_info ros2 topic info /odom -v
capture tf_info ros2 topic info /tf -v
capture tf_static_info ros2 topic info /tf_static -v
capture scan_hz timeout 8 ros2 topic hz /scan
capture odom_once timeout 8 ros2 topic echo --once /odom
capture tf_odom_base_link timeout 8 ros2 run tf2_ros tf2_echo odom base_link
capture tf_base_laser timeout 8 ros2 run tf2_ros tf2_echo base_link laser

echo "--- nodes ---"
cat "${LOG_DIR}/node_list.txt"
echo "--- topics ---"
grep -E '^/(scan|odom|odom_rf2o|odom_rf2o_raw|tf|tf_static|imu/yaw_pose|euler_only)$' \
  "${LOG_DIR}/topic_list.txt" || true
echo "--- /odom info ---"
cat "${LOG_DIR}/odom_info.txt"
echo "--- odom -> base_link ---"
cat "${LOG_DIR}/tf_odom_base_link.txt"
echo "--- base_link -> laser ---"
cat "${LOG_DIR}/tf_base_laser.txt"
echo "--- scan hz ---"
cat "${LOG_DIR}/scan_hz.txt"
