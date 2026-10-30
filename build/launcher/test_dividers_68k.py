"""Run the binary wrappers as actual M68000 code (machine68k required)."""
from pathlib import Path
import sys, unittest, os
from machine68k import Machine, CPUType, Register as R
sys.path.insert(0,str(Path(__file__).parent))
from patch_dividers import patch as divider_patch
from patch_now_playing import remove_patch as remove_now_playing

def patch(data, *args, **kwargs):
 # Exercise divider wrappers underneath the outer Now Playing layer.
 return divider_patch(remove_now_playing(data), *args, **kwargs)
ROOT=Path(__file__).resolve().parents[2]

class Divider68000Tests(unittest.TestCase):
 def setUp(self):
  self.m=Machine(CPUType.M68000,2048);self.mem=self.m.mem;self.cpu=self.m.cpu
  b,self.base,self.entries=patch((ROOT/os.environ.get('AVS_TEST_MENU','data/avs-highres/AVSMenu')).read_bytes(),'/tmp/av-vasm/vasmm68k_mot')
  self.mem.w_block(0,b[32:32+int.from_bytes(b[28:32],'big')*4])
  self.obj,self.nav,self.items,self.path,self.stack,self.stop=0x90000,0x91000,0x92000,0x93000,0xa0000,0xb0000
  self.mem.w32(self.obj+8,self.nav);self.mem.w32(self.nav+8,self.path);self.mem.w32(self.nav+20,self.items)
  self.mem.w_block(self.path,b'AVS:\0');self.mem.w16(self.obj+38,4)
  self.mem.w16(0x6b1c,0x4e71);self.mem.w16(0x25e0,0x4e71);self.mem.w16(self.stop,0x4e71)
  self.set_items([2,4,1,2,4,1,2])
 def tearDown(self):self.m.cleanup()
 def set_items(self,types):
  self.mem.w32(self.nav+16,len(types))
  for i,t in enumerate(types):
   item=0x94000+i*16;self.mem.w32(self.items+i*4,item);self.mem.w32(item+8,t)
   name=0x9a004+i*80;self.mem.w16(name-4,64);self.mem.w16(name-2,4)
   self.mem.w_block(name,b'Item\0');self.mem.w32(item,name);self.mem.w32(item+4,4)
 def execute(self,entry,target,regs=None):
  self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
  self.cpu.w32_reg(R.A0,self.obj)
  for register,value in (regs or {}).items():self.cpu.w32_reg(register,value)
  reached=[]
  def hook(pc):
   if pc==target:reached.append(True);raise StopIteration()
  self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(self.base+self.entries[entry])
  try:self.m.execute(200000)
  except StopIteration:pass
  self.assertTrue(reached)
 def normalize(self,index,offset=0,start=1,end=2):
  self.mem.w16(self.obj+42,offset);self.mem.w16(self.obj+36,index-offset)
  self.mem.w32(self.stack+4,end & 0xffffffff);self.mem.w32(self.stack+8,start)
  self.execute(1,self.base+self.entries[6])
  result=self.mem.r16(self.obj+42)+self.mem.r16(self.obj+36)
  self.redraw=(self.mem.r32(self.stack+8),self.mem.r32(self.stack+4))
  if self.mem.r16(self.obj+42)!=offset:
   self.assertEqual(self.redraw,(0,0xffffffff))
  elif result!=index and end!=-1:
   row=self.mem.r16(self.obj+36)
   self.assertEqual(self.redraw,(min(start,row),max(end,row)))
  return result
 def test_bidirectional_skip_and_scroll(self):
  self.assertEqual(self.normalize(3),3)
  self.assertEqual(self.normalize(4),5)
  self.assertEqual(self.mem.r16(self.obj+42),2)
  self.assertEqual(self.normalize(4,2),3)
 def test_spacer_crossings_keep_redraw_local_in_both_directions(self):
  self.mem.w16(self.obj+38,24)
  self.set_items([2,4,3,4,1,4,4,1,2])
  self.assertEqual(self.normalize(0,start=0,end=-1),0)
  self.assertEqual(self.normalize(1,start=0,end=1),2)
  self.assertEqual(self.redraw,(0,2))
  self.assertEqual(self.normalize(3,start=2,end=3),4)
  self.assertEqual(self.redraw,(2,4))
  self.assertEqual(self.normalize(5,start=4,end=5),7)
  self.assertEqual(self.redraw,(4,7))
  self.assertEqual(self.normalize(6,start=6,end=7),4)
  self.assertEqual(self.redraw,(4,7))
  self.assertEqual(self.normalize(3,start=3,end=4),2)
  self.assertEqual(self.redraw,(2,4))
  self.assertEqual(self.normalize(1,start=1,end=2),0)
  self.assertEqual(self.redraw,(0,2))
 def test_partial_normal_move_and_full_page_redraw_are_preserved(self):
  self.mem.w16(self.obj+38,24)
  self.normalize(5,start=0,end=-1)
  self.assertEqual(self.normalize(6,start=5,end=6),6)
  self.assertEqual(self.redraw,(5,6))
  self.assertEqual(self.normalize(4,start=0,end=-1),3)
  self.assertEqual(self.redraw,(0,0xffffffff))
 def test_initial_and_consecutive_dividers(self):
  self.set_items([4,4,2,4,4,1])
  self.assertEqual(self.normalize(0),2)
  self.assertEqual(self.normalize(3),5)
  self.assertEqual(self.normalize(4,2),2)
 def test_page_boundaries_and_all_dividers(self):
  self.set_items([4,2,1,4])
  self.assertEqual(self.normalize(0),1)
  self.assertEqual(self.normalize(3),2)
  self.assertEqual(self.normalize(4),2)
  self.set_items([4,4,4]);self.assertEqual(self.normalize(1),1)
 def test_new_directory_resets_direction(self):
  self.assertEqual(self.normalize(6),6)
  self.mem.w_block(self.path,b'AVS:Other.avs/\0');self.set_items([4,2,4,1])
  self.assertEqual(self.normalize(0),1)
 def test_letter_match_ignores_divider(self):
  frame=0x97000;self.cpu.w32_reg(R.A5,frame);self.mem.w32(frame+16,ord('G'));self.cpu.w32_reg(R.D0,ord('G'))
  self.cpu.w32_reg(R.D7,0x94000+16)
  self.execute(2,self.stop);self.assertFalse(self.cpu.r_sr()&4)
  self.mem.w_block(0x9a004,b'Game\0')
  self.cpu.w32_reg(R.D0,ord('G'));self.cpu.w32_reg(R.D7,0x94000)
  self.execute(2,self.stop);self.assertTrue(self.cpu.r_sr()&4)
 def test_cache_parser_marks_only_S_rows(self):
  frame,line=0x97000,0x98000;self.cpu.w32_reg(R.A5,frame)
  self.mem.w32(frame-76,line);self.mem.w32(frame-24,self.nav)
  for prefix,t in [(b'S',4),(b'D',1),(b'F',1),(b'V',3)]:
   item=0x94000+6*16;self.mem.w32(item+8,1);self.mem.w_block(line,prefix+b'[ Games ]\n\0')
   self.execute(0,0x25e0);self.assertEqual(self.mem.r32(item+8),t)

 def test_display_alias_preserves_path_and_draws_only_label(self):
  frame,line=0x97000,0x98000
  actual,label=b'Demos - By Year',b'  By Year'
  value=actual+b'\t'+label
  self.set_items([1]);item=0x94000;name=self.mem.r32(item)
  self.mem.w_block(name,value+b'\0');self.mem.w16(name-2,len(value))
  self.mem.w32(item+4,len(value))
  self.mem.w_block(line,b'A'+value+b'\n\0')
  self.mem.w32(frame-76,line);self.mem.w32(frame-24,self.nav)
  self.execute(0,0x25e0,{R.A5:frame})
  self.assertEqual(bytes(self.mem.r_block(name,len(actual)+1)),actual+b'\0')
  self.assertEqual(self.mem.r16(name-2),len(actual))
  packed=self.mem.r32(item+4)
  self.assertEqual(packed,((len(actual)+1)<<16)|len(label))
  gfx=0x99000;self.mem.w16(gfx-60,0x4e71)
  self.execute(5,gfx-60,{R.A0:name,R.D0:packed,R.A6:gfx})
  self.assertEqual(self.cpu.r32_reg(R.A0),name+len(actual)+1)
  self.assertEqual(self.cpu.r32_reg(R.D0),len(label))
  self.mem.w32(frame+16,ord('B'))
  self.execute(2,self.stop,{R.A5:frame,R.D7:item,R.D0:ord('D')})
  self.assertTrue(self.cpu.r_sr()&4)

 def test_ordinary_text_keeps_native_pointer_and_length(self):
  gfx=0x99000;self.mem.w16(gfx-60,0x4e71)
  self.execute(5,gfx-60,{R.A0:0x98000,R.D0:12,R.A6:gfx,R.D1:123})
  self.assertEqual(self.cpu.r32_reg(R.A0),0x98000)
  self.assertEqual(self.cpu.r32_reg(R.D0),12)
  self.assertEqual(self.cpu.r32_reg(R.D1),123)
 def test_explicit_favorites_prevents_automatic_duplicate(self):
  frame,method=0x97000,0x99000;self.mem.w32(frame-24,self.nav);self.mem.w16(method,0x4e75)
  for types,automatic,expected in [([2,4,3,4],1,0),([2,4,1],1,1),([2,4,1],0,0)]:
   self.set_items(types);self.cpu.w32_reg(R.A5,frame)
   self.execute(4,self.stop,{R.A1:method,R.D0:automatic})
   self.assertEqual(self.cpu.r32_reg(R.D0),expected)
   self.assertEqual(bool(self.cpu.r_sr()&4),expected==0)

 def test_viewport_is_composed_offscreen_before_single_present(self):
  self.set_items([2]*7)
  gfx,ex,globals_,rp,bm,plane,font,conf=0xc0000,0xc1000,0xc2000,0xc3000,0xc4000,0xc5000,0xc6000,0xc7000
  self.mem.w32(4,ex);self.mem.w32(globals_-52,gfx)
  self.mem.w32(self.obj+4,conf);self.mem.w32(self.obj+16,rp);self.mem.w32(self.obj+20,font)
  self.mem.w16(self.obj+32,208);self.mem.w16(self.obj+38,4)
  self.mem.w32(self.obj+28,bm)
  self.mem.w16(font+20,14);self.mem.w16(conf+26,2)
  self.mem.w16(conf+28,4);self.mem.w16(conf+30,24);self.mem.w16(conf+34,4)
  self.mem.w8(rp+24,255);self.mem.w32(rp+4,bm);self.mem.w16(bm,80);self.mem.w16(bm+2,432);self.mem.w8(bm+5,8)
  for i in range(8):self.mem.w32(bm+8+4*i,plane)
  self.mem.w16(self.obj+36,1);self.mem.w16(self.obj+42,0)
  for address in [gfx-606,gfx-228,gfx-270,gfx-342,gfx-354,gfx-306,gfx-36,ex-198,ex-210]:self.mem.w16(address,0x4e75)
  # Enable the existing transparent overlay's clean skin bitmap.
  data=(ROOT/os.environ.get('AVS_TEST_MENU','data/avs-highres/AVSMenu')).read_bytes()
  hires=int.from_bytes(data[28:32],'big')*4>0xa708 and data[0x6cb4:0x6cb6]==bytes.fromhex('6100')
  if hires:
   self.mem.w32(0xa690,plane)
   self.mem.w16(0xa6bc,80);self.mem.w16(0xa6be,432);self.mem.w8(0xa6c1,8)
   for i in range(8):self.mem.w32(0xa6bc+8+4*i,plane)
  if hires:
   self.skipTest('Hi-res uses direct composition; covered by the pixel-level test')
  allocations=[];events=[];frees=[];presents=[];frame_waits=[]
  def hook(pc):
   reg=self.cpu.r32_reg
   if pc==self.stop:raise StopIteration()
   if pc==gfx-270:frame_waits.append(pc)
   if pc==ex-198:
    allocations.append(reg(R.D0));self.assertEqual(reg(R.D1),0x10002);self.cpu.w32_reg(R.D0,0xd0000)
   if pc==ex-210:frees.append((reg(R.A1),reg(R.D0)))
   if pc in (gfx-606,gfx-306,gfx-36):
    dest=reg(R.A1)
    events.append((pc,dest,reg(R.A0)))
    if dest==rp:
     self.assertEqual(pc,gfx-606)
     self.assertNotEqual(reg(R.A0),bm)
     presents.append([reg(r) for r in (R.D0,R.D1,R.D2,R.D3,R.D4,R.D5,R.D6)])
  for start,end,offset in [(0,-1,0),(1,2,0),(0,-1,3)]:
   self.mem.w16(self.obj+42,offset)
   self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack)
   self.mem.w32(self.stack,self.stop);self.mem.w32(self.stack+4,end&0xffffffff);self.mem.w32(self.stack+8,start)
   self.cpu.w32_reg(R.A0,self.obj);self.cpu.w32_reg(R.A4,globals_)
   self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(self.base+self.entries[6])
   try:self.m.execute(1000000)
   except StopIteration:pass
   self.assertEqual(self.mem.r32(self.obj+16),rp)
  if hires:self.assertFalse(any(e[0]==gfx-36 for e in events))
  self.assertEqual(frame_waits,[])
  self.assertEqual(presents, [[4,24,4,24,208,64,0xc0], [4,40,4,40,208,32,0xc0], [4,24,4,24,208,64,0xc0]])
  # No screen-to-buffer copy after initialization, including scrolling.
  self.assertEqual(len([e for e in events if e[0]==gfx-606 and e[1]!=rp and e[2]==bm]), 7 if not hires else 1)
  self.assertEqual(allocations,[80*432*8])
  self.assertEqual(len([e for e in events if e[1]==rp]),3)
  self.assertTrue(all(e[1]!=rp for e in events[:-1] if e[0]!=gfx-606))
  self.assertTrue(any(e[1]!=rp for e in events))
  self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
  self.cpu.w32_reg(R.A4,globals_)
  # Stop at the original close routine after our buffer is released.
  close_target=0xa640 if hires else 0xc8000-66
  self.cpu.w32_reg(R.A6,0xc8000)
  def cleanup_hook(pc):
   if pc==ex-210:frees.append((self.cpu.r32_reg(R.A1),self.cpu.r32_reg(R.D0)))
   if pc==close_target:raise StopIteration()
  self.cpu.set_instr_hook_callback(cleanup_hook);self.cpu.w_pc(self.base+self.entries[7])
  try:self.m.execute(100000)
  except StopIteration:pass
  self.assertEqual(frees,[(0xd0000,80*432*8)])

 def test_fast_template_matches_transparent_text_for_all_pen_bits(self):
  # Check byte alignment, arbitrary background colors, a restricted write mask,
  # white text and the inverted selection text against JAM1 semantics.
  import random
  gfx,rp,bm,src=0xc0000,0xc1000,0xc2000,0xc3000
  self.mem.w16(gfx-606,0x4e75)
  self.mem.w32(rp+4,bm);self.mem.w8(bm+5,8)
  pattern=[0xa5,0x3c,0xf0,0x0f]*3
  self.mem.w_block(src,bytes(pattern))
  rng=random.Random(1209)
  for pen,mask in [(255,255),(254,255),(0,255),(0x93,0x5a)]:
   colors=[[rng.randrange(256) for _ in range(32)] for _ in range(6)]
   expected=[row[:] for row in colors]
   self.mem.w8(rp+24,mask)
   for y in range(3):
    for x in range(17):
     if pattern[y*4+(x+3)//8] & (0x80>>((x+3)%8)):
      old=expected[y+2][x+5]
      expected[y+2][x+5]=(old&~mask)|(pen&mask)
   calls=[]
   def hook(pc):
    if pc==self.stop:raise StopIteration()
    if pc!=gfx-606:return
    reg=self.cpu.r32_reg
    descriptor=reg(R.A0);dest=reg(R.A1);minterm=reg(R.D6)
    self.assertEqual(dest,rp);self.assertEqual(self.mem.r16(descriptor),4)
    self.assertEqual(self.mem.r16(descriptor+2),3)
    self.assertEqual(self.mem.r8(descriptor+4),8)
    self.assertEqual(self.mem.r8(descriptor+5),8)
    for plane in range(8):self.assertEqual(self.mem.r32(descriptor+8+plane*4),src)
    self.assertEqual(reg(R.D1),0)
    write=self.mem.r8(rp+24);calls.append(minterm)
    for y in range(reg(R.D5)):
     for x in range(reg(R.D4)):
      bit=bool(pattern[y*4+(x+reg(R.D0))//8] & (0x80>>((x+reg(R.D0))%8)))
      dy,dx=y+reg(R.D3),x+reg(R.D2)
      if bit:
       if minterm==0xe0:colors[dy][dx]|=write
       elif minterm==0x20:colors[dy][dx]&=~write
       else:self.fail(hex(minterm))
   self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
   for reg,value in {R.A0:src,R.A1:rp,R.A6:gfx,R.D0:3,R.D1:4,R.D2:5,R.D3:2,R.D4:17,R.D5:3,R.D6:pen}.items():self.cpu.w32_reg(reg,value)
   self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(self.base+self.entries[8])
   try:self.m.execute(100000)
   except StopIteration:pass
   self.assertEqual(colors,expected)
   self.assertEqual(self.mem.r8(rp+24),mask)
   self.assertLessEqual(len(calls),2)

 def test_direct_composition_preserves_skin_and_unaligned_viewport_edges(self):
  import numpy as np
  rng=np.random.default_rng(1022)
  gfx,rp,bm,srcbm,src=0xc0000,0xc1000,0xc2000,0xc3000,0xc5000
  bgbase,dstbase=0x100000,0x150000
  w,h,stride=640,432,80
  skin=rng.integers(240,256,size=(h,w),dtype=np.uint8)
  old_text=rng.integers(0,2,size=(h,w),dtype=np.uint8)
  pixels=skin|np.where(old_text,255,0).astype(np.uint8)
  # An old selection may have cleared bit zero, even in a solid-one skin plane.
  pixels[350:364,4:228]&=254
  mask=rng.integers(0,2,size=(768,224),dtype=np.uint8)
  self.mem.w_block(src,np.packbits(mask,axis=1).tobytes())
  self.mem.w16(gfx-228,0x4e75)
  self.mem.w32(rp+4,bm)
  for descriptor in (bm,0xa6bc):
   self.mem.w16(descriptor,stride);self.mem.w16(descriptor+2,h);self.mem.w8(descriptor+5,8)
  self.mem.w32(0xa690,bgbase)
  for plane in range(8):
   clean=bgbase+plane*stride*h;dest=dstbase+plane*stride*h
   self.mem.w32(0xa6bc+8+plane*4,clean);self.mem.w32(bm+8+plane*4,dest)
   self.mem.w_block(clean,np.packbits((skin>>plane)&1,axis=1).tobytes())
   self.mem.w_block(dest,np.packbits((pixels>>plane)&1,axis=1).tobytes())
  self.mem.w16(srcbm,28);self.mem.w16(srcbm+2,768);self.mem.w8(srcbm+5,1);self.mem.w32(srcbm+8,src)
  for x,y,sy,height in [(4,24,16,384),(4,40,48,32),(0,24,0,384),(13,24,80,384)]:
   expected=pixels.copy();expected[y:y+height,x:x+224]=skin[y:y+height,x:x+224]|np.where(mask[sy:sy+height],255,0).astype(np.uint8)
   reached=[]
   def hook(pc):
    if pc==self.stop:reached.append(True);raise StopIteration()
    # Full navigation must not fall back to the old overlay/blitter pipeline.
    self.assertNotEqual(pc,0xa480)
   self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
   for reg,value in {R.A0:srcbm,R.A1:rp,R.A6:gfx,R.D0:0,R.D1:sy,R.D2:x,R.D3:y,R.D4:224,R.D5:height,R.D6:0xc0}.items():self.cpu.w32_reg(reg,value)
   self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(self.base+self.entries[9])
   try:self.m.execute(10000000)
   except StopIteration:pass
   self.assertTrue(reached)
   actual=np.zeros((h,w),dtype=np.uint8)
   for plane in range(8):
    packed=bytes(self.mem.r_block(dstbase+plane*stride*h,stride*h))
    actual|=np.unpackbits(np.frombuffer(packed,dtype=np.uint8)).reshape(h,w)<<plane
   np.testing.assert_array_equal(actual,expected)
   pixels=actual

 def test_blank_label_replaces_previous_text_using_native_string_copy(self):
  # Execute the launcher's real StrCopy, not a replacement API stub.
  destination,source=0x98004,0x99000
  previous=b'Demo Scene'
  self.mem.w16(destination-4,64)
  self.mem.w16(destination-2,len(previous))
  self.mem.w_block(destination,previous+b'\0')
  self.mem.w_block(source,b' \n\0')
  for length in [0,1]:
   self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack)
   for offset,value in [(0,self.stop),(4,length),(8,source),(12,destination)]:
    self.mem.w32(self.stack+offset,value)
   reached=[]
   def hook(pc):
    if pc==self.stop:reached.append(True);raise StopIteration()
   self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(0x9c10)
   try:self.m.execute(10000)
   except StopIteration:pass
   self.assertTrue(reached)
   expected=previous if length==0 else b' '
   self.assertEqual(self.mem.r16(destination-2),len(expected))
   self.assertEqual(bytes(self.mem.r_block(destination,len(expected))),expected)

 def test_return_and_keypad_enter_have_identical_comparison_flags(self):
  for key,match in [(0x43,True),(0x44,True),(0x45,False),(0xff,False)]:
   self.execute(10,self.stop,{R.D0:key})
   self.assertEqual(bool(self.cpu.r_sr()&4),match)
   self.assertEqual(self.cpu.r32_reg(R.D0),key)

 def test_native_keyboard_action_accepts_both_enter_keys(self):
  for key in [0x43,0x44]:
   globals_,lowlevel=0x98000,0xc0000
   self.mem.w32(globals_-0x208,lowlevel)
   self.mem.w16(lowlevel-30,0x4e75);self.mem.w16(lowlevel-48,0x4e75)
   self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
   self.mem.w32(self.stack+4,2)
   self.cpu.w32_reg(R.A4,globals_);self.cpu.w32_reg(R.A0,self.obj)
   def hook(pc):
    if pc==self.stop:raise StopIteration()
    if pc==lowlevel-30:self.cpu.w32_reg(R.D0,0)
    if pc==lowlevel-48:self.cpu.w32_reg(R.D0,key)
   self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(0x5666)
   try:self.m.execute(200000)
   except StopIteration:pass
   self.assertEqual(self.cpu.r32_reg(R.D0),6)
   self.assertEqual(self.cpu.r32_reg(R.D1),1)
   self.assertEqual(self.cpu.r32_reg(R.D2),0)

 def prepare_search(self,char,tick,items=None):
  frame,globals_,dos=0x97000,0x98000,0xc0000
  self.mem.w32(frame+16,ord(char));self.mem.w32(globals_-44,dos)
  self.mem.w16(dos-192,0x4e75)
  if items is not None:self.mem.w32(self.nav+20,items)
  self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
  self.cpu.w32_reg(R.A4,globals_);self.cpu.w32_reg(R.A5,frame)
  self.cpu.w32_reg(R.D5,self.obj);self.cpu.w32_reg(R.D0,3)
  def hook(pc):
   if pc==dos-192:
    stamp=self.cpu.r32_reg(R.D1)
    self.mem.w32(stamp,1);self.mem.w32(stamp+4,tick//3000);self.mem.w32(stamp+8,tick%3000)
   if pc==self.stop:raise StopIteration()
  self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(self.base+self.entries[11])
  try:self.m.execute(200000)
  except StopIteration:pass
  return self.cpu.r32_reg(R.D6)

 def matches_name(self,name,divider=False,label=None):
  item,address=0x94000,0x9a004
  self.mem.w_block(address,name.encode()+b'\0')
  self.mem.w32(item,address);self.mem.w32(item+8,4 if divider else 2)
  self.mem.w32(item+4,len(name))
  if label is not None:
   offset=len(name)+1
   self.mem.w_block(address+offset,label.encode()+b'\0')
   self.mem.w32(item+4,(offset<<16)|len(label))
  self.execute(2,self.stop,{R.D7:item})
  return bool(self.cpu.r_sr()&4)

 def test_prefix_search_refines_current_selection_and_expires(self):
  self.mem.w_block(0x9a004+3*80,b'Settlers\0')
  self.assertEqual(self.prepare_search('S',100),3)
  self.assertTrue(self.matches_name('Settlers'))
  self.assertTrue(self.matches_name('Soccer'))
  self.assertEqual(self.prepare_search('E',115),2)
  self.assertTrue(self.matches_name('Settlers'))
  self.assertFalse(self.matches_name('Soccer'))
  self.assertFalse(self.matches_name('Settlers',divider=True))
  self.assertTrue(self.matches_name('Filesystem Name',label='  Settlers'))
  self.assertEqual(self.prepare_search('T',130),2)
  self.assertTrue(self.matches_name('Settlers'))
  self.assertEqual(self.prepare_search('A',190),3)
  self.assertTrue(self.matches_name('Agony'))
  self.assertFalse(self.matches_name('Settlers'))

 def test_native_search_refines_without_skipping_the_current_match(self):
  self.set_items([2,2,2,2])
  for i,name in enumerate([b'Agony',b'Banshee',b'Settlers',b'Soccer']):
   self.mem.w_block(0x9a004+i*80,name+b'\0')
  self.mem.w16(self.obj+38,4);self.mem.w16(self.obj+36,0);self.mem.w16(self.obj+42,0)
  globals_,dos,vtable,redraw=0x98000,0xc0000,0xc3000,0xc4000
  self.mem.w32(globals_-44,dos);self.mem.w16(dos-192,0x4e75)
  self.mem.w32(self.obj,vtable);self.mem.w32(vtable+28,redraw);self.mem.w16(redraw,0x4e75)
  for char,tick,expected in [('S',100,2),('E',110,2),('T',120,2),('Z',130,2),('A',200,0)]:
   self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
   self.mem.w32(self.stack+4,0);self.mem.w32(self.stack+8,0);self.mem.w32(self.stack+12,ord(char))
   self.cpu.w32_reg(R.A4,globals_);self.cpu.w32_reg(R.A0,self.obj)
   returned=[]
   def hook(pc):
    if pc==self.stop:returned.append(True);raise StopIteration()
    if pc==dos-192:
     stamp=self.cpu.r32_reg(R.D1)
     self.mem.w32(stamp,1);self.mem.w32(stamp+4,0);self.mem.w32(stamp+8,tick)
   self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(0x62b8)
   try:self.m.execute(200000)
   except StopIteration:pass
   self.assertTrue(returned)
   self.assertEqual(self.mem.r16(self.obj+36)+self.mem.r16(self.obj+42),expected)

 def test_native_search_refinement_moves_to_a_later_matching_entry(self):
  self.set_items([2,2,2,2,2])
  for i,name in enumerate([b'Agony',b'Saint Dragon',b'Shadow of the Beast',b'Street Rod',b'Stunt Car Racer']):
   self.mem.w_block(0x9a004+i*80,name+b'\0')
  self.mem.w16(self.obj+38,4);self.mem.w16(self.obj+36,0);self.mem.w16(self.obj+42,0)
  globals_,dos,vtable,redraw=0x98000,0xc0000,0xc3000,0xc4000
  self.mem.w32(globals_-44,dos);self.mem.w16(dos-192,0x4e75)
  self.mem.w32(self.obj,vtable);self.mem.w32(vtable+28,redraw);self.mem.w16(redraw,0x4e75)
  for char,tick,expected in [('S',100,1),('T',110,3),('U',120,4),('N',130,4),('Z',140,4),('S',210,1),('S',220,2),('T',230,3)]:
   self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
   self.mem.w32(self.stack+4,0);self.mem.w32(self.stack+8,0);self.mem.w32(self.stack+12,ord(char))
   self.cpu.w32_reg(R.A4,globals_);self.cpu.w32_reg(R.A0,self.obj)
   returned=[]
   def hook(pc):
    if pc==self.stop:returned.append(True);raise StopIteration()
    if pc==dos-192:
     stamp=self.cpu.r32_reg(R.D1)
     self.mem.w32(stamp,1);self.mem.w32(stamp+4,0);self.mem.w32(stamp+8,tick)
   self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(0x62b8)
   try:self.m.execute(200000)
   except StopIteration:pass
   self.assertTrue(returned)
   self.assertEqual(self.mem.r16(self.obj+36)+self.mem.r16(self.obj+42),expected)

 def test_repeated_initial_cycles_and_new_directory_resets_prefix(self):
  self.prepare_search('S',2990)
  self.assertEqual(self.prepare_search('S',2995),3)
  self.assertTrue(self.matches_name('Soccer'))
  self.prepare_search('E',3005) # continue across minute boundary
  self.assertTrue(self.matches_name('Settlers'))
  self.assertFalse(self.matches_name('Soccer'))
  self.assertEqual(self.prepare_search('A',3010,items=0x96000),3)
  self.assertTrue(self.matches_name('Agony'))

 def test_navigation_actions_reset_the_typing_prefix(self):
  self.prepare_search('S',100);self.prepare_search('E',110)
  self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
  for i,value in enumerate([51,61,71]):self.mem.w32(self.stack+4+i*4,value)
  self.cpu.w32_reg(R.D0,2)
  def hook(pc):
   if pc==self.stop:raise StopIteration()
  self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(self.base+self.entries[14])
  try:self.m.execute(200000)
  except StopIteration:pass
  self.assertEqual(self.cpu.r32_reg(R.D5),51)
  self.assertEqual(self.prepare_search('A',120),3)
  self.assertTrue(self.matches_name('Agony'))

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
  links=[];deleted=[];missing_qr=False
  def hook(pc):
   sp=self.cpu.r_sp()
   if pc==self.stop:raise StopIteration()
   if pc==0x9fce:self.cpu.w32_reg(R.D0,0xffffffff if missing_qr and cstring(self.mem.r32(sp+4)).endswith(b'-QR.iff') else 100)
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
  self.assertEqual(links,[(b'Saves:Favorites/Agony-QR.iff',b'AVS:Charts/01 Agony-QR.iff'),
                          (b'Saves:Favorites/Agony.tmd',b'AVS:Charts/01 Agony.tmd')])
  self.assertEqual(self.mem.r32(self.cpu.r_sp()),0xe0000) # replayed message push
  links.clear();missing_qr=True
  run(12)
  self.assertEqual(links,[(b'Saves:Favorites/Agony.tmd',b'AVS:Charts/01 Agony.tmd')])
  run(13)
  self.assertEqual(deleted,[b'AVS:Charts/01 Agony-QR.iff',b'AVS:Charts/01 Agony.tmd'])

 def test_typing_wait_does_not_swallow_the_next_held_letter(self):
  globals_,lowlevel=0x98000,0xc0000
  self.mem.w32(globals_-520,lowlevel)
  self.mem.w16(lowlevel-30,0x4e75);self.mem.w16(lowlevel-48,0x4e75)
  def run(start,arguments,keys):
   self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
   for i,value in enumerate(arguments):self.mem.w32(self.stack+4+i*4,value)
   self.cpu.w32_reg(R.A4,globals_);self.cpu.w32_reg(R.A0,self.obj)
   reads=[];returned=[]
   def hook(pc):
    if pc==self.stop:returned.append(True);raise StopIteration()
    if pc==lowlevel-30:self.cpu.w32_reg(R.D0,0)
    if pc==lowlevel-48:
     self.assertLess(len(reads),len(keys),'wait swallowed the next letter instead of returning')
     key=keys[len(reads)];reads.append(key);self.cpu.w32_reg(R.D0,key)
   self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(start)
   try:self.m.execute(200000)
   except StopIteration:pass
   self.assertTrue(returned)
   return reads
  run(0x5666,[0],[0x20]) # A is accepted
  self.assertEqual(self.cpu.r32_reg(R.D0),9)
  self.assertEqual(self.mem.r32(self.obj+46),ord('A'))
  self.assertEqual(run(0x59e0,[1,9],[0x20,0x28]),[0x20,0x28]) # A -> L, no neutral gap
  run(0x5666,[0],[0x28])
  self.assertEqual(self.cpu.r32_reg(R.D0),9)
  self.assertEqual(self.mem.r32(self.obj+46),ord('L'))

 def test_favorite_confirmation_restores_metadata_after_a_short_delay(self):
  frame,globals_,dos=0x97000,0x98000,0xc0000
  self.mem.w32(frame-8,self.obj);self.mem.w32(globals_-44,dos)
  self.mem.w16(dos-198,0x4e75);self.mem.w16(0x6e40,0x4e75)
  self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
  self.cpu.w32_reg(R.A4,globals_);self.cpu.w32_reg(R.A5,frame)
  events=[]
  def hook(pc):
   if pc==self.stop:raise StopIteration()
   if pc==dos-198:events.append(('delay',self.cpu.r32_reg(R.D1)))
   if pc==0x6e40:events.append(('restore',self.cpu.r32_reg(R.A0)))
  self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(self.base+self.entries[17])
  try:self.m.execute(200000)
  except StopIteration:pass
  self.assertEqual(events,[('delay',25),('restore',self.obj)])
  self.assertEqual(self.cpu.r_sp(),self.stack+20)

 def test_native_removal_clears_progress_before_confirmation(self):
  globals_,dos,vtable,clear,draw=0x98000,0xc0000,0xc1000,0xc2000,0xc3000
  self.mem.w32(globals_-44,dos);self.mem.w32(self.obj,vtable)
  for offset,address in [(4,draw),(8,clear),(24,0x6d54)]:self.mem.w32(vtable+offset,address)
  for address in [clear,draw,dos-198,dos-72,0x9fce]:self.mem.w16(address,0x4e75)
  self.mem.w16(self.path-4,255);self.mem.w16(self.path-2,4)
  self.mem.w16(self.obj+36,0);self.mem.w16(self.obj+42,0)
  events=[];returned=[]
  self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
  self.cpu.w32_reg(R.A4,globals_);self.cpu.w32_reg(R.A0,self.obj)
  def hook(pc):
   if pc==self.stop:returned.append(True);raise StopIteration()
   if pc==clear:events.append('clear')
   if pc==draw:
    sp=self.cpu.r_sp();length=self.mem.r32(sp+8);address=self.mem.r32(sp+16)
    events.append(bytes(self.mem.r_block(address,length)).decode('latin-1').strip())
   if pc==0x9fce:self.cpu.w32_reg(R.D0,100)
  self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(0x617a)
  try:self.m.execute(200000)
  except StopIteration:pass
  self.assertTrue(returned)
  self.assertEqual(events,['clear','Removing favorite...','clear','Favorite removed!'])

 def test_diagnostic_trace_records_keys_actions_and_prefix_state(self):
  import struct
  binary,base,entries=patch((ROOT/'data/avs-highres/AVSMenu').read_bytes(),'/tmp/av-vasm/vasmm68k_mot',trace_input=True)
  code=binary[32:32+int.from_bytes(binary[28:32],'big')*4]
  self.mem.w_block(0,code);self.base,self.entries=base,entries
  header=code.index(b'AVSTYP13')
  self.test_typing_wait_does_not_swallow_the_next_held_letter()
  self.prepare_search('S',100);self.prepare_search('T',110)
  count=self.mem.r32(header+8)
  records=[]
  for i in range(count):
   raw=bytes(self.mem.r_block(header+12+i*148,148))
   tag=struct.unpack_from('>I',raw)[0];regs=struct.unpack_from('>15I',raw,4)
   state=raw[64:];length=struct.unpack_from('>H',state,16)[0]
   records.append((tag,regs,state[18:18+length]))
  self.assertEqual({row[0] for row in records},{1,2,3})
  self.assertEqual([row[1][0] for row in records if row[0]==1],[ord('A'),ord('L')])
  self.assertEqual([row[2] for row in records if row[0]==2],[b'S',b'ST'])
  # Verify the diagnostic is written on normal launcher cleanup, not per key.
  globals_,dos=0x98000,0xc0000
  self.mem.w32(globals_-44,dos)
  for address in [dos-30,dos-48,dos-36]:self.mem.w16(address,0x4e75)
  written=[];closed=[];returned=[]
  self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
  self.cpu.w32_reg(R.A4,globals_)
  def dump_hook(pc):
   if pc==0xa640:returned.append(True);raise StopIteration()
   if pc==dos-30:self.cpu.w32_reg(R.D0,42)
   if pc==dos-48:
    self.assertEqual(self.cpu.r32_reg(R.D1),42)
    written.append(bytes(self.mem.r_block(self.cpu.r32_reg(R.D2),self.cpu.r32_reg(R.D3))))
   if pc==dos-36:closed.append(self.cpu.r32_reg(R.D1))
  self.cpu.set_instr_hook_callback(dump_hook);self.cpu.w_pc(base+entries[7])
  try:self.m.execute(200000)
  except StopIteration:pass
  self.assertTrue(returned);self.assertEqual(closed,[42])
  self.assertEqual(len(written),1)
  self.assertEqual(written[0][:8],b'AVSTYP13')
  self.assertEqual(len(written[0]),12+count*148)

if __name__=='__main__':unittest.main()
