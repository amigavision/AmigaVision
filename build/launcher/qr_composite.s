; AGA experiment: present screenshot + cached QR in one bitmap blit.
; Fixed screen storage 640x432x8; supported thumbnails 404x280, QR 50x50.
; Labels remain optional; enabled labels use the native load/draw path.
 org PATCH_BASE
 dc.l stage_begin-PATCH_BASE,skip_fade-PATCH_BASE,qr_gate-PATCH_BASE
 dc.l qr_loaded-PATCH_BASE,publish-PATCH_BASE,cleanup-PATCH_BASE
 dc.l state-PATCH_BASE
stage_begin:
 movem.l d0-d7/a0-a6,-(sp)
 lea state(pc),a3
 clr.l 12(a3)
 move.l -60(a5),a2
 move.l 8(a2),a2
 move.l a2,4(a3)
 move.l 4(a2),a0
 move.l a0,8(a3)
 cmpi.w #80,(a0)
 bne begin_done
 cmpi.w #432,2(a0)
 blt begin_done
 cmpi.b #8,5(a0)
 bne begin_done
 tst.l (a2) ; Layer must be NIL; native helper InitRastPort clears it.
 bne begin_done
 move.l -4(a5),a0
 cmpi.w #404,8(a0)
 bne begin_done
 cmpi.w #280,12(a0)
 bne begin_done
 move.l -60(a5),a0
 move.l 16(a0),a0
 moveq #0,d0
 move.w 38(a0),d0
 cmpi.w #236,d0
 bgt begin_done
 tst.w d0
 bmi begin_done
 moveq #0,d1
 move.w 40(a0),d1
 tst.w d1
 bmi begin_done
 cmpi.w #152,d1
 bgt begin_done
 ; Only compose QR when it fits entirely inside the thumbnail.
 move.w 94(a0),d2
 sub.w d0,d2
 bmi begin_done
 cmpi.w #354,d2
 bgt begin_done
 move.w 96(a0),d2
 sub.w d1,d2
 bmi begin_done
 cmpi.w #230,d2
 bgt begin_done
 tst.l (a3)
 bne have_memory
 move.l #281088,d0 ; full-screen stage + 64x64x8 QR cache + one-plane mask
 move.l #$10002,d1 ; MEMF_CLEAR | MEMF_CHIP
 move.l -40(a4),a6
 jsr -198(a6)
 tst.l d0
 beq begin_done
 move.l d0,(a3)
 lea stage_bitmap(pc),a0
 move.w #80,(a0)
 move.w #432,2(a0)
 move.b #8,5(a0)
 lea 8(a0),a1
 moveq #7,d1
stage_planes:
 move.l d0,(a1)+
 add.l #34560,d0
 dbra d1,stage_planes
 lea cache_bitmap(pc),a0
 move.w #8,(a0)
 move.w #64,2(a0)
 move.b #8,5(a0)
 lea 8(a0),a1
 moveq #7,d1
cache_planes:
 move.l d0,(a1)+
 add.l #512,d0
 dbra d1,cache_planes
 move.l d0,32(a3)
have_memory:
 ; Seed only the image rectangle; visible menu/metadata are never copied back.
 move.l 8(a3),a0
 lea stage_bitmap(pc),a1
 bsr image_coordinates
 move.l d0,d2
 move.l d1,d3
 bsr blit
 ; Seed the optional caption area too, preserving its transparent skin.
 bsr label_coordinates
 tst.l d6
 beq caption_seeded
 move.l d0,d2
 move.l d1,d3
 move.l 8(a3),a0
 lea stage_bitmap(pc),a1
 bsr blit
caption_seeded:
 lea stage_bitmap(pc),a0
 move.l a0,4(a2)
 moveq #1,d0
 move.l d0,12(a3)
begin_done:
 movem.l (sp)+,d0-d7/a0-a6
 lea -8(sp),sp
 bra.w $427a
skip_fade:
 ; il.close frees its RGB array before the later QR path. Retain our own
 ; four-byte-stride rgbcolor values before allowing that cleanup to run.
 movem.l d0-d7/a0-a6,-(sp)
 lea saved_palette(pc),a1
 moveq #0,d0
 move.w #255,d1
clear_palette:
 move.l d0,(a1)+
 dbra d1,clear_palette
 move.l -4(a5),a0
 move.l 20(a0),d1
 cmpi.l #256,d1
 bls palette_count_ok
 move.l #256,d1
palette_count_ok:
 tst.l d1
 beq palette_copied
 move.l 24(a0),a0
 move.l a0,d0
 beq palette_copied
 lea saved_palette(pc),a1
 subq.w #1,d1
