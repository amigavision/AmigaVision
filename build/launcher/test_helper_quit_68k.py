"""Execute the shutdown patch and native handler/cleanup on a modeled M68000.
Run with machine68k available. Library calls are modeled, not hardware tested.
"""
import hashlib,struct,sys,unittest
from pathlib import Path
from machine68k import Machine,CPUType,Register as R
sys.path.insert(0,str(Path(__file__).parent))
from patch_helper_quit import patch,remove_patch,BASELINE
ROOT=Path(__file__).resolve().parents[2]

class QuitTests(unittest.TestCase):
 def setUp(self):
  self.original=remove_patch((ROOT/'data/avs-highres/AVSHelper').read_bytes())
  self.patched=patch(self.original)
  self.base=struct.unpack_from('>I',self.original,28)[0]*4
  self.pending=self.base+72
  self.m=Machine(CPUType.M68000,2048);self.mem=self.m.mem;self.cpu=self.m.cpu
  self.mem.w_block(0,self.patched[32:32+struct.unpack_from('>I',self.patched,28)[0]*4])
  self.exec,self.dos,self.gfx=0x20000,0x30000,0x40000
  self.a4,self.frame,self.ldr,self.msg=0x90000,0xa0000,0x91000,0x92000
  self.stack,self.stop,self.conf=0xb0000,0xc0000,0x93000
  self.mem.w32(self.a4-40,self.exec);self.mem.w32(self.a4-44,self.dos);self.mem.w32(self.a4-52,self.gfx)
  self.mem.w32(self.frame+8,self.ldr);self.mem.w32(self.ldr,0x94000)
  self.mem.w32(self.ldr+16,self.conf);self.mem.w32(self.msg+20,0)
  self.calls=[];self.release=False
  self.io_calls={self.exec-480:'AbortIO',self.exec-474:'WaitIO',self.exec-450:'CloseDevice',self.exec-660:'DeleteIORequest',self.exec-672:'DeleteMsgPort'}
 def tearDown(self):self.m.cleanup()
 def run_at(self,pc,stop):
  self.cpu.w_sr(0x2000);self.cpu.w_sp(self.stack);self.mem.w32(self.stack,self.stop)
  self.cpu.w32_reg(R.A4,self.a4);self.cpu.w32_reg(R.A5,self.frame)
  self.mem.w32(self.stack+4,self.ldr)
  for addr in [self.exec-372,self.exec-378,self.gfx-228,self.dos-198,self.exec-360,self.exec-210,0x4ec6,*self.io_calls]:self.mem.w16(addr,0x4e75)
  self.mem.w16(stop,0x4e71)
  self.cpu.w_pc(pc)
  def hook(addr):
   if addr==stop:raise StopIteration()
   name={self.exec-372:'GetMsg',self.exec-378:'ReplyMsg',self.gfx-228:'WaitBlit',self.dos-198:'Delay',self.exec-360:'RemPort',self.exec-210:'FreeMem',0x4ec6:'Dispose'}.get(addr) or self.io_calls.get(addr)
   if name:
    self.calls.append(name)
    if name=='Delay':raise AssertionError('Delay in interrupt')
    if name=='GetMsg':self.cpu.w32_reg(R.D0,self.msg)
    if name=='ReplyMsg':
     self.assertEqual(self.cpu.r32_reg(R.A1),self.msg)
     self.assertEqual(self.mem.r32(self.pending),0)
     self.mem.w_block(self.conf,b'\xa5'*128) # sender may free config immediately
  self.cpu.set_instr_hook_callback(hook)
  try:self.m.execute(200000)
  except StopIteration:return
  self.fail('did not reach stop')
 def defer(self,busy):
  self.mem.w32(self.ldr+34,busy)
  self.run_at(0x3826,self.stop)
  self.assertEqual(self.calls,['GetMsg'])
  self.assertEqual(self.mem.r32(self.ldr+4),1)
  self.assertEqual(self.mem.r32(self.pending),self.msg)
 def test_busy_quit_returns_without_delay_or_reply(self):self.defer(0xffffffff)
 def test_idle_quit_also_defers_reply(self):self.defer(0)
 def test_other_messages_keep_native_reply(self):
  self.mem.w32(self.msg+20,6);self.mem.w32(self.ldr+30,123)
  self.run_at(0x3826,self.stop)
  self.assertEqual(self.calls,['GetMsg','ReplyMsg']);self.assertEqual(self.mem.r32(self.msg+28),123)
 def test_reply_after_normal_cleanup(self):
  self.defer(0xffffffff);self.calls=[]
  self.mem.w32(self.frame-60,self.ldr)
  # No slideshow: shared config remains valid until the final ReplyMsg.
  self.mem.w16(self.conf+64,0)
  self.run_at(0x4602,0x4870)
  self.assertEqual(self.calls,['Dispose','WaitBlit','ReplyMsg'])
  self.assertEqual(self.mem.r32(self.pending),0)
 def test_reply_after_exception_cleanup(self):
  self.defer(0xffffffff);self.calls=[]
  self.mem.w32(self.frame-60,self.ldr)
  self.run_at(0x4660,0x4870)
  self.assertEqual(self.calls,['Dispose','WaitBlit','ReplyMsg'])
 def test_slideshow_timer_is_drained_before_reply(self):
  self.defer(0xffffffff);self.calls=[]
  self.mem.w32(self.frame-60,self.ldr);self.mem.w16(self.conf+64,1)
  self.mem.w32(self.frame-8,1);self.mem.w32(self.frame-12,0x96000);self.mem.w32(self.frame-16,0x97000)
  self.run_at(0x4602,0x4870)
  self.assertEqual(self.calls,['AbortIO','WaitIO','CloseDevice','DeleteIORequest','DeleteMsgPort','Dispose','WaitBlit','ReplyMsg'])
 def test_active_composition_is_restored_and_freed_before_reply(self):
  self.defer(0xffffffff);self.calls=[]
  qrbase=struct.unpack_from('>I',self.original,32+self.base-4)[0]
  state=qrbase+struct.unpack_from('>I',self.original,32+qrbase+24)[0]
  self.mem.w32(state,0x100000);self.mem.w32(state+4,0x95000)
  self.mem.w32(state+8,0x98000);self.mem.w32(state+12,1)
  self.mem.w32(0x95004,0x99000);self.mem.w32(self.frame-60,self.ldr)
  self.run_at(0x4660,0x4870)
  self.assertEqual(self.mem.r32(0x95004),0x98000)
  self.assertEqual(self.mem.r32(state),0)
  self.assertEqual(self.calls,['WaitBlit','FreeMem','Dispose','WaitBlit','ReplyMsg'])
 def test_exit_without_quit_does_not_reply(self):
  self.run_at(0x4868,0x4870)
  self.assertEqual(self.calls,[]);self.assertEqual(self.cpu.r_sp(),self.stack+0x344)
 def test_reply_preserves_registers_and_original_stack_adjustment(self):
  self.mem.w32(self.pending,self.msg)
  self.cpu.w32_reg(R.D7,0x12345678)
  self.run_at(0x4868,0x4870)
  self.assertEqual(self.calls,['WaitBlit','ReplyMsg'])
  self.assertEqual(self.cpu.r32_reg(R.D7),0x12345678)
  self.assertEqual(self.cpu.r32_reg(R.D0),0)
  self.assertEqual(self.cpu.r_sp(),self.stack+0x344)
 def test_idempotence_and_hunk_tail(self):
  self.assertEqual(patch(self.patched),self.patched)
  n=struct.unpack_from('>I',self.patched,28)[0]*4
  self.assertEqual(self.patched[32+n:],self.original[32+self.base:])
  self.assertEqual(hashlib.sha256(self.original).hexdigest(),BASELINE)

if __name__=='__main__':unittest.main()
