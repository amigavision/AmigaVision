#!/usr/bin/env python3
"""Add optional caption suppression to the validated AGA hi-res QR helper.
Set qrcode_label_y = -1 to hide; restore its previous Y to enable again.
Run after patch_qr_thumbnail.py. No change to QR rendering itself.
"""
from pathlib import Path
import argparse,hashlib,struct,subprocess,tempfile
BASELINE='813330e99760c2fce8686f5781e98108c696fd0df7556fed9bea2f8282cc8383'
HOOKS=(0x5430,0x548e)

def remove_patch(data):
 end=32+struct.unpack_from('>I',data,28)[0]*4
 if data[end-20:end-12]!=b'QRLABEL1':return data
 base,_,_=struct.unpack_from('>3I',data,end-12)
 result=bytearray(data[:32+base]+data[end:])
 for pos in (20,28):struct.pack_into('>I',result,pos,base//4)
 for runtime in HOOKS:result[runtime+32:runtime+36]=bytes.fromhex('48e7fffe')
 return bytes(result)

def patch(data,assembler='/tmp/av-vasm/vasmm68k_mot'):
 original=remove_patch(data)
 if hashlib.sha256(original).hexdigest()!=BASELINE:raise ValueError('Unknown QR helper baseline')
 if original!=data:return data
 base=struct.unpack_from('>I',data,28)[0]*4
 with tempfile.TemporaryDirectory() as temp:
  out=Path(temp)/'toggle.bin'
  subprocess.run([assembler,'-Fbin','-m68000','-quiet',f'-DPATCH_BASE={base}','-o',str(out),str(Path(__file__).with_name('qr_label_toggle.s'))],check=True)
  blob=out.read_bytes()
 entries=struct.unpack_from('>2I',blob)
 result=bytearray(data[:32+base]+blob+data[32+base:])
 for pos in (20,28):struct.pack_into('>I',result,pos,(base+len(blob))//4)
 for runtime,entry in zip(HOOKS,entries):
  assert data[runtime+32:runtime+36]==bytes.fromhex('48e7fffe')
  struct.pack_into('>Hh',result,runtime+32,0x6000,base+entry-(runtime+2))
 return bytes(result)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('helper',type=Path);parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args();args.output.write_bytes(patch(args.helper.read_bytes()))
