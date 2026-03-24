#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  hdf_hst_clone.sh --hdf <image.hdf> --src-root <dir> [options]

Options:
  --hst-amiga <bin>   Path to hst-amiga-pfs binary (default: $HSTAMIGABIN or hst-amiga-pfs)
  --log-dir <dir>     Directory for logs
  --dry-run           Print commands without executing
  -h, --help          Show this help
EOF
}

HDF_PATH=""
SRC_ROOT=""
HST_AMIGA_BIN="${HSTAMIGABIN:-hst-amiga-pfs}"
LOG_DIR=""
DRY_RUN=0

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
    --hst-amiga)
      HST_AMIGA_BIN="$2"
      shift 2
      ;;
    --log-dir)
      LOG_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
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

run_cmd() {
  if (( DRY_RUN )); then
    printf '[dry-run] '
    printf '%q ' "$@"
    printf '\n'
    return 0
  fi
  "$@"
}

clone_partition() {
  local partition="$1"
  local src_dir="$2"
  local log_file="$3"
  shift 3
  local extra_args=()
  if (($# > 0)); then
    extra_args=("$@")
  fi

  echo "Importing ${partition} from ${src_dir}..."
  if (( DRY_RUN )); then
    run_cmd "$HST_AMIGA_BIN" pfs import-dir "$HDF_PATH" "$src_dir" "/" --partition "$partition" \
      --exclude ".DS_Store" --exclude "*.uaem" "${extra_args[@]}"
  else
    : >"$log_file"
    while IFS= read -r line; do
      printf '%s\n' "$line" >>"$log_file"
      printf '\r\033[K%s' "$line"
    done < <(
      "$HST_AMIGA_BIN" pfs import-dir "$HDF_PATH" "$src_dir" "/" --partition "$partition" \
        --exclude ".DS_Store" --exclude "*.uaem" "${extra_args[@]}" 2>&1
    )
    printf '\n'
  fi
}

if [[ -z "$HDF_PATH" || -z "$SRC_ROOT" ]]; then
  echo "error: --hdf and --src-root are required" >&2
  usage
  exit 1
fi

require_file "$HDF_PATH"
require_dir "$SRC_ROOT"
require_dir "$SRC_ROOT/DH0"
require_dir "$SRC_ROOT/DH1"
require_file "$HST_AMIGA_BIN"

if [[ -n "$LOG_DIR" ]]; then
  mkdir -p "$LOG_DIR"
fi

DH0_LOG="${LOG_DIR:+$LOG_DIR/}hst-amiga-dh0.log"
DH1_LOG="${LOG_DIR:+$LOG_DIR/}hst-amiga-dh1.log"

if (( ! DRY_RUN )); then
  : >"$DH0_LOG"
  : >"$DH1_LOG"
fi

clone_partition "DH0" "$SRC_ROOT/DH0" "$DH0_LOG"
clone_partition "DH1" "$SRC_ROOT/DH1" "$DH1_LOG" --no-uae-metadata
