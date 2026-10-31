# XZ block reuse experiment

This is a standalone prototype. `make distros` does not call it.
The integrated implementation is now in `build/xz_reuse.py`; it records hashes
during seed compression and avoids the source decoding performed by this
historical prototype.

`xz_reuse.py` reads the index of an existing Amiga HDF `.xz` release. For each
independent block, it decodes the source and compares the bytes against the
same offset of a separately patched PiStorm HDF. Exact matches retain the
original compressed bytes; changed blocks are compressed at preset 1.
A boot prefix and zero partition padding may be added. The result is **one
standard CRC64 XZ stream**, with a rebuilt index and footer, rather than
concatenated streams or a custom archive format. Metadata follows the
[official XZ specification](https://tukaani.org/xz/xz-file-format.txt).

Before publication, the prototype independently decodes the full output with
`xz`, checks its complete byte count and SHA-256 against the requested image,
and checks that all inputs retained their original sizes and modification
times. Existing output is replaced only after success. Corrupt source blocks
are rejected rather than silently recompressed.

Limits: one CRC64 source stream without trailing padding, blocks up to 64 MiB,
prefix up to 128 MiB, partition padding up to 1 MiB. Worker queues are bounded.
Seed and target HDF sizes must match. Filesystem/MBR validation belongs to the
existing PiStorm builder; this tool only validates the supplied byte layout.

```sh
pipenv run python build/experiments/xz_reuse.py \
  --seed /path/to/AmigaVision-Amiga-ECS.img.xz \
  --target /path/to/patched.hdf \
  --prefix /path/to/boot-prefix.img --padding 180224 \
  --output /path/to/disposable/experiment.img.xz \
  --report /tmp/xz-reuse-results.json

pipenv run python -m unittest discover -s build/experiments -p 'test_*.py'
```

The example padding is specific to the tested image; derive it from the actual
partition geometry for another image. All large temporary files should live on
the output device. Do not overwrite release artifacts when experimenting.

For a full-size experiment, an existing PiStorm release can be decompressed
into prefix, patched HDF, and padding to obtain an exact reference. That
extraction is measurement setup, not part of the proposed production workflow:
the normal PiStorm builder already creates its private patched HDF. The seed
is likewise the Amiga release that the normal distro run has already produced.
Compare assembly **plus independent verification** with the corresponding
existing streaming-compression and verification stages.

Tests cover exact compressed-block preservation, changed blocks, prefix and
padding, identity and all-changed targets, rejection of corrupt input and
concatenated streams, atomic publication, and decoding with xz, Python's lzma,
and 7-Zip when installed. Flashing-tool and hardware compatibility remain
unverified; do not enable this in release builds on the strength of these tests
alone.
