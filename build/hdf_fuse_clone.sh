#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  hdf_fuse_clone.sh --hdf <image.hdf> --src-root <dir> [options]

Options:
  --amifuse <bin>    Path to amifuse binary (default: $AMIFUSEBIN or amifuse)
  --temp-root <dir>  Build temp root containing boot.adf/cfg.fs-uae/clone (default: $AGSTEMP)
  --cache-root <dir> Cache root for formatted blank templates
  -h, --help         Show this help
EOF
}

HDF_PATH=""
SRC_ROOT=""
AMIFUSE_BIN="${AMIFUSEBIN:-amifuse}"
TEMP_ROOT="${AGSTEMP:-}"
CACHE_ROOT="${HOME}/Library/Caches/AmigaVision/pfs-template"
MOUNT_ROOT="/private/tmp/amigavision-build/mnt"
MOUNT_DH0="${MOUNT_ROOT}/Amiga"
MOUNT_DH1="${MOUNT_ROOT}/Data"
MOUNT_BIN="/sbin/mount"
DISKUTIL_BIN="/usr/sbin/diskutil"
UMOUNT_BIN="/sbin/umount"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hdf)
      HDF_PATH="$2"
      shift 2
      ;;
    --src-root)
      SRC_ROOT="$2"
      shift 2
      ;;
    --amifuse)
      AMIFUSE_BIN="$2"
      shift 2
      ;;
    --temp-root)
      TEMP_ROOT="$2"
      shift 2
      ;;
    --cache-root)
      CACHE_ROOT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$HDF_PATH" || -z "$SRC_ROOT" ]]; then
  echo "error: --hdf and --src-root are required" >&2
  usage
  exit 1
fi

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "error: file not found: $1" >&2
    exit 1
  fi
}

require_dir() {
  if [[ ! -d "$1" ]]; then
    echo "error: directory not found: $1" >&2
    exit 1
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: command not found: $1" >&2
    exit 1
  fi
}

kill_mount_processes() {
  local mountpoint="$1"
  pkill -f "${AMIFUSE_BIN} mount .* --mountpoint ${mountpoint}" >/dev/null 2>&1 || true
}

check_mountpoint_clear() {
  local mountpoint="$1"
  local mount_line=""
  mount_line="$("$MOUNT_BIN" | grep -F " on ${mountpoint} " || true)"
  if [[ -n "$mount_line" ]]; then
    if [[ "$mount_line" == amifuse:* ]]; then
      kill_mount_processes "$mountpoint"
      umount_mountpoint "$mountpoint"
      mount_line="$("$MOUNT_BIN" | grep -F " on ${mountpoint} " || true)"
    fi
  fi
  if [[ -n "$mount_line" ]]; then
    echo "error: mount point already in use: ${mountpoint}" >&2
    exit 1
  fi
  if [[ -e "$mountpoint" ]]; then
    if [[ -d "$mountpoint" ]]; then
      rmdir "$mountpoint" >/dev/null 2>&1 || true
    fi
  fi
  if [[ -e "$mountpoint" ]]; then
    echo "error: mount point already exists: ${mountpoint}" >&2
    exit 1
  fi
}

wait_for_mount() {
  local mountpoint="$1"
  local waited=0
  while (( waited < 30 )); do
    if "$MOUNT_BIN" | grep -F " on ${mountpoint} " >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  return 1
}

wait_for_unmount() {
  local mountpoint="$1"
  local waited=0
  while (( waited < 30 )); do
    if ! "$MOUNT_BIN" | grep -F " on ${mountpoint} " >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  return 1
}

umount_mountpoint() {
  local mountpoint="$1"
  if "$MOUNT_BIN" | grep -F " on ${mountpoint} " >/dev/null 2>&1; then
    "$DISKUTIL_BIN" unmount "$mountpoint" >/dev/null 2>&1 || "$UMOUNT_BIN" "$mountpoint" >/dev/null 2>&1 || true
    if ! wait_for_unmount "$mountpoint"; then
      kill_mount_processes "$mountpoint"
      "$UMOUNT_BIN" "$mountpoint" >/dev/null 2>&1 || true
      wait_for_unmount "$mountpoint" || true
    fi
  fi
}

probe_mount_writable() {
  local mountpoint="$1"
  local logfile="$2"
  local probe_dir="$mountpoint/AmigaVisionWriteProbe-$$"
  {
    echo "[probe] mountpoint=$mountpoint"
    ls -ld "$mountpoint" 2>&1 || true
    stat -f '[probe] mode=%Sp uid=%u gid=%g inode=%i' "$mountpoint" 2>&1 || true
    if mkdir "$probe_dir"; then
      echo "[probe] mkdir rc=0 path=$probe_dir"
      rmdir "$probe_dir" >/dev/null 2>&1 || true
      return 0
    fi
    local rc=$?
    echo "[probe] mkdir rc=$rc path=$probe_dir"
    return 1
  } >>"$logfile" 2>&1
}

