"""Accept literal, quoted, or shell-escaped paths without shell evaluation."""
import os
import shlex
from pathlib import Path


def normalize_path(value):
    value = os.fspath(value).strip()
    quoted = len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]
    if quoted or '\\ ' in value:
        try:
            parts = shlex.split(value)
        except ValueError:
            parts = []
        if len(parts) == 1:
            value = parts[0]
    return str(Path(value).expanduser())


if __name__ == '__main__':
    import sys
    print(normalize_path(sys.argv[1]))
