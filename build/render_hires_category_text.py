#!/usr/bin/env python3
"""Refresh native hi-res category text and affected logos, optionally including ECS."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import argparse,os,json
import avs_util as util
from render_hires_years import DIRECTORIES,render_native_card
from repair_hires_palettes import read_chunks,decode
from ecs_artwork import convert
from PIL import Image

ROOT=Path('data/img_highres')
LETTERS=('By Title.avs','Demo Scene.avs/Demos - By Title.avs',
         'Demo Scene.avs/Demos - By Group.avs','Demo Scene.avs/Music Disks - By Title.avs')


def specifications():
    result={}
    # Read text/size/style from the menu, not from an enlarged medium bitmap.
    def visit(rows,path):
        if not isinstance(rows,list):return
        for row in rows:
            if isinstance(row,list):visit(row,path)
            elif isinstance(row,dict):
                for name,value in row.items():
                    if name=='image':
                        operations=value.get('ops',value) if isinstance(value,dict) else value
                        operations=operations if isinstance(operations,list) else [operations]
                        is_gameography='Artists & Publishers.avs' in path.parts
                        if operations and (all(op.get('op')=='tx' for op in operations)
                                           or is_gameography and all(op.get('op')=='pi' for op in operations)):
                            target=ROOT/(str(path)[:-4]+'.iff')
                            if target.is_file():
                                if is_gameography:
                                    operations=[dict(op) for op in operations]
                                    for op in operations:
                                        if op.get('op')=='pi' and op.get('scale','fit')=='fit':
                                            with Image.open(Path('data/img_src')/op['path']) as source:
                                                # Center original pixels; only shrink sources that exceed the frame.
                                                op['scale']=min(1.0,404/source.width,280/source.height)
                                result[target]=operations
                    elif isinstance(value,list):visit(value,path/(name+'.avs'))
    visit(util.yaml_load('configs/AmigaVision.yaml'),Path(''))
    for directory in DIRECTORIES:
        for path in directory.glob('*.iff'):
            result[path]=[{'op':'tx','txt':'19XX' if path.stem=='Unknown' else path.stem,'size':112}]
    for directory in LETTERS:
        for path in (ROOT/directory).glob('*.iff'):
            if len(path.stem)==1:
                result[path]=[{'op':'tx','txt':path.stem,'size':240}]
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ecs',action='store_true',help='Also refresh changed/missing/older ECS derivatives')
    parser.add_argument('--gameographies-only',action='store_true',help='Only refresh Artists & Publishers cards')
    args=parser.parse_args()
    os.environ.setdefault('AVSCONTENT',str(Path(__file__).resolve().parents[2]/'AV-Content'))
    changed=[];cache={};specs=specifications()
    if args.gameographies_only:
        specs={p:ops for p,ops in specs.items() if 'Artists & Publishers.avs' in p.parts}
    for path,ops in specs.items():
        key=json.dumps(ops,sort_keys=True)
        if key not in cache:cache[key]=render_native_card(ops)
        data=cache[key]
        if path.read_bytes()!=data:
            path.write_bytes(data);changed.append(path)
        image,mode=decode(read_chunks(path))
        assert image.size==(404,280) and mode==0x19004 and max(image.tobytes())<240
        assert read_chunks(path)[b'BMHD'][10]==1
    print(f'Checked {len(specs)} category cards; updated {len(changed)} AGA cards',flush=True)
    if args.ecs:
        jobs=[]
        for p in specs:
            target=Path('data/img_ecs')/p.relative_to(ROOT)
            if p in changed or not target.exists() or target.stat().st_mtime_ns < p.stat().st_mtime_ns:
                jobs.append((str(p),str(target),False))
        with ProcessPoolExecutor(max_workers=4) as pool:
            for target in pool.map(convert,jobs,chunksize=4):
                image,_=decode(read_chunks(Path(target)))
                assert image.size==(404,280) and max(image.tobytes())<=12
                assert read_chunks(Path(target))[b'BMHD'][10]==1
        print(f'Converted {len(jobs)} updated cards for ECS',flush=True)


if __name__=='__main__':main()