copy_palette:
 move.l (a0)+,(a1)+
 dbra d1,copy_palette
palette_copied:
 lea state(pc),a0
 moveq #1,d0
 move.l d0,20(a0)
 movem.l (sp)+,d0-d7/a0-a6
 bra.w $43ae
qr_gate:
 movem.l d0-d7/a0-a6,-(sp)
 lea state(pc),a3
 move.b $54d2(pc),d0 ; native entry_changed flag (same-entry guard restored)
 bne new_entry
 tst.l 12(a3)
 beq native_qr
 move.l -60(a5),a0
 move.l 16(a0),a0
 cmpi.w #-1,100(a0)
 bne native_qr ; native caption remains correct when re-enabled
 tst.l 24(a3)
 beq native_qr
 tst.l 16(a3)
 beq cached_done ; cached missing QR: no repeated disk lookup
 lea cache_bitmap(pc),a0
 lea stage_bitmap(pc),a1
 moveq #0,d0
 moveq #0,d1
 bsr qr_coordinates_dest
 bsr replay_qr
cached_done:
 movem.l (sp)+,d0-d7/a0-a6
 bra publish
new_entry:
 clr.l 16(a3)
 clr.l 24(a3)
native_qr:
 move.l #1,28(a3)
 movem.l (sp)+,d0-d7/a0-a6
 move.l -72(a5),-(sp)
 bra.w $43fe
qr_loaded:
 ; Hook only reached after the QR load_body call, not a failed open/parse.
 lea 16(sp),sp
 movem.l d0-d7/a0-a6,-(sp)
 lea state(pc),a3
 clr.l 16(a3)
 tst.l 12(a3)
 beq loaded_done
 move.l -32(a5),a0
 cmpi.w #50,8(a0)
 bne uncacheable
 cmpi.w #50,12(a0)
 bne uncacheable
 ; Save the final 8-plane colored QR, including its black pixels.
 lea stage_bitmap(pc),a0
 lea cache_bitmap(pc),a1
 bsr qr_coordinates_source
 moveq #0,d2
 moveq #0,d3
 bsr blit
 ; Build a one-bit QR FOREGROUND mask for pen 244 exactly. Do not cache
 ; background pixels or use the helper RastPort's inherited plane mask.
 lea cache_bitmap(pc),a0
 move.l 32(a3),a1
 moveq #0,d2
 move.l #244,d4
 moveq #127,d7
make_cache_mask:
 moveq #-1,d0
 moveq #0,d3
 lea 8(a0),a2
mask_plane:
 move.l (a2)+,a6
 move.l (a6,d2.w),d1
 btst d3,d4
 bne foreground_bit_set
 not.l d1
foreground_bit_set:
 and.l d1,d0
 addq.w #1,d3
 cmpi.w #8,d3
 bne mask_plane
 move.l d0,(a1)+
 addq.w #4,d2
 dbra d7,make_cache_mask
 moveq #1,d0
 move.l d0,16(a3)
 bra loaded_done
uncacheable:
 clr.l 28(a3)
 clr.l 24(a3)
loaded_done:
 movem.l (sp)+,d0-d7/a0-a6
 bra.w $45b0
publish:
 movem.l d0-d7/a0-a6,-(sp)
 lea state(pc),a3
 tst.l 12(a3)
 beq publish_fade
 tst.l 28(a3)
 beq cache_ready
 move.l #1,24(a3)
cache_ready:
 move.l 4(a3),a2
 move.l 8(a3),4(a2)
 lea stage_bitmap(pc),a0
 move.l 8(a3),a1
 bsr image_coordinates
 move.l d0,d2
 move.l d1,d3
 bsr blit
 ; Optional caption is outside the thumbnail in this layout. Copy its region
 ; independently; it cannot make the QR appear later than the screenshot.
 move.l -32(a5),a1
 tst.w 10(a1)
 beq presented
 bsr label_coordinates
 tst.l d6
 beq presented
 move.l d0,d2
 move.l d1,d3
 lea stage_bitmap(pc),a0
 move.l 8(a3),a1
 bsr blit
presented:
 clr.l 12(a3)
publish_fade:
 tst.l 20(a3)
 beq finish
 clr.l 20(a3)
 ; Mirror native status checks and palette arguments, but run AFTER publish.
 move.l -60(a5),a0
 cmpi.l #1,4(a0)
 beq finish
 lea saved_palette(pc),a0
 move.l a0,-(sp)
 move.l -60(a5),a0
 move.l 12(a0),-(sp)
 moveq #0,d0
 move.w 20(a0),d0
 ext.l d0
 move.l d0,-(sp)
 pea 2.w
 bsr.w $3542
 lea 16(sp),sp
