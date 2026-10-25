"""Convert hi-res QR masters from 50px to lossless 25px modules with RLE."""
from pathlib import Path
from PIL import Image
import iff_ilbm
from repair_hires_palettes import decode,read_chunks

def resize_qr(path):
    path=Path(path)
    chunks=read_chunks(path)
    image,mode=decode(chunks)
    if image.size==(25,25):
        return False
    if image.size!=(50,50):
        raise ValueError(f'Unexpected QR size: {path}: {image.size}')
    small=image.resize((25,25),Image.Resampling.NEAREST)
    if small.resize((50,50),Image.Resampling.NEAREST).tobytes()!=image.tobytes():
        raise ValueError(f'QR is not an exact 2x module raster: {path}')
    # Preserve the original indexed palette and crisp one-pixel QR modules.
    palette=list(chunks[b'CMAP'])
    data=iff_ilbm.ilbm(25,25,small.load(),palette,mode=mode,pack=1)
    temporary=path.with_suffix(".iff.tmp")
    temporary.write_bytes(data)
    temporary.replace(path)
    check,_=decode(read_chunks(path))
    assert check.size==(25,25) and check.tobytes()==small.tobytes()
    assert check.convert('RGB').tobytes()==small.convert('RGB').tobytes()
    assert read_chunks(path)[b'BMHD'][10]==1
    return True


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths',nargs='*',type=Path)
    args=parser.parse_args()
    paths=args.paths or sorted(Path('data/img_highres/qr').glob('*.iff')) + sorted(Path('data/avs-highres').glob('*-qr.iff'))
    converted=sum(resize_qr(path) for path in paths)
    print(f'{converted} QR images converted; {len(paths)-converted} already 25x25')
