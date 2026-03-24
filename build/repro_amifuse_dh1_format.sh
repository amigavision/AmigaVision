#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  repro_amifuse_dh1_format.sh [options]

Creates a fresh two-partition PDS3 RDB HDF, then runs:
  amifuse format <image> DH0 Amiga
  amifuse format <image> DH1 Data
  amifuse mount --write <image> DH1
  mkdir + rsync against the mounted DH1 volume

Options:
  --out-dir <dir>      Output directory for the repro image and logs
  --amifuse <bin>      Path to amifuse binary
  --rdbtool <bin>      Path to rdbtool binary
  --pfs3 <file>        Path to pfs3.bin
  --dh0-mb <mb>        Approximate DH0 size in MiB (default: 636)
  --dh1-mb <mb>        Approximate DH1 size in MiB (default: 8851)
  -h, --help           Show this help
EOF
}

OUT_DIR="${TMPDIR:-/tmp}/amifuse-repro"
AMIFUSE_BIN="${HOME}/Library/Caches/AmigaVision/amifuse-venv/bin/amifuse"
RDBTOOL_BIN="${HOME}/Library/Caches/AmigaVision/amifuse-venv/bin/rdbtool"
PFS3_BIN="$(cd "$(dirname "$0")/.." && pwd)/data/pfs3/pfs3.bin"
DH0_MB=636
DH1_MB=8851
MOUNT_BIN="/sbin/mount"
DISKUTIL_BIN="/usr/sbin/diskutil"
UMOUNT_BIN="/sbin/umount"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --amifuse)
      AMIFUSE_BIN="$2"
      shift 2
      ;;
    --rdbtool)
      RDBTOOL_BIN="$2"
      shift 2
      ;;
    --pfs3)
      PFS3_BIN="$2"
      shift 2
      ;;
    --dh0-mb)
      DH0_MB="$2"
      shift 2
      ;;
    --dh1-mb)
      DH1_MB="$2"
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

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "error: file not found: $1" >&2
    exit 1
  fi
}

CYL_HEADS=16
CYL_SECTORS=63
SECTOR_SIZE=512
CYL_SIZE=$((SECTOR_SIZE * CYL_HEADS * CYL_SECTORS))
RDB_CYLS=1

require_file "$AMIFUSE_BIN"
require_file "$RDBTOOL_BIN"
require_file "$PFS3_BIN"

mkdir -p "$OUT_DIR"
HDF_PATH="$OUT_DIR/repro-pds3-two-partition.hdf"
DH0_LOG="$OUT_DIR/amifuse-format-dh0.log"
DH1_LOG="$OUT_DIR/amifuse-format-dh1.log"
RDB_LOG="$OUT_DIR/rdbtool-layout.log"
MOUNT_LOG="$OUT_DIR/amifuse-mount-dh1.log"
RSYNC_LOG="$OUT_DIR/rsync-dh1.log"
SRC_DIR="$OUT_DIR/src"
MOUNTPOINT="$OUT_DIR/mnt-dh1"
TEST_DIR="$MOUNTPOINT/probe-dir"

dh0_cyls=$(((DH0_MB * 1024 * 1024 + CYL_SIZE - 1) / CYL_SIZE))
dh1_cyls=$(((DH1_MB * 1024 * 1024 + CYL_SIZE - 1) / CYL_SIZE))
total_cyls=$((RDB_CYLS + dh0_cyls + dh1_cyls))
chs_cyls=$((total_cyls + 1))
dh0_start=$RDB_CYLS
dh1_start=$((dh0_start + dh0_cyls))

rm -f "$HDF_PATH" "$DH0_LOG" "$DH1_LOG" "$RDB_LOG"
rm -f "$MOUNT_LOG" "$RSYNC_LOG"
rm -rf "$SRC_DIR" "$MOUNTPOINT"

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
    wait_for_unmount "$mountpoint" || true
  fi
}