DH0_PID=""
DH1_PID=""
cleanup() {
  umount_mountpoint "$MOUNT_DH1"
  umount_mountpoint "$MOUNT_DH0"
  if [[ -n "$DH1_PID" ]]; then
    kill "$DH1_PID" >/dev/null 2>&1 || true
    wait "$DH1_PID" 2>/dev/null || true
    DH1_PID=""
  fi
  if [[ -n "$DH0_PID" ]]; then
    kill "$DH0_PID" >/dev/null 2>&1 || true
    wait "$DH0_PID" 2>/dev/null || true
    DH0_PID=""
  fi
}
trap cleanup EXIT

require_file "$HDF_PATH"
require_dir "$SRC_ROOT"
require_dir "$SRC_ROOT/DH0"
require_dir "$SRC_ROOT/DH1"

if ! command -v "$AMIFUSE_BIN" >/dev/null 2>&1; then
  echo "error: amifuse not found: $AMIFUSE_BIN" >&2
  exit 1
fi

if [[ ! -d "/Library/Filesystems/macfuse.fs" ]] && ! pkgutil --pkgs | grep -qi macfuse; then
  echo "error: macFUSE does not appear to be installed" >&2
  exit 1
fi

check_mountpoint_clear "$MOUNT_DH0"
check_mountpoint_clear "$MOUNT_DH1"

mkdir -p "$CACHE_ROOT"
mkdir -p "$MOUNT_ROOT"

mount_with_amifuse() {
  local mountpoint="$1"
  local partition="$2"
  local volname="$3"
  local logfile="$4"
  "$AMIFUSE_BIN" mount "$HDF_PATH" \
    --write \
    --debug \
    --partition "$partition" \
    --volname "$volname" \
    --mountpoint "$mountpoint" \
    >"$logfile" 2>&1 &
  local pid=$!
  if ! wait_for_mount "$mountpoint"; then
    wait "$pid" || true
    return 1
  fi
  echo "$pid"
}

mount_and_probe_partition() {
  local mountpoint="$1"
  local partition="$2"
  local volname="$3"
  local logfile="$4"
  local pid_var="$5"
  local pid=""

  pid="$(mount_with_amifuse "$mountpoint" "$partition" "$volname" "$logfile")" || return 1
  printf -v "$pid_var" '%s' "$pid"
  probe_mount_writable "$mountpoint" "$logfile" || return 1
  return 0
}

format_template_with_fsuae() {
  local dh0_log="$TEMP_ROOT/amifuse-format-dh0.log"
  local dh1_log="$TEMP_ROOT/amifuse-format-dh1.log"
  if ! "$AMIFUSE_BIN" format "$HDF_PATH" DH0 Amiga >"$dh0_log" 2>&1; then
    echo "error: failed to format DH0 via amifuse" >&2
    cat "$dh0_log" >&2
    return 1
  fi
  if ! "$AMIFUSE_BIN" format "$HDF_PATH" DH1 Data >"$dh1_log" 2>&1; then
    echo "error: failed to format DH1 via amifuse" >&2
    cat "$dh1_log" >&2
    return 1
  fi
}

ensure_formatted_template() {
  local template_key
  template_key="$(shasum -a 1 "$HDF_PATH" | awk '{print $1}')"
  local template_path="$CACHE_ROOT/${template_key}.hdf"

  if [[ -f "$template_path" ]]; then
    echo "Restoring formatted template cache..."
    cp -f "$template_path" "$HDF_PATH"
    return 0
  fi

  format_template_with_fsuae
  echo "Saving formatted template cache..."
  cp -f "$HDF_PATH" "$template_path"
}

clone_partition() {
  local src_dir="$1"
  local mountpoint="$2"
  local partition="$3"
  local volname="$4"
  local logfile="$5"
  local pid_var="$6"

  check_mountpoint_clear "$mountpoint"
  mount_and_probe_partition "$mountpoint" "$partition" "$volname" "$logfile" "$pid_var" || return 1
  rsync -a --delete --exclude '*.uaem' --exclude '.DS_Store' "$src_dir"/ "$mountpoint"/
  sync
  umount_mountpoint "$mountpoint"
  if [[ "$pid_var" == "DH0_PID" ]]; then
    DH0_PID=""
  else
    DH1_PID=""
  fi
  return 0
}

run_clone_pass() {
  local log_root="$TEMP_ROOT"
  mkdir -p "$log_root"
  clone_partition "$SRC_ROOT/DH0" "$MOUNT_DH0" "DH0" "Amiga" "$log_root/amifuse-dh0.log" "DH0_PID" || return 1
  clone_partition "$SRC_ROOT/DH1" "$MOUNT_DH1" "DH1" "Data" "$log_root/amifuse-dh1.log" "DH1_PID" || return 1
  return 0
}

if ! run_clone_pass; then
  echo "Direct amifuse mount failed, falling back to formatted template cache..."
  cleanup
  ensure_formatted_template
  if ! run_clone_pass; then
    echo "error: amifuse mount failed even after formatting fallback" >&2
    exit 1
  fi
fi
