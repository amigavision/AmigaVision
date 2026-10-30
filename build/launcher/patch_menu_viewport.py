#!/usr/bin/env python3
"""Bound the AGA hi-res menu text bitmap; retain existing flicker-free compositor.
Apply after the validated AVSNOW04 menu. Preserve the original HUNK tail.
"""
from pathlib import Path
import argparse,hashlib,struct,subprocess,tempfile
BASELINE='3d809d1082f75b2f77d89a1ca1ea490ecd4e8c1464ff4d7d907473ae8a214b53'
HOOKS=((0x6832,'20280010'),(0x699e,'20280010'),(0x6b88,'20463028002a'),(0x6c94,'610042a6'))
SELECT=(0xa4e4,bytes.fromhex('d26b002a'))
def remove_patch(data):
 end=32+struct.unpack_from('>I',data,28)[0]*4
 tag=data[end-12:end-4]
 if tag not in (b'AVSVIEW1',b'AVSVIEW2'):return data
 base=struct.unpack_from('>I',data,end-4)[0]
 out=bytearray(data[:32+base]+data[end:])
 for off in (20,28):struct.pack_into('>I',out,off,base//4)
 for addr,value in (HOOKS[:3] if tag==b'AVSVIEW1' else HOOKS):out[32+addr:32+addr+len(bytes.fromhex(value))]=bytes.fromhex(value)
 out[32+SELECT[0]:32+SELECT[0]+4]=SELECT[1]
 if hashlib.sha256(out).hexdigest()!=BASELINE:raise ValueError('Unknown viewport-patched menu')
 return bytes(out)
def patch(data,assembler='/tmp/av-vasm/vasmm68k_mot'):
 original=remove_patch(data)
 end=32+struct.unpack_from('>I',data,28)[0]*4
 if data[end-12:end-4]==b'AVSVIEW2':return data
 data=original
 if hashlib.sha256(data).hexdigest()!=BASELINE:raise ValueError('Unknown AGA hi-res menu; revalidate viewport hooks')
 base=struct.unpack_from('>I',data,28)[0]*4;end=32+base
 with tempfile.TemporaryDirectory() as temp:
  out=Path(temp)/'viewport.bin'
  subprocess.run([assembler,'-Fbin','-m68000','-quiet',f'-DPATCH_BASE={base}',f"-DORIGINAL_COMPOSE={0x6c96+struct.unpack_from('>h',data,32+0x6c96)[0]}",'-o',str(out),str(Path(__file__).with_name('menu_viewport.s'))],check=True)
  blob=out.read_bytes()
 result=bytearray(data[:end]+blob+data[end:])
 for off in (20,28):struct.pack_into('>I',result,off,(base+len(blob))//4)
 entries=struct.unpack_from('>6I',blob)
 for (addr,expected),entry in zip(HOOKS,entries[:3]+entries[5:6]):
  expected=bytes.fromhex(expected);assert data[32+addr:32+addr+len(expected)]==expected
  result[32+addr:32+addr+len(expected)]=struct.pack('>Hh',0x6100 if addr==0x6c94 else 0x6000,base+entry-(addr+2))+bytes.fromhex('4e71')*((len(expected)-4)//2)
 addr,expected=SELECT;assert data[32+addr:32+addr+4]==expected
 result[32+addr:32+addr+4]=bytes.fromhex('4e714e71')
 return bytes(result)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('menu',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_bytes(patch(a.menu.read_bytes()))
