#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_distros.sh [package_distros.py args...]

Environment:
  DISTRO_DATE            Release date stamp. Defaults to today's date.

If stdin is interactive, the script prompts before packaging starts so the
release date and output directory can be confirmed or edited.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

default_date="$(date +%Y.%m.%d)"
date_stamp="${DISTRO_DATE:-$default_date}"

# Remove the configured output argument so the prompted value is authoritative.
package_args=()
output_dir="${DISTRO_OUT:-${AGSDEST:-$HOME/Developer/AV-Output}/distros}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      if [[ $# -lt 2 || -z "$2" ]]; then
        printf 'error: --output-dir requires a path\n' >&2
        exit 2
      fi
      output_dir="$2"
      shift 2
      ;;
    --output-dir=*)
      output_dir="${1#*=}"
      shift
      ;;
    *) package_args+=("$1"); shift ;;
  esac
done

if [[ -t 0 ]]; then
  printf 'Preparing distro packaging.\n'
  printf 'Release date [%s]: ' "$date_stamp"
  read -r input_date
  if [[ -n "$input_date" ]]; then
    date_stamp="$input_date"
  fi

  printf 'Output directory [%s]: ' "$output_dir"
  read -r input_output
  if [[ -n "$input_output" ]]; then
    output_dir="$input_output"
  fi

  printf 'Using output directory: %s\n' "$output_dir"
  printf 'Using release date: %s\n' "$date_stamp"
  printf '\n'
fi

DISTRO_DATE="$date_stamp" python3 build/package_distros.py --date-stamp "$date_stamp" --output-dir "$output_dir" "${package_args[@]}"
