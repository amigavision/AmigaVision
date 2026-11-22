"""Run full screenshot Favorites linking and deletion as native 68000 code."""
import sys,os,struct,unittest
from pathlib import Path
from machine68k import Register as R
sys.path.insert(0,str(Path(__file__).parent))
import test_dividers_68k as native
from patch_favorite_screenshots import patch,remove_patch
class FavoritesTests(unittest.TestCase):
 set_items=native.Divider68000Tests.set_items
 tearDown=native.Divider68000Tests.tearDown
 def setUp(self):
  native.Divider68000Tests.setUp(self)
  data=(native.ROOT/os.environ.get('AVS_TEST_MENU','data/avs-highres/AVSMenu')).read_bytes()
  result=patch(data)
  self.assertEqual(patch(result),result)
  self.assertEqual(remove_patch(result),remove_patch(data))
  self.mem.w_block(0,result[32:32+struct.unpack_from('>I',result,28)[0]*4])
 def test_favorites_add_and_remove_optional_qr_and_metadata(self):
  frame,globals_,dos,vtable,getpath=0x97000,0x98000,0xc0000,0xc1000,0x6d54
  src,dst,dstpath,dstname=0xd0004,0xd1004,0xd2004,0xd3004
  def cstring(address):
   result=bytearray()
   while self.mem.r8(address):result.append(self.mem.r8(address));address+=1
   return bytes(result)
  def string(address,value):
   self.mem.w_block(address,value+b'\0');self.mem.w16(address-4,255);self.mem.w16(address-2,len(value))
  string(dstpath,b'Saves:Favorites/');string(dstname,b'Agony');string(dst,b'');string(src,b'')
  string(self.path,b'AVS:Charts/');string(0x9a004,b'01 Agony')
  self.mem.w16(self.obj+36,0);self.mem.w16(self.obj+42,0)
  for offset,value in [(-8,self.obj),(-28,src),(-20,dst),(-36,dstpath),(-12,dstname)]:self.mem.w32(frame+offset,value)
  self.mem.w32(self.obj,vtable);self.mem.w32(vtable+24,getpath)
  self.mem.w32(vtable+8,0xc3000);self.mem.w16(0xc3000,0x4e75)
  self.mem.w32(globals_-44,dos)
  for address in [0x9fce,dos-444,dos-72]:self.mem.w16(address,0x4e75)
  links=[];deleted=[];missing_qr=False;missing_screens=set()
  def hook(pc):
   sp=self.cpu.r_sp()
   if pc==self.stop:raise StopIteration()
   if pc==0x9fce:
    filename=cstring(self.mem.r32(sp+4))
    missing=(missing_qr and filename.endswith(b'-QR.iff')) or any(filename.endswith(suffix) for suffix in missing_screens)
    self.cpu.w32_reg(R.D0,0xffffffff if missing else 100)
   elif pc==dos-444:links.append((cstring(self.cpu.r32_reg(R.D1)),cstring(self.cpu.r32_reg(R.D2))))
   elif pc==dos-72:deleted.append(cstring(self.cpu.r32_reg(R.D1)))
  def run(entry):
   self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
   self.cpu.w32_reg(R.A4,globals_);self.cpu.w32_reg(R.A5,frame)
   self.cpu.w32_reg(R.A0,0xe0000);self.cpu.w32_reg(R.D6,src);self.cpu.w32_reg(R.D7,self.obj)
   self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(self.base+self.entries[entry])
   try:self.m.execute(200000)
   except StopIteration:pass
  run(12)
  numbered=[(b'Saves:Favorites/Agony-'+str(i).encode()+b'.iff',b'AVS:Charts/01 Agony-'+str(i).encode()+b'.iff') for i in range(1,10)]
  self.assertEqual(links,numbered+[(b'Saves:Favorites/Agony-QR.iff',b'AVS:Charts/01 Agony-QR.iff'),
                          (b'Saves:Favorites/Agony.tmd',b'AVS:Charts/01 Agony.tmd')])
  self.assertEqual(self.mem.r32(self.cpu.r_sp()),0xe0000) # replayed message push
  links.clear();missing_qr=True;missing_screens={b'-2.iff',b'-4.iff',b'-9.iff'}
  run(12)
  self.assertEqual(links,[pair for pair in numbered if not any(pair[1].endswith(suffix) for suffix in missing_screens)]+[(b'Saves:Favorites/Agony.tmd',b'AVS:Charts/01 Agony.tmd')])
  run(13)
  self.assertEqual(deleted,[pair[1] for pair in numbered]+[b'AVS:Charts/01 Agony-QR.iff',b'AVS:Charts/01 Agony.tmd'])

if __name__=='__main__':unittest.main()
