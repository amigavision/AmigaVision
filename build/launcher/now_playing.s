; Producer only publishes a bounded path. Menu task owns drawing and cleanup.
 org PATCH_BASE
 dc.l started-PATCH_BASE,tick-PATCH_BASE,leave-PATCH_BASE,cleanup-PATCH_BASE
 dc.l state-PATCH_BASE,path-PATCH_BASE,caption-PATCH_BASE
 dc.l keys-PATCH_BASE,copper_capacity-PATCH_BASE,copper_footer-PATCH_BASE
 dc.l shuffle_playlist-PATCH_BASE,playlist_next-PATCH_BASE
started:
 movem.l d0-d7/a0-a6,-(sp)
 move.l d6,a0
 tst.l 50(a0)
 beq started_done
 move.l -40(a4),a6
 jsr -132(a6) ; Forbid: don't expose a partial filename
 move.l d5,a0
 lea path(pc),a1
 move.w #254,d0
publish_path:
 move.b (a0)+,(a1)+
 dbeq d0,publish_path
 clr.b (a1)
 lea state(pc),a0
 move.l -52(a5),48(a0) ; music task next-track signal mask
 addq.l #1,(a0)
 move.l -40(a4),a6
 jsr -138(a6)
started_done:
 movem.l (sp)+,d0-d7/a0-a6
 moveq #-1,d0
 move.l d6,a0
 bra.w $8348

tick:
 jsr -270(a6) ; original WaitTOF
 movem.l d0-d7/a0-a6,-(sp)
 lea state(pc),a3
 move.l d4,44(a3)
 move.l (a3),d0
 cmp.l 4(a3),d0
 beq check_expiry
 bsr hide
 move.l -40(a4),a6
 jsr -132(a6)
 lea path(pc),a0
 lea caption(pc),a1
 adda.w #13,a1
 move.w #255,d0
snapshot:
 move.b (a0)+,(a1)+
 dbeq d0,snapshot
 clr.b (a1)
 move.l (a3),4(a3)
 move.l -40(a4),a6
 jsr -138(a6)
 bsr basename
 bsr show
 bra tick_done
check_expiry:
 tst.l 8(a3)
 beq tick_done
 bsr clock
 sub.l 16(a3),d0
 bpl clock_elapsed
 add.l #4320000,d0 ; DateStamp midnight rollover, 50 ticks/sec
clock_elapsed:
 cmp.l #250,d0
 blo tick_done
 bsr hide
tick_done:
 movem.l (sp)+,d0-d7/a0-a6
 bra.w $4bf2

basename:
 lea caption+13(pc),a0
 move.l a0,a1
find_base:
 move.b (a0)+,d0
 beq base_found
 cmp.b #'/',d0
 beq new_base
 cmp.b #':',d0
 beq new_base
 cmp.b #92,d0
 bne find_base
new_base:
 move.l a0,a1
 bra find_base
base_found:
 lea caption+13(pc),a0
 moveq #0,d2
base_copy:
 move.b (a1)+,d0
 move.b d0,(a0)+
 beq base_copied
 addq.w #1,d2
 bra base_copy
base_copied:
 cmp.w #4,d2
 blo suffix_done
 move.l -5(a0),d0
 or.l #$20202020,d0
 cmp.l #$2e6d6f64,d0 ; case-insensitive .mod suffix only
 bne suffix_done
 clr.b -5(a0)
 subq.w #4,d2
suffix_done:
 add.w #13,d2
 move.l d2,32(a3)
 rts

clock:
 lea stamp(pc),a0
 move.l a0,d1
 move.l -44(a4),a6
 jsr -192(a6) ; DateStamp: ticks are always 1/50 s, PAL or NTSC
 lea stamp(pc),a0
 move.l 4(a0),d0
 mulu.w #3000,d0
 add.l 8(a0),d0
 rts

show:
 move.l 44(a3),a0
 move.l 16(a0),a0 ; menu's displayed RastPort
 move.l a0,d0
 beq show_done
 lea overlay_rp(pc),a1
 moveq #24,d0
