#!/usr/bin/env python3
"""Remove a build cache, retrying directory-not-empty metadata races."""

import errno
from pathlib import Path
import shutil
import sys
import time


def remove_build_cache(path):
    for attempt in range(4):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            if not path.exists():
                return
            # An entry disappeared during traversal; rescan the remaining tree.
        except OSError as error:
            if error.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                raise
            # Finder can recreate .DS_Store after a directory has been scanned.
            if attempt == 3:
                raise
        if attempt == 3:
            raise OSError(errno.ENOTEMPTY, "Build cache changed during removal", str(path))
        time.sleep(0.1)


if __name__ == "__main__":
    remove_build_cache(Path(sys.argv[1]))
