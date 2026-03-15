#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  pi_image.sh --base-img <replayos.img> --hdf <AmigaVision.hdf> --output-img <out.img> [options]

Options:
  --payload-dir <dir>  Directory to copy to replay partition (default: ./replay)
  --size <size>        Final raw image size passed to truncate (default: 16g)
  --keep-mounted       Leave image attached and mounted for debugging
  -h, --help           Show this help

Notes:
  - This script expects a RePlayOS image that already contains a writable replay partition.
  - If your base image does not have that partition yet, boot it once on hardware first and
    re-use that initialized image as your base.
EOF
}

BASE_IMG=""
HDF_PATH=""
OUTPUT_IMG=""
PAYLOAD_DIR="./replay"
IMAGE_SIZE="16g"
KEEP_MOUNTED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-img)
      BASE_IMG="$2"
      shift 2
      ;;
    --hdf)
      HDF_PATH="$2"
      shift 2
      ;;
    --output-img)
      OUTPUT_IMG="$2"
      shift 2
      ;;
    --payload-dir)
      PAYLOAD_DIR="$2"
      shift 2
      ;;
    --size)
      IMAGE_SIZE="$2"
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
  echo "error: --base-img, --hdf, and --output-img are required" >&2
  usage
  exit 1
fi

if [[ ! -f "$BASE_IMG" ]]; then
  echo "error: base image not found: $BASE_IMG" >&2
  exit 1
fi

if [[ ! -f "$HDF_PATH" ]]; then
  echo "error: AmigaVision HDF not found: $HDF_PATH" >&2
  exit 1
fi

if [[ ! -d "$PAYLOAD_DIR" ]]; then
  echo "error: payload dir not found: $PAYLOAD_DIR" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_IMG")"
cp -f "$BASE_IMG" "$OUTPUT_IMG"
truncate -s "$IMAGE_SIZE" "$OUTPUT_IMG"

RAW_DISK=""
MOUNT_POINT=""

cleanup() {
  if [[ "$KEEP_MOUNTED" -eq 1 ]]; then
    return
  fi

  if [[ -n "$MOUNT_POINT" && -d "$MOUNT_POINT" ]]; then
    diskutil unmount "$MOUNT_POINT" >/dev/null 2>&1 || true
    rmdir "$MOUNT_POINT" >/dev/null 2>&1 || true
  fi

  if [[ -n "$RAW_DISK" ]]; then
    hdiutil detach "$RAW_DISK" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

ATTACH_OUTPUT="$(hdiutil attach -imagekey diskimage-class=CRawDiskImage -nomount "$OUTPUT_IMG")"
RAW_DISK="$(awk 'NR==1 {print $1}' <<<"$ATTACH_OUTPUT")"

if [[ -z "$RAW_DISK" ]]; then
  echo "error: failed to attach image: $OUTPUT_IMG" >&2
  echo "$ATTACH_OUTPUT" >&2
  exit 1
fi

REPLAY_PARTITION="$(diskutil list "$RAW_DISK" | awk '
  /ExFAT|FAT32|MS-DOS FAT|Microsoft Basic Data/ { candidate=$NF }
  END { print candidate }
')"

if [[ -z "$REPLAY_PARTITION" ]]; then
  echo "error: no writable replay partition found in base image: $BASE_IMG" >&2
  echo "hint: boot RePlayOS once to initialize storage, then re-use that image as --base-img" >&2
  exit 1
fi

MOUNT_POINT="$(mktemp -d /tmp/amigavision-replay.XXXXXX)"
diskutil mount -mountPoint "$MOUNT_POINT" "/dev/$REPLAY_PARTITION" >/dev/null

rsync -a --delete --exclude ".DS_Store" "$PAYLOAD_DIR"/ "$MOUNT_POINT"/
mkdir -p "$MOUNT_POINT/roms/commodore_ami"
cp -f "$HDF_PATH" "$MOUNT_POINT/roms/commodore_ami/AmigaVision.hdf"
sync

if [[ "$KEEP_MOUNTED" -eq 1 ]]; then
  echo "Image mounted for debugging:"
  echo "  disk: $RAW_DISK"
  echo "  partition: /dev/$REPLAY_PARTITION"
  echo "  mount point: $MOUNT_POINT"
  trap - EXIT
fi

echo "Created flashable image: $OUTPUT_IMG"
