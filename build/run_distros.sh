#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_distros.sh [package_distros.py args...]

Environment:
  DISTRO_DATE            Release date stamp. Defaults to today's date.

If stdin is interactive, the script prompts before packaging starts so the
release date can be confirmed or edited.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

default_date="$(date +%Y.%m.%d)"
date_stamp="${DISTRO_DATE:-$default_date}"

if [[ -t 0 ]]; then
  printf 'Preparing distro packaging.\n'
  printf 'Release date [%s]: ' "$date_stamp"
  read -r input_date
  if [[ -n "$input_date" ]]; then
    date_stamp="$input_date"
  fi

  printf 'Using release date: %s\n' "$date_stamp"
  printf '\n'
fi

DISTRO_DATE="$date_stamp" python3 build/package_distros.py --date-stamp "$date_stamp" "$@"
