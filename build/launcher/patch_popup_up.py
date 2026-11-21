"""Move the hi-res music popup and its Copper text up two pixels in place."""
import struct
EDITS=((bytes.fromhex('302900145840'),bytes.fromhex('302900145c40')),
       (bytes.fromhex('92805581d081'),bytes.fromhex('92805981d081')))
def transform(data,reverse=False):
 end=32+struct.unpack_from('>I',data,28)[0]*4
 while data[end-12:end-4]!=b'AVSNOW04':
  if data[end-12:end-4] not in (b'AVSRESM1',b'AVSCANC1',b'AVSEXIT1',b'AVSVIEW3'):return data
  end=32+struct.unpack_from('>I',data,end-4)[0]
 base=32+struct.unpack_from('>I',data,end-4)[0];body=data[base:end-12]
 for old,new in EDITS:
  expected,replacement=(new,old) if reverse else (old,new)
  if replacement in body:continue
  if body.count(expected)!=1:raise ValueError('Unknown popup geometry')
  body=body.replace(expected,replacement)
 return data[:base]+body+data[end-12:]
def remove_patch(data):return transform(data,True)
def patch(data):return transform(data)
