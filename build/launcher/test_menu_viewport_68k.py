"""Execute viewport caching and native composition with modeled graphics calls."""
import sys,struct,unittest
from pathlib import Path
from machine68k import Machine,CPUType,Register as R
sys.path.insert(0,str(Path(__file__).parent))
from patch_menu_viewport import patch,remove_patch
ROOT=Path(__file__).resolve().parents[2]
class ViewportTests(unittest.TestCase):
 def setUp(self):
  self.m=Machine(CPUType.M68000,4096);self.mem=self.m.mem;self.cpu=self.m.cpu
  self.original=remove_patch((ROOT/'data/avs-highres/AVSMenu').read_bytes());self.data=patch(self.original)
  self.base=struct.unpack_from('>I',self.original,28)[0]*4
  self.entries=struct.unpack_from('>6I',self.data,32+self.base);self.state=self.base+self.entries[3]
  self.mem.w_block(0,self.data[32:32+struct.unpack_from('>I',self.data,28)[0]*4])
  self.obj,self.nav,self.conf,self.font=0x90000,0x91000,0x92000,0x93000
  self.rp,self.bm,self.items,self.gfx,self.glob=0x94000,0x95000,0xa0000,0x20000,0xb0000
  self.frame,self.stack,self.stop=0xc0000,0xd0000,0xe0000
  self.mem.w32(self.obj+4,self.conf);self.mem.w32(self.obj+8,self.nav);self.mem.w32(self.obj+20,self.font)
  self.mem.w32(self.obj+24,self.rp);self.mem.w32(self.obj+28,self.bm);self.mem.w16(self.obj+32,224)
  self.mem.w16(self.obj+38,24);self.mem.w16(self.conf+34,24);self.mem.w16(self.conf+26,2)
  self.mem.w32(self.nav+20,self.items);self.mem.w32(self.rp+4,self.bm);self.mem.w32(self.rp+52,self.font)
  self.mem.w16(self.font+20,14);self.mem.w16(self.font+24,7);self.mem.w16(self.font+26,11)
  self.mem.w16(self.bm,28);self.mem.w16(self.bm+2,385);self.mem.w8(self.bm+5,1)
  self.mem.w32(self.bm+8,0x180000);self.mem.w32(self.glob-52,self.gfx)
  self.mem.w32(self.frame-12,self.obj)
  self.draws=[];self.shifts=[];self.rows=[None]*24;self.pen=1
  self.calls={self.gfx-30:'BltBitMap',self.gfx-228:'WaitBlit',self.gfx-342:'Pen',self.gfx-306:'Rect',self.gfx-240:'Move',self.gfx-60:'Text'}
  for addr in self.calls:self.mem.w16(addr,0x4e75)
  self.set_items(4000)
 def tearDown(self):self.m.cleanup()
 def set_items(self,count):
  self.count=count;self.mem.w32(self.nav+16,count)
  for i in range(count):
   item=0x100000+i*16;name=0x200000+i*48
   self.mem.w32(self.items+4*i,item);self.mem.w32(item,name);value=f'Entry {i}'.encode()
   self.mem.w32(item+4,len(value));self.mem.w32(item+8,2);self.mem.w_block(name,value+b'\0')
 def execute(self,entry,stop,regs=None):
  self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop);self.mem.w16(stop,0x4e71)
  self.cpu.w32_reg(R.A4,self.glob);self.cpu.w32_reg(R.A5,self.frame);self.cpu.w32_reg(R.A2,self.obj)
  for r,v in (regs or {}).items():self.cpu.w32_reg(r,v)
  def hook(pc):
   if pc==stop:raise StopIteration()
   name=self.calls.get(pc);get=self.cpu.r32_reg
   if name=='Pen':self.pen=get(R.D0)
   elif name=='BltBitMap':
    src,dst,height=get(R.D1)//16,get(R.D3)//16,get(R.D5)//16
    self.assertEqual(get(R.A0),self.bm);self.assertEqual(get(R.A1),self.bm)
    self.assertEqual((get(R.D4),get(R.D6),get(R.D7)),(224,0xc0,1))
    old=self.rows[:];self.rows[dst:dst+height]=old[src:src+height];self.shifts.append((src,dst,height))
   elif name=='Rect':
    self.assertEqual(self.pen,0);a,b=get(R.D1)//16,get(R.D3)//16
    for i in range(a,b+1):self.rows[i]=None
   elif name=='Move':self.xy=(get(R.D0),get(R.D1))
   elif name=='Text':
    value=bytes(self.mem.r_block(get(R.A0),get(R.D0))).decode()
    self.draws.append(value);self.rows[(self.xy[1]-12)//16]=value
  self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(self.base+self.entries[entry])
  try:self.m.execute(2000000)
  except StopIteration:return
  self.fail('gate did not reach stop')
 def initialize(self,count=4000):
  if count!=self.count:self.set_items(count)
  self.execute(0,0x6836,{R.A0:self.nav});cap=min(count,24)
  self.assertEqual(self.cpu.r32_reg(R.D0),cap)
  self.rows=[f'Entry {i}' if i<count else None for i in range(cap)]
  return cap
 def scroll(self,offset):
  self.mem.w16(self.obj+42,offset);self.execute(4,self.stop)
 def expect(self,offset):self.assertEqual(self.rows,[f'Entry {i}' if i<self.count else None for i in range(offset,offset+min(self.count,24))])
 def test_allocation_height_is_bounded_for_large_and_small_lists(self):
  for count in (0,1,7,24,25,4000):
   cap=self.initialize(count);self.assertEqual(28*(cap*16+1),28*(min(count,24)*16+1))
   self.execute(1,0x69a2);self.assertEqual(self.cpu.r32_reg(R.D0),cap)
 def test_highlight_only_reuses_text_without_any_rendering(self):
  self.initialize();self.scroll(0);self.assertEqual(self.draws,[]);self.assertEqual(self.shifts,[])
 def test_one_row_scroll_down_draws_only_one_entry(self):
  self.initialize();self.scroll(1);self.expect(1)
  self.assertEqual(self.draws,['Entry 24']);self.assertEqual(self.shifts,[(1,0,23)])
 def test_one_row_scroll_up_draws_only_one_entry(self):
  self.initialize();self.scroll(1);self.draws=[];self.shifts=[];self.scroll(0);self.expect(0)
  self.assertEqual(self.draws,['Entry 0']);self.assertEqual(self.shifts,[(0,1,23)])
 def test_partial_jumps_reuse_overlap_and_page_jumps_bound_work(self):
  self.initialize()
  for offset,work in [(3,3),(8,5),(2,6),(2000,24),(1976,24),(1999,23),(0,24)]:
   self.draws=[];self.scroll(offset);self.expect(offset);self.assertEqual(len(self.draws),work)
 def test_long_scroll_and_end_of_list(self):
  self.initialize()
  for offset in [*range(1,75),3976,3975,3976,0]:self.scroll(offset);self.expect(offset)
 def test_initial_restored_position_rebuilds_only_visible_rows(self):
  self.initialize();self.scroll(2500);self.expect(2500);self.assertEqual(len(self.draws),24)
 def test_directory_change_with_same_menu_object_invalidates(self):
  self.initialize();self.scroll(3);self.initialize(7);self.draws=[];self.scroll(0);self.expect(0);self.assertEqual(self.draws,[])
 def test_aliases_and_blank_dividers_render_correctly(self):
  self.initialize();alias=0x96000;value=b'Disk Mags - By Year\0  By Year\0';self.mem.w_block(alias,value)
  item=self.mem.r32(self.items+24*4);self.mem.w32(item,alias);self.mem.w32(item+4,((len(value.split(bytes(1))[0])+1)<<16)|9);self.mem.w32(item+8,4)
  self.scroll(1);self.assertEqual(self.rows[-1],'  By Year')
  item=self.mem.r32(self.items+25*4);self.mem.w32(item+4,0);self.mem.w32(item+8,4)
  self.scroll(2);self.assertIsNone(self.rows[-1])
 def test_window_source_y_and_selection_source_are_local(self):
  self.initialize();self.mem.w16(self.obj+42,3000)
  self.execute(2,0x6b8e,{R.D6:self.obj});self.assertEqual(self.cpu.r32_reg(R.D0),0)
  self.assertEqual(self.data[32+0xa4e4:32+0xa4e8],bytes.fromhex('4e714e71'))
 def test_native_height_calculation_allocates_only_viewport_pixels(self):
  for count in (0,1,24,1000,4000):
   self.set_items(count)
   self.execute(0,0x6866,{R.A0:self.nav})
   self.assertEqual(self.mem.r16(self.obj+34),min(count,24)*16+1)
 def test_native_selection_row_is_relative_to_cached_view(self):
  self.mem.w16(self.obj+36,23);self.mem.w16(self.obj+42,3000)
  self.mem.w32(self.stack+76,self.obj)
  # Execute the actual native selection source calculation, with only the
  # obsolete absolute offset addition replaced by NOPs.
  self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w16(0xa4fc,0x4e71)
  def hook(pc):
   if pc==0xa4fc:raise StopIteration()
  self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(0xa4da)
  try:self.m.execute(10000)
  except StopIteration:pass
  self.assertEqual(self.cpu.r32_reg(R.D1),23*16)
 def test_skin_never_overwrites_highlight_during_composition(self):
  import numpy as np
  self.initialize();self.mem.w16(self.conf+30,24)
  displayrp,displaybm=0x96000,0x97000
  cleanbase,destbase=0x280000,0x300000
  self.mem.w32(displayrp+4,displaybm)
  self.mem.w32(0xa690,cleanbase)
  for bm in (displaybm,0xa6bc):
   self.mem.w16(bm,80);self.mem.w16(bm+2,432);self.mem.w8(bm+5,8)
  rng=np.random.default_rng(1030)
  skin=rng.integers(240,254,size=(432,640),dtype=np.uint8)
  mask=rng.integers(0,2,size=(385,224),dtype=np.uint8)
  self.mem.w_block(0x180000,np.packbits(mask,axis=1).tobytes())
  for plane in range(8):
   self.mem.w32(0xa6bc+8+plane*4,cleanbase+plane*80*432)
   self.mem.w32(displaybm+8+plane*4,destbase+plane*80*432)
   self.mem.w_block(cleanbase+plane*80*432,np.packbits((skin>>plane)&1,axis=1).tobytes())
  for selected,start,rows,divider in [(23,0,24,False),(10,0,24,False),(10,9,3,False),(10,0,2,False),(10,10,2,False),(10,0,24,True)]:
   self.mem.w16(self.obj+36,selected)
   self.mem.w32(self.mem.r32(self.items+selected*4)+8,4 if divider else 2)
   pixels=skin.copy();top=24+selected*16
   pixels[top:top+16,4:228]=255-mask[selected*16:selected*16+16]
   expected=pixels.copy();y=24+start*16;h=rows*16
   expected[y:y+h,4:228]=skin[y:y+h,4:228]|np.where(mask[start*16:(start+rows)*16],255,0).astype(np.uint8)
   if not divider and y<top+16 and y+h>top:
    lo,hi=max(y,top),min(y+h,top+16)
    expected[lo:hi,4:228]=pixels[lo:hi,4:228]
   for plane in range(8):self.mem.w_block(destbase+plane*80*432,np.packbits((pixels>>plane)&1,axis=1).tobytes())
   self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop);self.mem.w16(self.stop,0x4e71)
   for r,v in {R.A0:self.bm,R.A1:displayrp,R.A6:self.gfx,R.D0:0,R.D1:start*16,R.D2:4,R.D3:y,R.D4:224,R.D5:h,R.D6:0xc0}.items():self.cpu.w32_reg(r,v)
   regions=[]
   def hook(pc):
    if pc==0x6c98:raise StopIteration()
    if pc==0xaf3c:regions.append((self.cpu.r32_reg(R.D1),self.cpu.r32_reg(R.D3),self.cpu.r32_reg(R.D5)))
   self.mem.w16(0x6c98,0x4e71)
   self.cpu.set_instr_hook_callback(hook);self.cpu.w_pc(0x6c94)
   try:self.m.execute(10000000)
   except StopIteration:pass
   actual=np.zeros((432,640),dtype=np.uint8)
   for plane in range(8):actual|=np.unpackbits(np.frombuffer(bytes(self.mem.r_block(destbase+plane*80*432,80*432)),dtype=np.uint8)).reshape(432,640)<<plane
   np.testing.assert_array_equal(actual,expected)
   self.assertLessEqual(len(regions),2)
   for sy,dy,height in regions:
    self.assertEqual(sy,dy-24)
    if not divider:self.assertTrue(dy+height<=top or dy>=top+16)
 def test_composition_hook_keeps_native_subroutine_return(self):
  self.assertEqual(self.data[32+0x6c94:32+0x6c96],bytes.fromhex('6100'))
  displacement=struct.unpack_from('>h',self.data,32+0x6c96)[0]
  self.assertEqual(0x6c96+displacement,self.base+self.entries[5])
 def test_idempotent_and_preserves_original_hunk_tail(self):
  self.assertEqual(patch(self.data),self.data);self.assertEqual(remove_patch(self.data),self.original)
  n=struct.unpack_from('>I',self.data,28)[0]*4
  self.assertEqual(self.data[32+n:],self.original[32+self.base:])
if __name__=='__main__':unittest.main()
