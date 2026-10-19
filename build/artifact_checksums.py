"""Checksums for finished release artifacts, computed in a single file pass."""
import hashlib
from pathlib import Path


def write_checksums(artifact):
    artifact = Path(artifact)
    digests = {'sha256': hashlib.sha256(), 'md5': hashlib.md5(usedforsecurity=False)}
    with artifact.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            for digest in digests.values():
                digest.update(chunk)
    values = {name: digest.hexdigest() for name, digest in digests.items()}
    for name, value in values.items():
        artifact.with_name(artifact.name + '.' + name + '.txt').write_text(
            f'{value}  {artifact.name}\n', encoding='utf-8')
    return values
