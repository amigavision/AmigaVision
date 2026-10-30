"""Native M68000 notification/timing/drawing gates; OS graphics calls modeled."""
import sys,struct,unittest
from pathlib import Path
from machine68k import Machine,CPUType,Register as R
sys.path.insert(0,str(Path(__file__).parent))
from patch_now_playing import patch,remove_patch,BASELINES
ROOT=Path(__file__).resolve().parents[2]
class NowPlayingTests(unittest.TestCase):
 def setUp(self):
  self.m=Machine(CPUType.M68000,2048);self.mem=self.m.mem;self.cpu=self.m.cpu
  self.original=remove_patch((ROOT/'data/avs-highres/AVSMenu').read_bytes())
  self.data=patch(self.original);self.base=struct.unpack_from('>I',self.original,28)[0]*4
  self.entries=struct.unpack_from('>12I',self.data,32+self.base)
  self.state,self.path,self.caption=[self.base+x for x in self.entries[4:7]]
  n=struct.unpack_from('>I',self.data,28)[0]*4;self.mem.w_block(0,self.data[32:32+n])
  self.a4,self.obj,self.rp,self.bm,self.font=0x90000,0x91000,0x92000,0x93000,0x94000
  self.ex,self.gfx,self.dos=0x20000,0x30000,0x40000
  self.frame=0x98000;self.mem.w32(self.frame-52,0x100)
  self.cpu.w32_reg(R.A5,self.frame)
  self.stack=0xa0000;self.ctx=0x95000;self.source=0x96000
  self.mem.w32(self.a4-40,self.ex);self.mem.w32(self.a4-52,self.gfx);self.mem.w32(self.a4-44,self.dos)
  self.mem.w32(self.obj+16,self.rp);self.mem.w32(self.rp+4,self.bm);self.mem.w32(self.rp+52,self.font)
  self.mem.w16(self.bm,80);self.mem.w16(self.bm+2,432);self.mem.w8(self.bm+5,8)
  self.mem.w16(self.font+20,14);self.mem.w16(self.font+26,11)
  self.mem.w32(self.ctx+50,0x97000)
  self.events=[];self.now=1000;self.oom=False;self.draws=[];self.allocations=[];self.signals=[]
  self.height=432;self.fontsize=14;self.pens=[]
  self.saved=None;self.surface=bytearray((i*17)%256 for i in range(640*432))
  self.functions={self.ex-132:'Forbid',self.ex-138:'Permit',self.ex-198:'AllocMem',self.ex-210:'FreeMem',self.ex-324:'Signal',0xa0be:'PaletteLength',self.dos-192:'DateStamp',self.gfx-270:'WaitTOF',self.gfx-228:'WaitBlit',self.gfx-30:'BltBitMap',self.gfx-606:'Restore',self.gfx-354:'DrawMode',self.gfx-342:'Pen',self.gfx-306:'Rect',self.gfx-54:'TextLength',self.gfx-240:'Move',self.gfx-60:'Text'}
  for addr in self.functions:self.mem.w16(addr,0x4e75)
  self.cpu.w32_reg(R.A4,self.a4);self.cpu.w32_reg(R.D4,self.obj);self.cpu.w32_reg(R.A6,self.gfx)
 def tearDown(self):self.m.cleanup()
 def string(self,addr):
  result=bytearray()
  while self.mem.r8(addr):result.append(self.mem.r8(addr));addr+=1
  return result.decode('latin1')
 def execute(self,entry,stop):
  self.mem.w16(stop,0x4e71);self.cpu.w_sr(0x2700);self.cpu.w_sp(self.stack);self.cpu.w_pc(self.base+self.entries[entry])
  def hook(pc):
   if pc==stop:raise StopIteration()
   name=self.functions.get(pc)
   if not name:return
   self.events.append(name);get=self.cpu.r32_reg
   if name=='Signal':self.signals.append((get(R.A1),get(R.D0)))
   elif name=='PaletteLength':self.cpu.w32_reg(R.D0,16)
   elif name=='AllocMem':
    self.allocations.append(get(R.D0));self.assertIn(get(R.D1),(0x10002,1))
    self.cpu.w32_reg(R.D0,0 if self.oom else 0x100000)
   elif name=='DateStamp':
    ds=get(R.D1);self.mem.w32(ds,123);self.mem.w32(ds+4,self.now//3000);self.mem.w32(ds+8,self.now%3000)
   elif name=='Pen':self.pens.append(get(R.D0))
   elif name=='TextLength':self.cpu.w32_reg(R.D0,get(R.D0)*7)
   elif name=='Move':self.xy=(get(R.D0),get(R.D1))
   elif name=='Text':self.draws.append((self.string(get(R.A0))[:get(R.D0)],self.xy))
   elif name=='BltBitMap':
    self.assertEqual((get(R.D0),get(R.D1),get(R.D2),get(R.D3),get(R.D4),get(R.D5)),(0,self.height-self.fontsize-4,0,0,640,self.fontsize+4))
    self.saved=self.surface[(self.height-self.fontsize-4)*640:]
   elif name=='Rect':
    self.rect=(get(R.D0),get(R.D1),get(R.D2),get(R.D3));self.surface[get(R.D1)*640:]=bytes((self.height-get(R.D1))*640)
   elif name=='Restore':
    self.assertEqual((get(R.D2),get(R.D3),get(R.D4),get(R.D5)),(0,self.height-self.fontsize-4,640,self.fontsize+4));self.surface[(self.height-self.fontsize-4)*640:]=self.saved
  self.cpu.set_instr_hook_callback(hook)
  try:self.m.execute(1000000)
  except StopIteration:return
  self.fail('gate did not return')
 def start(self,name):
  self.mem.w_block(self.source,name.encode('latin1')+b'\0');self.cpu.w32_reg(R.D5,self.source);self.cpu.w32_reg(R.D6,self.ctx)
  self.execute(0,0x8348)
 def tick(self):
  self.cpu.w32_reg(R.A6,self.gfx);self.cpu.w32_reg(R.D4,self.obj);self.execute(1,0x4bf2)
 def test_initial_track_centered_full_width_and_restore_at_five_seconds(self):
  original=bytes(self.surface);self.start('Data:Music/7 Launcher BGM/Space Tune.mod');self.tick()
  self.assertEqual(self.draws,[('Now Playing: Space Tune',((640-23*7)//2,427))])
  self.assertEqual(self.rect,(0,414,639,431));self.assertEqual(self.allocations,[11520])
  self.now+=249;self.tick();self.assertNotIn('FreeMem',self.events)
  self.now+=1;self.tick();self.assertEqual(bytes(self.surface),original)
  self.assertLess(self.events.index('Restore'),self.events.index('FreeMem'))
 def test_new_track_restarts_timer_and_restores_before_new_capture(self):
  self.start('one.mod');self.tick();self.now+=100;self.start('two.MOD');self.events=[];self.tick()
  self.assertEqual(self.draws[-1][0],'Now Playing: two')
  self.assertLess(self.events.index('Restore'),self.events.index('BltBitMap'))
  self.now+=249;self.events=[];self.tick();self.assertNotIn('Restore',self.events)
  self.now+=1;self.tick();self.assertIn('Restore',self.events)
 def test_no_music_no_overlay(self):
  self.tick();self.assertEqual(self.allocations,[]);self.assertEqual(self.draws,[])
 def test_failed_module_does_not_publish(self):
  self.mem.w32(self.ctx+50,0);self.start('bad.mod');self.tick();self.assertEqual(self.draws,[])
 def test_basename_suffix_and_non_suffix_preserved(self):
  for path,want in [('Data:thing.mod','thing'),('dir/sub/music.MOD','music'),('dir/some.mod.name','some.mod.name'),('mod.song','mod.song')]:
   self.start(path);self.tick();self.assertEqual(self.draws[-1][0],'Now Playing: '+want)
 def test_long_name_is_bounded_and_fits(self):
  self.start('x'*400+'.mod');self.tick();self.assertLessEqual(len(self.draws[-1][0])*7,632)
  self.assertLessEqual(len(self.string(self.path)),255)
 def test_midnight_rollover(self):
  self.now=4319850;self.start('night.mod');self.tick();self.now=100;self.tick();self.assertIn('Restore',self.events)
 def test_oom_does_not_blank_footer_or_block_navigation(self):
  original=bytes(self.surface);self.oom=True;self.start('tune.mod');self.tick()
  self.assertEqual(bytes(self.surface),original);self.assertEqual(self.draws,[])
  self.tick();self.assertEqual(len(self.allocations),1)
 def test_exit_restores_and_frees(self):
  self.start('one.mod');self.tick();self.events=[];self.execute(2,0x565e)
  self.assertEqual(self.events,['Restore','WaitBlit','FreeMem']);self.assertEqual(self.cpu.r_sp(),self.stack+0x210)
 def test_exception_cleanup_restores_and_frees(self):
  self.start('one.mod');self.tick();self.events=[];self.mem.w32(self.stack,0x12345678);self.execute(3,0x90ea)
  self.assertEqual(self.events,['Restore','WaitBlit','FreeMem'])
 def test_ecs_and_medres_palette_and_geometry(self):
  for height,font,depth in [(432,14,4),(200,7,8)]:
   self.height=height;self.fontsize=font
   self.mem.w16(self.bm+2,height);self.mem.w8(self.bm+5,depth)
   self.mem.w16(self.font+20,font);self.mem.w16(self.font+26,font-3)
   self.surface=bytearray((i*17)%256 for i in range(640*height));original=bytes(self.surface)
   self.start('tune.mod');self.tick()
   self.assertEqual(self.rect,(0,height-font-4,639,height-1))
   self.assertEqual(self.pens[-2:],[(1<<depth)-2,(1<<depth)-1])
   self.assertEqual(self.allocations[-1],80*(font+4)*depth)
   self.now+=250;self.tick();self.assertEqual(bytes(self.surface),original)
 def key(self,raw):
  self.cpu.w32_reg(R.D0,raw);self.execute(7,0x568a)
 def test_f8_pause_f9_next_and_key_debounce(self):
  self.mem.w32(self.a4-540,0x99000);self.mem.w32(self.a4-536,0x200)
  self.start('one.mod')
  self.key(0x57);self.key(0x57)
  self.assertEqual(self.signals,[(0x99000,0x200)])
  self.assertEqual(self.cpu.r32_reg(R.D0),0xff)
  self.key(0xff);self.key(0x57)
  self.assertEqual(self.signals[-1],(0x99000,0x200));self.assertEqual(len(self.signals),2)
  self.key(0xff);self.key(0x58);self.key(0x58)
  self.assertEqual(self.signals[-1],(0x99000,0x100));self.assertEqual(len(self.signals),3)
  self.key(0xff);self.key(0x58);self.assertEqual(len(self.signals),4)
 def test_other_keys_and_disabled_music(self):
  self.key(0x57);self.key(0xff);self.key(0x58);self.assertEqual(self.signals,[])
  self.key(0x20);self.assertEqual(self.cpu.r32_reg(R.D0),0x20)
 def test_copper_capacity_reserves_footer_descriptors(self):
  self.cpu.w32_reg(R.D0,123);self.execute(8,0x78fc)
  self.assertEqual(self.cpu.r32_reg(R.D4),187)
  self.assertEqual(self.mem.r32(self.cpu.r_sp()),8)
 def test_native_footer_copper_matches_popup_glyph_rows(self):
  config,screen,descriptors,palette=0x99000,0x9a000,0x9b000,0x9c000
  self.mem.w32(self.frame+8,self.font);self.mem.w32(self.frame+12,config);self.mem.w32(self.frame+16,screen)
  self.mem.w32(self.frame-24,descriptors);self.mem.w32(self.frame-12,4);self.mem.w32(self.frame-8,0x1be)
  self.mem.w32(config+104,palette);self.mem.w16(screen+14,432)
  for i in range(16):self.mem.w32(palette+4*i,0xfff-i*0x11)
  self.cpu.w32_reg(R.D0,3);self.execute(9,0x79f6)
  self.assertEqual(self.cpu.r32_reg(R.D4),10)
  for i,y in enumerate(range(416,430,2)):
   words=[self.mem.r16(descriptors+(i+3)*8+j*2) for j in range(4)]
   self.assertEqual(words,[y,0,0x1be,0xfff-i*2*0x11])
 def make_playlist(self,count):
  nodes=[0xd0010+64*i for i in range(count)]
  for i,node in enumerate(nodes):
   self.mem.w_block(node,f'track{i}.mod'.encode()+b'\0')
   self.mem.w32(node-8,nodes[i+1] if i+1<count else 0)
  self.mem.w32(self.frame-60,nodes[0] if nodes else 0)
  self.mem.w32(self.frame-20,nodes[-1] if nodes else 0)
  self.mem.w32(self.frame-88,count)
  self.mem.w32(0xa1d2,0x12345678) # native E Rand seed
  self.mem.w32(self.ctx+50,0);self.cpu.w32_reg(R.D6,self.ctx)
  self.execute(10,0x8128)
  return nodes
 def choose(self):
  self.execute(11,0x81da)
  return self.cpu.r32_reg(R.D5)
 def test_shuffled_cycle_covers_every_track_and_repeats_exactly(self):
  nodes=self.make_playlist(23)
  first=[self.choose() for _ in nodes];second=[self.choose() for _ in nodes]
  self.assertEqual(set(first),set(nodes));self.assertEqual(len(set(first)),len(nodes))
  self.assertNotEqual(first,nodes);self.assertEqual(second,first)
  self.assertEqual(self.allocations,[23*4]);self.assertEqual(self.events.count('FreeMem'),1)
  self.assertEqual(self.mem.r32(self.frame-20),first[-1])
 def test_single_track_cycles_without_allocation(self):
  nodes=self.make_playlist(1);self.assertEqual([self.choose() for _ in range(4)],nodes*4)
  self.assertEqual(self.allocations,[])
 def test_empty_playlist_exits_safely(self):
  self.make_playlist(0);self.execute(11,0x8514);self.assertEqual(self.allocations,[])
 def test_shuffle_oom_falls_back_to_sequential_cycle(self):
  self.oom=True;nodes=self.make_playlist(9)
  self.assertEqual([self.choose() for _ in range(18)],nodes*2)
  self.assertEqual(self.events.count('FreeMem'),0)
 def test_playing_track_does_not_advance_playlist(self):
  nodes=self.make_playlist(7);cursor=self.mem.r32(self.state+56)
  self.mem.w32(self.ctx+50,0x97000);self.execute(11,0x83ae)
  self.assertEqual(self.mem.r32(self.state+56),cursor)
  self.mem.w32(self.ctx+50,0);self.assertEqual(self.choose(),cursor)
 def test_playlist_many_sizes_and_indices(self):
  for count in (2,3,4,17,64,101):
   nodes=self.make_playlist(count);order=[]
   for index in range(count):
    order.append(self.choose());self.assertEqual(self.mem.r32(self.frame-36),index)
   self.assertEqual(set(order),set(nodes));self.assertEqual(self.choose(),order[0])
 def test_cd32_play_pause_is_edge_triggered_and_consumed(self):
  self.mem.w32(self.a4-540,0x99000);self.mem.w32(self.a4-536,0x200)
  for pressed in (True,True,False,True):
   self.cpu.w32_reg(R.D5,0x20000 if pressed else 0)
   self.key(0xff)
   self.assertEqual(self.cpu.r32_reg(R.D5)&0x20000,0)
  self.assertEqual(self.signals,[(0x99000,0x200),(0x99000,0x200)])
 def test_cd32_other_buttons_preserved_and_disabled_music_safe(self):
  self.cpu.w32_reg(R.D5,0x20000|0x400000|4);self.key(0xff)
  self.assertEqual(self.signals,[])
  self.assertEqual(self.cpu.r32_reg(R.D5),0x400000|4)
 def test_cd32_and_keyboard_have_independent_release_state(self):
  self.mem.w32(self.a4-540,0x99000);self.mem.w32(self.a4-536,0x200)
  self.cpu.w32_reg(R.D5,0x20000);self.key(0xff)
  self.cpu.w32_reg(R.D5,0x20000);self.key(0x57)
  self.cpu.w32_reg(R.D5,0x20000);self.key(0x57)
  self.assertEqual(len(self.signals),2)
 def test_all_profiles_idempotent_and_tail_unchanged(self):
  for profile in BASELINES:
   original=remove_patch((ROOT/'data'/profile/'AVSMenu').read_bytes());new=patch(original)
   self.assertEqual(patch(new),new);self.assertEqual(remove_patch(new),original)
   a=struct.unpack_from('>I',original,28)[0]*4;b=struct.unpack_from('>I',new,28)[0]*4
   self.assertEqual(new[32+b:],original[32+a:])
if __name__=='__main__':unittest.main()
