#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  pi_image.sh --hdf <AmigaVision.hdf> --output-img <out.img> [options]

Options:
  --keep-mounted       Leave image attached and mounted for debugging
  -h, --help           Show this help

Notes:
  - Set REPLAYOS_BASE_IMG in the environment to a RePlayOS image file or a directory
    containing a RePlayOS*.img.zst, *.img.gz, or *.img image.
  - The base must already contain a replay partition large enough for the HDF plus 100 MiB.
  - Compressed bases are unpacked beside the output; the base itself is never mounted or modified.
  - If your base image does not have that partition yet, boot it once on hardware first and
    re-use that initialized image as your base.
EOF
}

BASE_IMG="${REPLAYOS_BASE_IMG:-}"
HDF_PATH=""
OUTPUT_IMG=""
WORK_IMG=""
PAYLOAD_DIR="./replay"
BIOS_DIR="${REPLAYOS_BIOS_DIR:-}"
KEEP_MOUNTED=0
BUILD_COMPLETE=0

timed_run() {
  local label="$1"
  shift
  local started=$SECONDS status=0
  "$@" || status=$?
  printf 'Timing: RPi %s: %ss\n' "$label" "$((SECONDS - started))" >&2
  return "$status"
}

resolve_tool() {
  local preferred_path="$1"
  local tool_name="$2"

  if [[ -x "$preferred_path" ]]; then
    printf '%s\n' "$preferred_path"
    return 0
  fi

  command -v "$tool_name" 2>/dev/null || true
}

HDIUTIL_BIN="${HDIUTIL_BIN:-$(resolve_tool /usr/bin/hdiutil hdiutil)}"
DISKUTIL_BIN="${DISKUTIL_BIN:-$(resolve_tool /usr/sbin/diskutil diskutil)}"
CP_BIN="${CP_BIN:-$(resolve_tool /bin/cp cp)}"
RSYNC_BIN="${RSYNC_BIN:-$(resolve_tool /usr/bin/rsync rsync)}"
STAT_BIN="${STAT_BIN:-$(resolve_tool /usr/bin/stat stat)}"
AWK_BIN="${AWK_BIN:-$(resolve_tool /usr/bin/awk awk)}"
MKTEMP_BIN="${MKTEMP_BIN:-$(resolve_tool /usr/bin/mktemp mktemp)}"

resolve_base_img() {
  local input_path="$1"

  if [[ -f "$input_path" ]]; then
    printf '%s\n' "$input_path"
    return 0
  fi

  if [[ -d "$input_path" ]]; then
    local candidate newest="" newest_mtime=0 mtime
    shopt -s nullglob
    for candidate in "$input_path"/RePlayOS*.img.zst "$input_path"/RePlayOS*.img.gz "$input_path"/RePlayOS*.img; do
      [[ -f "$candidate" ]] || continue
      mtime="$("$STAT_BIN" -f '%m' "$candidate")"
      if [[ -z "$newest" || "$mtime" -gt "$newest_mtime" ]]; then
        newest="$candidate"
        newest_mtime="$mtime"
      fi
    done
    shopt -u nullglob
    if [[ -n "$newest" ]]; then
      printf '%s\n' "$newest"
      return 0
    fi
    echo "error: no RePlayOS image (.img.zst, .img.gz, .img) found in: $input_path" >&2
    return 1
  fi

  echo "error: base image not found: $input_path" >&2
  return 1
}

find_replay_partition() {
  local raw_disk="$1"
  local candidate_ids=()
  local candidate_id info volume_name fs_personality

  while IFS= read -r candidate_id; do
    [[ -n "$candidate_id" ]] || continue
    candidate_ids+=("$candidate_id")
  done < <("$DISKUTIL_BIN" list "$raw_disk" | "$AWK_BIN" '/disk[0-9]+s[0-9]+$/ { print $NF }')

  for candidate_id in "${candidate_ids[@]}"; do
    info="$("$DISKUTIL_BIN" info "/dev/$candidate_id")"
    volume_name="$(printf '%s\n' "$info" | "$AWK_BIN" -F': *' '/Volume Name:/ { print $2; exit }')"
    fs_personality="$(printf '%s\n' "$info" | "$AWK_BIN" -F': *' '/File System Personality:/ { print $2; exit }')"
    if [[ "$volume_name" == "replay" ]]; then
      printf '%s\n' "$candidate_id"
      return 0
    fi
    if [[ "$fs_personality" == "ExFAT" ]]; then
      printf '%s\n' "$candidate_id"
      return 0
    fi
  done

  for candidate_id in "${candidate_ids[@]}"; do
    info="$("$DISKUTIL_BIN" info "/dev/$candidate_id")"
    fs_personality="$(printf '%s\n' "$info" | "$AWK_BIN" -F': *' '/File System Personality:/ { print $2; exit }')"
    if [[ "$fs_personality" == "MS-DOS FAT32" ]]; then
      printf '%s\n' "$candidate_id"
      return 0
    fi
  done

  return 1
}

