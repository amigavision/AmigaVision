# Post build script
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

SRC_DIR="$REPO_DIR/content/distro_mini"
if [ ! -d "$SRC_DIR" ]; then
  echo "error: Mini distro assets not found in $REPO_DIR/content/distro_mini" >&2
  exit 1
fi

rm -rf "$AGSDEST"/AmigaVision-Mini
mkdir -p "$AGSDEST"/AmigaVision-Mini
cp -R "$SRC_DIR"/. "$AGSDEST"/AmigaVision-Mini/

if [ -f "$AGSDEST"/AmigaVision-Mini/AmigaVision-Mini-ReadMe.md ]; then
  mv "$AGSDEST"/AmigaVision-Mini/AmigaVision-Mini-ReadMe.md "$AGSDEST"/AmigaVision-Mini/AmigaVision-Mini-ReadMe.txt
fi