MOUNT_PID=""
cleanup() {
  umount_mountpoint "$MOUNTPOINT"
  if [[ -n "$MOUNT_PID" ]]; then
    wait "$MOUNT_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "Creating repro HDF:"
echo "  output: $HDF_PATH"
echo "  geometry: ${chs_cyls} cylinders, ${CYL_HEADS} heads, ${CYL_SECTORS} sectors"
echo "  DH0: ~${DH0_MB} MiB (${dh0_cyls} cylinders)"
echo "  DH1: ~${DH1_MB} MiB (${dh1_cyls} cylinders)"
echo ""

"$RDBTOOL_BIN" "$HDF_PATH" \
  create \
  "chs=${chs_cyls},${CYL_HEADS},${CYL_SECTORS}" \
  + init \
  "rdb_cyls=${RDB_CYLS}" \
  "rdb_flags=0x2"

"$RDBTOOL_BIN" "$HDF_PATH" fsadd "$PFS3_BIN" fs=PDS3

"$RDBTOOL_BIN" "$HDF_PATH" \
  add "name=DH0" "start=${dh0_start}" "size=${dh0_cyls}" \
  "interleave=65536" "fs=PDS3" "bs=512" \
  "max_transfer=0x0001FE00" "mask=0x7FFFFFFE" "num_buffer=128" \
  "bootable=True" "pri=1"

"$RDBTOOL_BIN" "$HDF_PATH" \
  add "name=DH1" "start=${dh1_start}" "size=${dh1_cyls}" \
  "interleave=65536" "fs=PDS3" "bs=512" \
  "max_transfer=0x0001FE00" "mask=0x7FFFFFFE" "num_buffer=128"

{
  echo "=== rdbtool info ==="
  "$RDBTOOL_BIN" "$HDF_PATH" info
  echo
  echo "=== rdbtool free ==="
  "$RDBTOOL_BIN" "$HDF_PATH" free
} >"$RDB_LOG" 2>&1

echo "Formatting DH0..."
if "$AMIFUSE_BIN" format "$HDF_PATH" DH0 Amiga >"$DH0_LOG" 2>&1; then
  echo "  DH0 format: success"
else
  echo "  DH0 format: failed"
fi

echo "Formatting DH1..."
if "$AMIFUSE_BIN" format "$HDF_PATH" DH1 Data >"$DH1_LOG" 2>&1; then
  echo "  DH1 format: success"
else
  echo "  DH1 format: failed"
fi

mkdir -p "$SRC_DIR/Subdir"
printf '%s\n' "hello from amifuse repro" > "$SRC_DIR/root.txt"
printf '%s\n' "nested file" > "$SRC_DIR/Subdir/nested.txt"
mkdir -p "$MOUNTPOINT"

echo "Mounting DH1 in write mode..."
if "$AMIFUSE_BIN" mount "$HDF_PATH" --write --partition DH1 --volname Data --mountpoint "$MOUNTPOINT" >"$MOUNT_LOG" 2>&1 & then
  MOUNT_PID=$!
else
  MOUNT_PID=""
fi

if wait_for_mount "$MOUNTPOINT"; then
  echo "  DH1 mount: success"
else
  echo "  DH1 mount: failed"
fi

echo "Creating test directory on mounted DH1..."
if mkdir "$TEST_DIR" >>"$RSYNC_LOG" 2>&1; then
  echo "  mkdir on DH1: success"
else
  echo "  mkdir on DH1: failed"
fi

echo "Copying tiny test tree to mounted DH1..."
if rsync -a "$SRC_DIR"/ "$MOUNTPOINT"/ >>"$RSYNC_LOG" 2>&1; then
  echo "  rsync to DH1: success"
else
  echo "  rsync to DH1: failed"
fi

echo ""
echo "Logs:"
echo "  $RDB_LOG"
echo "  $DH0_LOG"
echo "  $DH1_LOG"
echo "  $MOUNT_LOG"
echo "  $RSYNC_LOG"
