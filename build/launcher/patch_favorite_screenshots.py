#!/usr/bin/env python3
"""Link all numbered screenshots when adding Favorites; remove them on deletion."""
from pathlib import Path
import struct
TAG=b'AVSFAVS1'
ORIGINAL=bytes.fromhex('48e7fffe')
def remove_patch(data):
 end=32+struct.unpack_from('>I',data,28)[0]*4
 if data[end-12:end-4]!=TAG:return data
 size=struct.unpack_from('>I',data,end-4)[0]
 hooks=struct.unpack_from('>2I',data,32+size)
 result=bytearray(data[:32+size]+data[end:])
 for off in (20,28):struct.pack_into('>I',result,off,size//4)
 for hook in hooks:result[32+hook:32+hook+4]=ORIGINAL
 return bytes(result)
def patch(data):
 end=32+struct.unpack_from('>I',data,28)[0]*4;size=end-32
 if data[end-12:end-4]==TAG:return data
 tag=data.find(b'AVSDIV14',32,end)
 if tag<0:raise ValueError('Expected native Favorites extension')
 values=struct.unpack_from('>20I',data,tag+8);base=values[0]
 hooks=[base+values[i+1] for i in (12,13)]
 blob=bytearray(struct.pack('>2I',*hooks));fixups=[];wrappers=[]
 def branch(op,target):
  blob.extend(bytes.fromhex(op));offset=len(blob);blob.extend(bytes(2));fixups.append((offset,target))
 for hook in hooks:
  if data[32+hook:32+hook+4]!=ORIGINAL:raise ValueError('Unknown Favorites entry')
  # Existing first BSR calls the native optional-asset copy/delete wrapper.
  opcode=data[32+hook+8:32+hook+10]
  if opcode[0]!=0x61:raise ValueError('Unknown Favorites call')
  displacement=struct.unpack('>b',opcode[1:])[0]
  if not displacement:displacement=struct.unpack_from('>h',data,32+hook+10)[0]
  callee=hook+10+displacement
  wrappers.append(size+len(blob));blob.extend(ORIGINAL)
  for i in range(1,10):
   branch('45fa',f'suffix{i}') # lea suffix(pc),a2
   branch('6100',callee)
  branch('6000',hook+4) # existing QR, metadata and completion behavior
 labels={}
 for i in range(1,10):
  labels[f'suffix{i}']=size+len(blob);blob.extend(f'-{i}.iff'.encode()+b'\0')
 for offset,target in fixups:
  if isinstance(target,str):target=labels[target]
  struct.pack_into('>h',blob,offset,target-(size+offset))
 blob.extend(bytes((-len(blob))%4));blob.extend(TAG+struct.pack('>I',size))
 result=bytearray(data[:end]+blob+data[end:])
 for off in (20,28):struct.pack_into('>I',result,off,(size+len(blob))//4)
 for hook,wrapper in zip(hooks,wrappers):result[32+hook:32+hook+4]=struct.pack('>Hh',0x6000,wrapper-(hook+2))
 return bytes(result)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('menu',type=Path);a=p.parse_args();a.menu.write_bytes(patch(a.menu.read_bytes()))
