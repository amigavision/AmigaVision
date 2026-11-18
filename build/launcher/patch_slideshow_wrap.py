#!/usr/bin/env python3
"""Keep configured initial image; wrap the numbered slideshow to image one."""
from pathlib import Path
import argparse
# Native search budget must cover the whole 1..end range when files are missing.
# Initial index loads at $3cd4/$3e8e intentionally remain unchanged.
EDITS=((0x3cf4,bytes.fromhex('32280042'),bytes.fromhex('72014e71')),
       (0x3f96,bytes.fromhex('30280042'),bytes.fromhex('70014e71')))
def transform(data,reverse=False):
 result=bytearray(data)
 for address,old,new in EDITS:
  expected,replacement=(new,old) if reverse else (old,new)
  actual=data[32+address:32+address+4]
  if actual==replacement:continue
  if actual!=expected:raise ValueError(f'Unknown slideshow instruction at {address:x}')
  result[32+address:32+address+4]=replacement
 return bytes(result)
def patch(data):return transform(data)
def remove_patch(data):return transform(data,True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('helper',type=Path);a=p.parse_args();a.helper.write_bytes(patch(a.helper.read_bytes()))