clone_base_img() {
  local source_img="$1"
  local output_img="$2"

  case "$source_img" in
    *.zst)
      command -v zstd >/dev/null || { echo "error: zstd is required to unpack $source_img" >&2; return 1; }
      zstd -d --sparse -q -c "$source_img" >"$output_img"
      return
      ;;
    *.gz)
      gzip -d -c "$source_img" >"$output_img"
      return
      ;;
  esac

  if [[ -n "$CP_BIN" && -x "$CP_BIN" ]]; then
    if "$CP_BIN" -c "$source_img" "$output_img" 2>/dev/null; then
      echo "Cloned base image using copy-on-write."
      return 0
    fi
  fi

  echo "Copy-on-write clone unavailable, falling back to rsync copy..."
  "$RSYNC_BIN" -ah --progress "$source_img" "$output_img"
}

rsync_clean() {
  COPYFILE_DISABLE=1 "$RSYNC_BIN" --exclude ".DS_Store" --exclude "._*" "$@"
}

purge_macos_metadata() {
  local root="$1"
  find "$root" \( -name '.DS_Store' -o -name '._*' \) -delete
}

cleanup_stale_output_artifacts() {
  local output_img="$1"
  local output_dir output_name

  output_dir="$(dirname "$output_img")"
  output_name="$(basename "$output_img")"

  rm -f "$output_img".partial.*
  rm -f "$output_dir"/."$output_name".*
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hdf)
      HDF_PATH="$2"
      shift 2
      ;;
    --output-img)
      OUTPUT_IMG="$2"
      shift 2
      ;;
    --keep-mounted)
      KEEP_MOUNTED=1
      shift
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

if [[ -z "$BASE_IMG" || -z "$HDF_PATH" || -z "$OUTPUT_IMG" ]]; then
  echo "error: REPLAYOS_BASE_IMG plus --hdf and --output-img are required" >&2
  usage
  exit 1
fi

for required_bin in \
  "$HDIUTIL_BIN" \
  "$DISKUTIL_BIN" \
  "$CP_BIN" \
  "$RSYNC_BIN" \
  "$STAT_BIN" \
  "$AWK_BIN" \
  "$MKTEMP_BIN"
do
  if [[ -z "$required_bin" || ! -x "$required_bin" ]]; then
    echo "error: required system tool not found: $required_bin" >&2
    exit 1
  fi
done

BASE_IMG="$(resolve_base_img "$BASE_IMG")"
echo "Using RePlayOS base image: $BASE_IMG"

if [[ ! -f "$HDF_PATH" ]]; then
  echo "error: AmigaVision HDF not found: $HDF_PATH" >&2
  exit 1
fi

if [[ ! -d "$PAYLOAD_DIR" ]]; then
  echo "error: payload dir not found: $PAYLOAD_DIR" >&2
  exit 1
fi

if [[ -n "$BIOS_DIR" && ! -d "$BIOS_DIR" ]]; then
  echo "error: BIOS dir not found: $BIOS_DIR" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_IMG")"
cleanup_stale_output_artifacts "$OUTPUT_IMG"
RAW_DISK=""
MOUNT_POINT=""