clone_rp:
 move.l (a0)+,(a1)+
 dbra d0,clone_rp
 lea overlay_rp(pc),a2
 move.l 4(a2),a0
 move.l a0,40(a3)
 moveq #0,d0
 move.w (a0),d0
 cmp.w #128,d0
 bhi show_done
 tst.w d0
 beq show_done
 lsl.l #3,d0
 move.l d0,20(a3)
 moveq #0,d0
 move.b 5(a0),d0
 beq show_done
 cmp.b #8,d0
 bhi show_done
 move.l d0,36(a3)
 move.l 52(a2),a1 ; current textfont
 move.l a1,d0
 beq show_done
 moveq #0,d0
 move.w 20(a1),d0 ; tf_YSize
 addq.w #4,d0
 cmp.w #64,d0
 bhi show_done
 move.l d0,24(a3)
 moveq #0,d1
 move.w 2(a0),d1
 sub.l d0,d1
 bmi show_done
 move.l d1,28(a3)
 move.l 20(a3),d0
 lsr.l #3,d0
 mulu.w 26(a3),d0 ; low word of height
 move.l d0,d2 ; size per plane
 mulu.w 38(a3),d0 ; low word of depth
 move.l d0,12(a3)
 move.l #$10002,d1
 move.l -40(a4),a6
 jsr -198(a6)
 tst.l d0
 beq show_done
 move.l d0,8(a3)
 lea saved_bitmap(pc),a0
 move.l 20(a3),d1
 lsr.l #3,d1
 move.w d1,(a0)
 move.l 24(a3),d1
 move.w d1,2(a0)
 move.l 36(a3),d1
 move.b d1,5(a0)
 subq.w #1,d1
 lea 8(a0),a0
planes:
 move.l d0,(a0)+
 add.l d2,d0
 dbra d1,planes
 ; Save the entire instruction strip before blanking it.
 move.l 40(a3),a0
 lea saved_bitmap(pc),a1
 moveq #0,d0
 move.l 28(a3),d1
 moveq #0,d2
 moveq #0,d3
 move.l 20(a3),d4
 move.l 24(a3),d5
 move.l #$c0,d6
 move.l #$ff,d7
 suba.l a2,a2
 move.l -52(a4),a6
 jsr -30(a6) ; BltBitMap
 jsr -228(a6)
 lea overlay_rp(pc),a2
 move.b #$ff,24(a2)
 move.l a2,a1
 moveq #0,d0
 jsr -354(a6) ; JAM1
 moveq #1,d0
 move.l 36(a3),d1
 lsl.l d1,d0
 subq.l #2,d0 ; fixed black pen: 254 AGA, 14 ECS
 move.l a2,a1
 jsr -342(a6)
 moveq #0,d0
 move.l 28(a3),d1
 move.l 20(a3),d2
 subq.l #1,d2
 move.l 28(a3),d3
 add.l 24(a3),d3
 subq.l #1,d3
 move.l a2,a1
 jsr -306(a6)
 moveq #1,d0
 move.l 36(a3),d1
 lsl.l d1,d0
 subq.l #1,d0 ; fixed white/Copper pen
 move.l a2,a1
 jsr -342(a6)
measure:
 lea caption(pc),a0
 move.l 32(a3),d0
 move.l a2,a1
 jsr -54(a6) ; TextLength
 move.l 20(a3),d1
 subq.l #8,d1
 cmp.l d1,d0
 ble fits
 subq.l #1,32(a3)
 lea caption(pc),a0
 move.l 32(a3),d0
 clr.b (a0,d0.w)
 bra measure
fits:
 move.l 20(a3),d1
 sub.l d0,d1
 lsr.l #1,d1
 move.l d1,d0
 move.l 52(a2),a0
 moveq #0,d1
 move.w 26(a0),d1 ; tf_Baseline
 add.l 28(a3),d1
 addq.l #2,d1
 move.l a2,a1
 jsr -240(a6) ; Move
 lea caption(pc),a0
 move.l 32(a3),d0
 move.l a2,a1
 jsr -60(a6) ; Text
 jsr -228(a6)
 bsr clock
 move.l d0,16(a3)
