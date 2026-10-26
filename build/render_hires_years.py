#!/usr/bin/env python3
"""Render existing By Year cards at native AGA thumbnail resolution, with RLE."""
from pathlib import Path
from io import BytesIO
import os
from PIL import Image
import avs_compositor as compositor
import iff_ilbm
from repair_hires_palettes import black_padding_palette,read_chunks,decode

DIRECTORIES=(Path('data/img_highres/By Year.avs'),
             Path('data/img_highres/Demo Scene.avs/Demos - By Year.avs'),
             Path('data/img_highres/Demo Scene.avs/Music Disks - By Year.avs'))


def render_year(label):
    font=Path(os.environ['AVSCONTENT'])/'fonts/display.otf'
    if not font.is_file():
        raise FileNotFoundError(font)
    # Render the type directly into the final 404x280 canvas. Do not use a
    # 320x128 med-res raster or enlarge its already antialiased glyph pixels.
    with compositor.compose({'op':'tx','txt':label,'size':112},size=(404,280)) as image:
        rgb=Image.open(BytesIO(image.make_blob('png'))).convert('RGB')
    indexed=black_padding_palette(rgb.quantize(colors=240,method=Image.Quantize.MEDIANCUT,
                                              kmeans=4,dither=Image.Dither.NONE))
    return iff_ilbm.ilbm(*indexed.size,indexed.load(),indexed.getpalette(),mode=0x19004,pack=1)


def main():
    if 'AVSCONTENT' not in os.environ:
        os.environ['AVSCONTENT']=str(Path(__file__).resolve().parents[2]/'AV-Content')
    rendered={};count=0
    for directory in DIRECTORIES:
        for path in sorted(directory.glob('*.iff')):
            label='19XX' if path.stem=='Unknown' else path.stem
            if label not in rendered:
                rendered[label]=render_year(label)
            path.write_bytes(rendered[label])
            image,_=decode(read_chunks(path))
            assert image.size==(404,280) and max(image.tobytes())<240
            assert read_chunks(path)[b'BMHD'][10]==1
            assert not any(read_chunks(path)[b'CMAP'][720:])
            count+=1
    print(f'Rendered {count} native hi-res year cards ({len(rendered)} unique labels), RLE/palettes verified')


if __name__=='__main__':
    main()
