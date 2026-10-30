#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_distros.sh [package_distros.py args...]
  run_distros.sh --pistorm [pistorm_image.py args...]

Environment:
  DISTRO_DATE            Release version. Defaults to today's date.
  DISTRO_OUT             Default output directory.
  EMULATORS_ARCHIVE      Set to 1 to archive emulator folders in a full run.

--build-all reuses existing main, ECS, and Mini images, builds missing images,
and prepares listings before packaging all distributions,
using the selected drive for generated images, caches, and staging files.
It asks only for the version and output directory at the start.

If stdin is interactive, the script prompts before packaging starts so the
release date and output directory can be confirmed or edited.
For emulators, it also asks whether to create a 7z archive (default: no).
Pass --skip-emulator-archive or --emulator-archive to choose without a prompt.
Noninteractive emulator runs keep the folders unless --emulator-archive is passed.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

default_date="$(date +%Y.%m.%d)"
date_stamp="${DISTRO_DATE:-$default_date}"

# Remove the configured output argument so the prompted value is authoritative.
build_all=false
pistorm=false
explicit_output=""
package_args=()
emulator_package=false
archive_choice_explicit=false
main_hdf=""
ecs_hdf=""
mini_hdf=""
output_dir="${DISTRO_OUT:-${AVSDEST:-$HOME/Developer/AV-Output}/distros}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pistorm)
      pistorm=true
      shift
      ;;
    --date-stamp)
      date_stamp="$2"
      shift 2
      ;;
    --output)
      explicit_output="$2"
      package_args+=("$1" "$2")
      shift 2
      ;;
    --build-all)
      build_all=true
      shift
      ;;
    --main-hdf|--ecs-hdf|--mini-hdf)
      case "$1" in
        --main-hdf) main_hdf="$2" ;;
        --ecs-hdf) ecs_hdf="$2" ;;
        --mini-hdf) mini_hdf="$2" ;;
      esac
      package_args+=("$1" "$2")
      shift 2
      ;;
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
    emulators|all)
      emulator_package=true
      package_args+=("$1")
      shift
      ;;
    --skip-emulator-archive|--emulator-archive)
      archive_choice_explicit=true
      package_args+=("$1")
      shift
      ;;
    *) package_args+=("$1"); shift ;;
  esac
done

if [[ "$pistorm" == true && -n "$explicit_output" ]]; then
  output_dir="$(dirname "$(python3 build/user_paths.py "$explicit_output")")"
fi

if [[ -t 0 ]]; then
  printf 'Preparing distro packaging.\n'
  printf 'Release version [%s]: ' "$date_stamp"
  read -r input_date
  if [[ -n "$input_date" ]]; then
    date_stamp="$input_date"
  fi

  printf 'Output directory [%s]: ' "$output_dir"
  read -r input_output
  if [[ -n "$input_output" ]]; then
    output_dir="$input_output"
  fi

  output_dir="$(python3 build/user_paths.py "$output_dir")"

  if [[ "$build_all" == false && "$emulator_package" == true && "$archive_choice_explicit" == false ]]; then
    while true; do
      printf 'Create a 7z archive of the emulator folders? [y/N]: '
      read -r archive_answer
      case "$archive_answer" in
        y|Y|yes|YES) break ;;
        ""|n|N|no|NO)
          package_args+=(--skip-emulator-archive)
          break
          ;;
        *) printf 'Please answer yes or no.\n' ;;
      esac
    done
  fi

  printf 'Using output directory: %s\n' "$output_dir"
  printf 'Using release version: %s\n' "$date_stamp"
  printf '\n'
fi

output_dir="$(python3 build/user_paths.py "$output_dir")"