show_done:
 rts

hide:
 tst.l 8(a3)
 beq hide_done
 lea saved_bitmap(pc),a0
 lea overlay_rp(pc),a1
 moveq #0,d0
 moveq #0,d1
 moveq #0,d2
 move.l 28(a3),d3
 move.l 20(a3),d4
 move.l 24(a3),d5
 move.l #$c0,d6
 move.l -52(a4),a6
 jsr -606(a6)
 jsr -228(a6)
 move.l 8(a3),a1
 clr.l 8(a3)
 move.l 12(a3),d0
 move.l -40(a4),a6
 jsr -210(a6)
hide_done:
 rts

leave:
 movem.l d0-d7/a0-a6,-(sp)
 lea state(pc),a3
 bsr hide
 movem.l (sp)+,d0-d7/a0-a6
 moveq #0,d0
 adda.l #$210,sp
 bra.w $565e
cleanup:
 movem.l d0-d7/a0-a6,-(sp)
 lea state(pc),a3
 bsr hide
 movem.l (sp)+,d0-d7/a0-a6
 move.l (sp)+,-88(a4)
 bra.w $90ea
; F8/F9 are handled once per key press without blocking the menu loop.
keys:
 and.l #$ffff,d0
 cmp.w #$57,d0 ; raw F8
 beq music_key
 cmp.w #$58,d0 ; raw F9
 beq music_key
 movem.l a0,-(sp)
 lea state(pc),a0
 clr.l 52(a0)
 movem.l (sp)+,a0
 bra.w $568a
music_key:
 movem.l d1-d7/a0-a6,-(sp)
 lea state(pc),a0
 cmp.l 52(a0),d0
 beq music_key_done
 move.l d0,52(a0)
 move.l -540(a4),a1 ; existing music process task
 move.l a1,d1
 beq music_key_done
 cmp.w #$57,d0
 beq pause_key
 move.l 48(a0),d0
 bra signal_key
pause_key:
 move.l -536(a4),d0 ; native pause/resume signal
signal_key:
 tst.l d0
 beq music_key_done
 move.l -40(a4),a6
 jsr -324(a6) ; Signal
music_key_done:
 movem.l (sp)+,d1-d7/a0-a6
 move.l #$ff,d0 ; consume the music key
 bra.w $568a

; Reserve descriptors for one extra footer band. Existing menu/metadata
; coordinates and Copper ordering are otherwise unchanged.
copper_capacity:
 move.l d0,d4
 add.l #64,d4
 pea 8.w
 bra.w $78fc
copper_footer:
 movem.l d0-d7/a0-a6,-(sp)
 move.l d0,d4 ; next descriptor index from native metadata gradient
 move.l 8(a5),a0 ; font
 moveq #0,d0
 move.w 20(a0),d0
 move.l 16(a5),a0 ; screen
 moveq #0,d1
 move.w 14(a0),d1
 sub.l d0,d1
 subq.l #2,d1 ; first glyph row, matching popup's 2px top inset
 add.l d1,d0
 subq.l #1,d0 ; final glyph row
 move.l 12(a5),a0 ; config
 move.l 104(a0),-(sp) ; existing configured Copper palette
 move.l -24(a5),-(sp) ; allocated descriptor array
 move.l d1,-(sp) ; first row
 move.l d0,-(sp) ; final row
 clr.l -(sp) ; horizontal start at left screen edge, full-width label
 move.l -8(a5),-(sp) ; native text color register
 move.l -12(a5),-(sp) ; native interlace step
 move.l d4,-(sp) ; first descriptor index
 bsr.w $7710 ; native Copper gradient generator
 lea 32(sp),sp
 move.l d0,(sp) ; return updated descriptor count
 movem.l (sp)+,d0-d7/a0-a6
 move.l d0,d4
 move.l d6,-(sp)
 bra.w $79f6

