#!/usr/bin/env python3
"""Append the Now Playing footer to validated AVS menu executables, last in chain."""
from pathlib import Path
import argparse,hashlib,struct,subprocess,tempfile
BASELINES={
 'avs':'317661254f6326c417696ddcf2573912e02ae3351d283d1a9cf1c210d59d1591',
 'avs-highres':'3c1bf8482bad039b0c9c98a5156b607116d359e248de0d799334a2ffde0072cf',
 'avs-ecs':'96e77efcaac5f1bc9f15b6e36bb61e26d0ebfec34338e08958592c9cdace43a0'}
HOOKS=((0x8344,'70ff2046'),(0x4bee,'4eaefef2'),(0x5656,'7000dffc00000210'),(0x90e6,'295fffa8'),(0x5684,'02800000ffff'),(0x78f6,'280048780008'),(0x79f2,'28002f06'),(0x8124,'48e71800'),(0x8186,'204620280032'))
def remove_patch(data):
 # A viewport cache may wrap this layer; normalize it before older tests or
 # a music-layer rebuild. Reapply the viewport patch last after such edits.
 end=32+struct.unpack_from('>I',data,28)[0]*4
 if data[end-12:end-4]==b'AVSVIEW1':
  from patch_menu_viewport import remove_patch as remove_viewport
  data=remove_viewport(data)
 end=32+struct.unpack_from('>I',data,28)[0]*4
 tag=data[end-12:end-4]
 if tag not in (b'AVSNOW01',b'AVSNOW02',b'AVSNOW03',b'AVSNOW04'):return data
 base=struct.unpack_from('>I',data,end-4)[0]
 out=bytearray(data[:32+base]+data[end:])
 for off in (20,28):struct.pack_into('>I',out,off,base//4)
 for addr,original in (HOOKS[:4] if tag==b'AVSNOW01' else HOOKS[:7] if tag==b'AVSNOW02' else HOOKS):out[32+addr:32+addr+len(bytes.fromhex(original))]=bytes.fromhex(original)
 if hashlib.sha256(out).hexdigest() not in BASELINES.values() and tag in (b'AVSNOW02',b'AVSNOW03',b'AVSNOW04'):
  # Original med-res kept its count in d3; the extension returns the used
  # count in d4 for the subsequent sorter, just like the hi-res fixes.
  out[32+0x79f2:32+0x79f4]=bytes.fromhex('2600')
 if hashlib.sha256(out).hexdigest() not in BASELINES.values():raise ValueError('Unknown patched menu')
 return bytes(out)
def patch(data,assembler='/tmp/av-vasm/vasmm68k_mot'):
 original=remove_patch(data)
 end=32+struct.unpack_from('>I',data,28)[0]*4
 if data[end-12:end-4]==b'AVSNOW04':return data
 data=original
 if hashlib.sha256(data).hexdigest() not in BASELINES.values():raise ValueError('Unknown menu baseline')
 base=struct.unpack_from('>I',data,28)[0]*4;end=32+base
 with tempfile.TemporaryDirectory() as temp:
  out=Path(temp)/'now.bin'
  subprocess.run([assembler,'-Fbin','-m68000','-quiet',f'-DPATCH_BASE={base}','-o',str(out),str(Path(__file__).with_name('now_playing.s'))],check=True)
  blob=out.read_bytes()
 result=bytearray(data[:end]+blob+data[end:])
 for off in (20,28):struct.pack_into('>I',result,off,(base+len(blob))//4)
 entries=struct.unpack_from('>12I',blob)
 hook_entries=entries[:4]+entries[7:]
 for (addr,expected),entry in zip(HOOKS,hook_entries):
  expected=bytes.fromhex('26002f06' if addr==0x79f2 and hashlib.sha256(data).hexdigest()==BASELINES['avs'] else expected);assert data[32+addr:32+addr+len(expected)]==expected
  result[32+addr:32+addr+len(expected)]=struct.pack('>Hh',0x6000,base+entry-(addr+2))+bytes.fromhex('4e71')*((len(expected)-4)//2)
 return bytes(result)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('menu',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_bytes(patch(a.menu.read_bytes()))