cleanup() {
  if [[ "$KEEP_MOUNTED" -eq 1 ]]; then
    return
  fi

  if [[ -n "$MOUNT_POINT" && -d "$MOUNT_POINT" ]]; then
    "$DISKUTIL_BIN" unmount "$MOUNT_POINT" >/dev/null 2>&1 || true
    rmdir "$MOUNT_POINT" >/dev/null 2>&1 || true
  fi

  if [[ -n "$RAW_DISK" ]]; then
    "$HDIUTIL_BIN" detach "$RAW_DISK" >/dev/null 2>&1 || true
  fi

  if [[ "$BUILD_COMPLETE" -ne 1 && -n "$WORK_IMG" && -e "$WORK_IMG" ]]; then
    rm -f "$WORK_IMG" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT
WORK_IMG="$OUTPUT_IMG.partial.$$"
echo "Preparing temporary RePlayOS image on output storage..."
timed_run "unpack/clone blank base" clone_base_img "$BASE_IMG" "$WORK_IMG"

ATTACH_OUTPUT="$(timed_run "attach image" "$HDIUTIL_BIN" attach -imagekey diskimage-class=CRawDiskImage -nomount "$WORK_IMG")"
RAW_DISK="$("$AWK_BIN" 'NR==1 {print $1}' <<<"$ATTACH_OUTPUT")"

if [[ -z "$RAW_DISK" ]]; then
  echo "error: failed to attach image: $WORK_IMG" >&2
  echo "$ATTACH_OUTPUT" >&2
  exit 1
fi

REPLAY_PARTITION="$(find_replay_partition "$RAW_DISK" || true)"

if [[ -z "$REPLAY_PARTITION" ]]; then
  echo "error: no writable replay partition found in base image: $BASE_IMG" >&2
  echo "hint: boot RePlayOS once to initialize storage, then re-use that initialized image in REPLAYOS_BASE_IMG" >&2
  exit 1
fi

MOUNT_POINT="$("$MKTEMP_BIN" -d /tmp/amigavision-replay.XXXXXX)"
timed_run "mount replay partition" "$DISKUTIL_BIN" mount -mountPoint "$MOUNT_POINT" "/dev/$REPLAY_PARTITION" >/dev/null

timed_run "copy support files" rsync_clean -a "$PAYLOAD_DIR"/ "$MOUNT_POINT"/
if [[ -n "$BIOS_DIR" ]]; then
  mkdir -p "$MOUNT_POINT/bios"
  timed_run "copy BIOS files" rsync_clean -a "$BIOS_DIR"/ "$MOUNT_POINT/bios"/
fi
mkdir -p "$MOUNT_POINT/roms/commodore_ami"
# The filesystem, not just the raw container, must have room for the payload.
HDF_BYTES="$("$STAT_BIN" -f '%z' "$HDF_PATH")"
FREE_KB="$(df -Pk "$MOUNT_POINT" | "$AWK_BIN" 'NR==2 {print $4}')"
REQUIRED_BYTES=$((HDF_BYTES + 100 * 1024 * 1024))
if [[ $((FREE_KB * 1024)) -lt "$REQUIRED_BYTES" ]]; then
  echo "error: replay partition needs $REQUIRED_BYTES free bytes for the HDF plus 100 MiB; resize the blank base filesystem first" >&2
  exit 1
fi
echo "Copying AmigaVision.hdf into replay image..."
COPYFILE_DISABLE=1 timed_run "copy AmigaVision HDF" "$RSYNC_BIN" -ah --progress --exclude "._*" "$HDF_PATH" "$MOUNT_POINT/roms/commodore_ami/AmigaVision.hdf"
timed_run "remove macOS metadata" purge_macos_metadata "$MOUNT_POINT"
timed_run "flush filesystem" sync

if [[ "$KEEP_MOUNTED" -eq 1 ]]; then
  BUILD_COMPLETE=1
  echo "Image mounted for debugging:"
  echo "  disk: $RAW_DISK"
  echo "  partition: /dev/$REPLAY_PARTITION"
  echo "  mount point: $MOUNT_POINT"
  echo "  image path: $WORK_IMG"
  trap - EXIT
  exit 0
fi

# Flush and detach before publishing or allowing the caller to compress it.
timed_run "unmount replay partition" "$DISKUTIL_BIN" unmount "$MOUNT_POINT" >/dev/null
rmdir "$MOUNT_POINT"
MOUNT_POINT=""
timed_run "detach image" "$HDIUTIL_BIN" detach "$RAW_DISK" >/dev/null
RAW_DISK=""
rm -f "$OUTPUT_IMG"
mv "$WORK_IMG" "$OUTPUT_IMG"
BUILD_COMPLETE=1

echo "Created flashable image: $OUTPUT_IMG"