; Build one permutation of the native linked filename list. Only an array
; of pointers is allocated temporarily, in ordinary memory, never Chip RAM.
shuffle_playlist:
 movem.l d0-d7/a0-a6,-(sp)
 lea state(pc),a3
 clr.l 60(a3) ; next ordinal
 move.l -60(a5),56(a3) ; initial cursor (also OOM fallback)
 move.l -88(a5),d7 ; number of scanned modules
 cmp.l #2,d7
 blo shuffle_done
 cmp.l #65535,d7 ; native Rand uses a 16-bit bound
 bhi shuffle_done
 move.l d7,d0
 lsl.l #2,d0
 moveq #1,d1 ; MEMF_PUBLIC, no Chip requirement
 move.l -40(a4),a6
 jsr -198(a6)
 tst.l d0
 beq shuffle_done ; sequential cycle still covers every entry
 move.l d0,a2
 move.l d0,a1
 move.l -60(a5),a0
 move.l d7,d6
fill_playlist:
 move.l a0,d0
 beq broken_playlist
 move.l a0,(a1)+
 move.l -8(a0),a0
 subq.l #1,d6
 bne fill_playlist
 move.l d7,d6
 subq.l #1,d6
shuffle_pair:
 move.l d6,d0
 addq.l #1,d0
 move.l d0,-(sp)
 bsr.w $a196 ; Rand(i+1), range [0,i]
 addq.l #4,sp
 lsl.l #2,d0
 move.l a2,a0
 adda.l d0,a0
 move.l d6,d0
 lsl.l #2,d0
 move.l a2,a1
 adda.l d0,a1
 move.l (a0),d0
 move.l (a1),(a0)
 move.l d0,(a1)
 subq.l #1,d6
 bne shuffle_pair
 ; Relink the original E strings; no path data is copied or duplicated.
 move.l a2,a0
 move.l (a0)+,a1
 move.l a1,-60(a5)
 move.l a1,56(a3)
 move.l d7,d6
 subq.l #1,d6
relink_playlist:
 move.l (a0)+,d0
 move.l d0,-8(a1)
 move.l d0,a1
 subq.l #1,d6
 bne relink_playlist
 clr.l -8(a1)
 move.l a1,-20(a5) ; retain native tail invariant
broken_playlist:
 move.l a2,a1
 move.l d7,d0
 lsl.l #2,d0
 move.l -40(a4),a6
 jsr -210(a6)
shuffle_done:
 movem.l (sp)+,d0-d7/a0-a6
 movem.l d3-d4,-(sp) ; replay original seed-following instruction
 bra.w $8128

playlist_next:
 movem.l d0-d7/a0-a6,-(sp)
 move.l d6,a0
 tst.l 50(a0)
 bne playlist_playing ; native loop must not replace a playing module
 lea state(pc),a3
 move.l 56(a3),a0
 move.l a0,d0
 bne playlist_choose
 move.l -60(a5),a0 ; end reached: repeat the identical shuffled order
playlist_choose:
 move.l a0,d0
 beq playlist_empty
 move.l a0,20(sp) ; return filename as d5
 move.l -8(a0),56(a3)
 move.l 60(a3),-36(a5) ; native last_mod_index bookkeeping
 addq.l #1,60(a3)
 tst.l 56(a3)
 bne playlist_chosen
 clr.l 60(a3)
playlist_chosen:
 movem.l (sp)+,d0-d7/a0-a6
 bra.w $81da
playlist_playing:
 movem.l (sp)+,d0-d7/a0-a6
 bra.w $83ae
playlist_empty:
 movem.l (sp)+,d0-d7/a0-a6
 bra.w $8514

 cnop 0,4
state: dcb.l 16,0
path: dcb.b 260,0
caption: dc.b 'Now Playing: '
 dcb.b 260,0
 cnop 0,4
overlay_rp: dcb.b 100,0
saved_bitmap: dcb.b 40,0
stamp: dcb.l 3,0
 cnop 0,4
 dc.b 'AVSNOW03'
 dc.l PATCH_BASE