finish:
 lea state(pc),a3 ; native E fade routine may clobber A2/A3
 clr.l 28(a3)
 movem.l (sp)+,d0-d7/a0-a6
 moveq #0,d0
 move.l -60(a5),a0
 bra.w $45e2
cleanup:
 movem.l d0-d7/a0-a6,-(sp)
 lea state(pc),a3
 tst.l 12(a3)
 beq cleanup_free
 move.l 4(a3),a0
 move.l 8(a3),4(a0)
 clr.l 12(a3)
cleanup_free:
 tst.l (a3)
 beq cleanup_done
 move.l -52(a4),a6
 jsr -228(a6) ; WaitBlit
 move.l (a3),a1
 clr.l (a3)
 move.l #281088,d0
 move.l -40(a4),a6
 jsr -210(a6) ; FreeMem
cleanup_done:
 movem.l (sp)+,d0-d7/a0-a6
 move.l (sp)+,-88(a4)
 bra.w $4664
image_coordinates:
 move.l -60(a5),a6
 move.l 16(a6),a6
 moveq #0,d0
 move.w 38(a6),d0
 moveq #0,d1
 move.w 40(a6),d1
 move.l #404,d4
 move.l #280,d5
 rts
qr_coordinates_source:
 move.l -60(a5),a6
 move.l 16(a6),a6
 moveq #0,d0
 move.w 94(a6),d0
 moveq #0,d1
 move.w 96(a6),d1
 moveq #50,d4
 moveq #50,d5
 rts
qr_coordinates_dest:
 move.l -60(a5),a6
 move.l 16(a6),a6
 moveq #0,d2
 move.w 94(a6),d2
 moveq #0,d3
 move.w 96(a6),d3
 moveq #50,d4
 moveq #50,d5
 rts
label_coordinates:
 moveq #0,d6
 move.l -60(a5),a6
 move.l 16(a6),a6
 cmpi.w #-1,100(a6)
 beq label_region_done
 moveq #0,d0
 move.w 94(a6),d0
 subq.l #8,d0
 moveq #0,d1
 move.w 100(a6),d1
 tst.l d0
 bmi label_region_done
 cmpi.l #576,d0
 bgt label_region_done
 cmpi.l #400,d1
 bgt label_region_done
 moveq #64,d4
 moveq #32,d5
 moveq #1,d6
label_region_done:
 rts
replay_qr:
 ; Redraw cached 1-bit modules with a known pen/mode/plane mask.
 movem.l d0-d7/a0-a6,-(sp)
 move.l 4(a3),a2
 moveq #0,d7
 move.b 24(a2),d7
 move.l d7,-(sp)
 moveq #0,d7
 move.b 25(a2),d7
 move.l d7,-(sp)
 moveq #0,d7
 move.b 28(a2),d7
 move.l d7,-(sp)
 move.b #$ff,24(a2)
 move.l -52(a4),a6
 move.l a2,a1
 move.l #244,d0
 jsr -342(a6) ; SetAPen
 move.l a2,a1
 moveq #0,d0
 jsr -354(a6) ; SetDrMd JAM1
 move.l 32(a3),a0
 move.l a2,a1
 moveq #0,d0
 moveq #8,d1
 bsr qr_coordinates_dest
 move.l -52(a4),a6
 jsr -36(a6) ; BltTemplate: cached module mask, not an image rectangle
 jsr -228(a6)
 move.l a2,a1
 move.l (sp)+,d0
 jsr -354(a6)
 move.l a2,a1
 move.l (sp)+,d0
 jsr -342(a6)
 move.l (sp)+,d0
 move.b d0,24(a2)
 movem.l (sp)+,d0-d7/a0-a6
 rts
blit:
 ; BltBitMap(A0, D0,D1, A1,D2,D3, D4,D5, $c0, $ff, NIL).
 ; Preserve caller registers: graphics.library may clobber scratch registers.
 movem.l d0-d7/a0-a6,-(sp)
 move.l #$c0,d6
 move.l #$ff,d7
 suba.l a2,a2
 move.l -52(a4),a6
 jsr -30(a6)
 jsr -228(a6) ; cache/source must be complete before reuse or fade
 movem.l (sp)+,d0-d7/a0-a6
 rts
 cnop 0,4
state: dcb.l 9,0 ; allocation, RP, real bitmap, active, cached QR present
stage_bitmap: dcb.b 40,0
cache_bitmap: dcb.b 40,0
 cnop 0,4
saved_palette: dcb.l 256,0 ; rgbcolor has a four-byte E object stride
 dc.b 'QRCOMP03'
 dc.l PATCH_BASE
