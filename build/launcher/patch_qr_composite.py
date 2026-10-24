#!/usr/bin/env python3
"""Present the AGA 404x280 experiment thumbnail and cached 50x50 QR together.
Run after the thumbnail-redraw and optional-caption patches. Fixed validated
helper only. Unchanged entries reuse a chip-memory QR raster instead of disk I/O.
"""
from pathlib import Path
import argparse,hashlib,struct,subprocess,tempfile
BASELINE='b5d681d07a402af5eaf0529e501cdf62708a5ff33a5572e8693bb7df87a01099'
HOOKS=((0x4276,'4feffff8'),(0x4370,'206dffc4'),(0x53de,'2f00103a00f0'),
       (0x45ac,'4fef0010'),(0x45dc,'7000206dffc4'),(0x4660,'295fffa8'))

def remove_patch(data):
 end=32+struct.unpack_from('>I',data,28)[0]*4
 if data[end-12:end-4] not in (b'QRCOMP01',b'QRCOMP02',b'QRCOMP03'):return data
 base=struct.unpack_from('>I',data,end-4)[0]
 result=bytearray(data[:32+base]+data[end:])
 for pos in (20,28):struct.pack_into('>I',result,pos,base//4)
 for runtime,original in HOOKS:result[runtime+32:runtime+32+len(bytes.fromhex(original))]=bytes.fromhex(original)
 result[0x53a4+32:0x53a6+32]=bytes.fromhex('600a')
 return bytes(result)

def patch(data,assembler='/tmp/av-vasm/vasmm68k_mot'):
 original=remove_patch(data)
 if hashlib.sha256(original).hexdigest()!=BASELINE:raise ValueError('Unknown QR helper baseline')
 end=32+struct.unpack_from('>I',data,28)[0]*4
 if data[end-12:end-4]==b'QRCOMP03':return data
 data=original
 base=struct.unpack_from('>I',data,28)[0]*4
 with tempfile.TemporaryDirectory() as temp:
  out=Path(temp)/'composite.bin'
  subprocess.run([assembler,'-Fbin','-m68000','-quiet',f'-DPATCH_BASE={base}','-o',str(out),str(Path(__file__).with_name('qr_composite.s'))],check=True)
  blob=out.read_bytes()
 entries=struct.unpack_from('>7I',blob)
 result=bytearray(data[:32+base]+blob+data[32+base:])
 for pos in (20,28):struct.pack_into('>I',result,pos,(base+len(blob))//4)
 for (runtime,expected),entry in zip(HOOKS,entries):
  assert data[runtime+32:runtime+32+len(bytes.fromhex(expected))]==bytes.fromhex(expected),(hex(runtime),data[runtime+32:runtime+38].hex())
  struct.pack_into('>Hh',result,runtime+32,0x6000,base+entry-(runtime+2))
  if len(bytes.fromhex(expected))==6:result[runtime+36:runtime+38]=bytes.fromhex('4e71')
 # Restore native true entry identity. qr_gate now replays the cached raster.
 assert data[0x53a4+32:0x53a6+32]==bytes.fromhex('600a')
 result[0x53a4+32:0x53a6+32]=bytes.fromhex('660a')
 return bytes(result)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('helper',type=Path);parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args();args.output.write_bytes(patch(args.helper.read_bytes()))