if [[ "$build_all" == true ]]; then
  # Resolve once so every child receives the exact same destination, including
  # paths with spaces and a user-entered ~/ prefix. Never evaluate shell input.
  case "$output_dir" in
    "~") output_dir="$HOME" ;;
    "~/"*) output_dir="$HOME/${output_dir#\~/}" ;;
  esac
  mkdir -p "$output_dir"
  output_dir="$(cd "$output_dir" && pwd -P)"
  free_kb="$(df -Pk "$output_dir" | awk 'NR==2 {print $4}')"
  if [[ "$free_kb" -lt 23068672 ]]; then
    printf 'Building all the distros requires 22GB or more of free space in %s.\n' "$output_dir" >&2
    exit 1
  fi
  work_dir="$output_dir/.build"
  mkdir -p "$work_dir/images" "$work_dir/tmp"
  export TMPDIR="$work_dir/tmp"
  export AVSCACHE_ROOT="$work_dir/cache"
  export DISTRO_DATE="$date_stamp" DISTRO_OUT="$output_dir"
  # Prefer configured images, then images from an earlier distro run on this
  # drive. Build only missing images and pass the selected paths to packaging.
  ensure_image() {
    local configured="$1" filename="$2" target="$3" variable="$4" selected
    if [[ -n "$configured" ]]; then
      configured="$(python3 build/user_paths.py "$configured")"
    fi
    selected="$configured"
    if [[ ! -f "$selected" ]]; then
      selected="$work_dir/images/$filename"
    fi
    if [[ -f "$selected" ]]; then
      printf 'Reusing image: %s\n' "$selected"
    else
      printf 'Building missing image: %s\n' "$selected"
      "${MAKE:-make}" "$target" "DISTRO_DATE=$date_stamp" "DISTRO_OUT=$output_dir" \
        "AVSDEST=$work_dir/images" "AVSTEMP=$work_dir/stage" \
        "AMIGAVISION_HDF=$work_dir/images/AmigaVision.hdf" \
        "ECS_HDF=$work_dir/images/AmigaVision-ECS.hdf" \
        "MINI_HDF=$work_dir/images/AmigaVision-Mini.hdf" \
        "MINI_UAE=$work_dir/images/AmigaVision-Mini.uae"
      if [[ ! -f "$selected" ]]; then
        printf 'error: %s did not create %s\n' "$target" "$selected" >&2
        return 1
      fi
    fi
    printf -v "$variable" '%s' "$selected"
  }
  ensure_image "$main_hdf" AmigaVision.hdf image main_hdf
  ensure_image "$ecs_hdf" AmigaVision-ECS.hdf ecs-image ecs_hdf
  ensure_image "$mini_hdf" AmigaVision-Mini.hdf mini-image mini_hdf
  "${MAKE:-make}" listings "DISTRO_DATE=$date_stamp" "DISTRO_OUT=$output_dir" \
    "DISTRO_LISTINGS_DIR=$work_dir/listings"
  # CD32's generator and packer also use AVSDEST for intermediate payloads.
  export AVSDEST="$work_dir/images"
  package_args+=(--main-hdf "$main_hdf" --ecs-hdf "$ecs_hdf" --mini-hdf "$mini_hdf"
                 --listings-dir "$work_dir/listings")
  if [[ "$archive_choice_explicit" == false ]]; then
    if [[ "${EMULATORS_ARCHIVE:-auto}" == 1 ]]; then
      package_args+=(--emulator-archive)
    else
      package_args+=(--skip-emulator-archive)
    fi
    archive_choice_explicit=true
  fi
fi

if [[ ! -t 0 && "$emulator_package" == true && "$archive_choice_explicit" == false ]]; then
  package_args+=(--skip-emulator-archive)
fi

if [[ "$pistorm" == true ]]; then
  python3 build/pistorm_image.py --date-stamp "$date_stamp" --output-dir "$output_dir" "${package_args[@]}"
else
  DISTRO_DATE="$date_stamp" python3 build/package_distros.py --date-stamp "$date_stamp" --output-dir "$output_dir" "${package_args[@]}"
fi
