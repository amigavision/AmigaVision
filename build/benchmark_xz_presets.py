#!/usr/bin/env python3
"""Benchmark complete HDFs without retaining multi-gigabyte output archives."""
import argparse
import json
from pathlib import Path
import subprocess
from time import monotonic


def benchmark(source, preset):
    before = source.stat()
    count, started = 0, monotonic()
    with subprocess.Popen(['xz', '-T0', f'-{preset}', '-c', str(source)], stdout=subprocess.PIPE) as process:
        try:
            while chunk := process.stdout.read(4 * 1024 * 1024):
                count += len(chunk)
            if process.wait():
                raise subprocess.CalledProcessError(process.returncode, process.args)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    after = source.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError(f'Input changed during benchmark: {source}')
    return {'source': source.name, 'source_bytes': before.st_size, 'source_mtime_ns': before.st_mtime_ns,
            'preset': preset, 'seconds': round(monotonic() - started, 2), 'compressed_bytes': count}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('images', nargs='+', type=Path)
    parser.add_argument('--presets', nargs='+', type=int, choices=range(10), default=[3, 1])
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    results = []
    for image in args.images:
        for preset in args.presets:
            print(f'Benchmarking complete {image.name} with xz -{preset}', flush=True)
            results.append(benchmark(image, preset))
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(results, indent=2) + '\n')
            print(json.dumps(results[-1]), flush=True)


if __name__ == '__main__': main()
