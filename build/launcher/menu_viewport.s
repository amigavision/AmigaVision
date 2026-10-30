; Bounded one-bit menu cache. Keep the proven direct AGA display compositor.
 org PATCH_BASE
 dc.l allocate_rows-PATCH_BASE,initial_rows-PATCH_BASE,window_source-PATCH_BASE
 dc.l state-PATCH_BASE,ensure_window-PATCH_BASE

allocate_rows:
 movem.l d1-d7/a0-a6,-(sp)
 move.l 16(a0),d0 ; original navigator item count
 move.l -12(a5),a2 ; menu object during native create_menu_bitmap
 move.l 4(a2),a0
 moveq #0,d1
 move.w 34(a0),d1 ; configured visible rows, independent of list length
 cmp.l d1,d0
 bls bounded_count
 move.l d1,d0
bounded_count:
 lea state(pc),a0
 move.l a2,(a0)
 move.l d0,4(a0)
 clr.l 8(a0) ; native initial rendering starts at item zero
 move.l 8(a2),a1
 move.l 20(a1),12(a0)
 movem.l (sp)+,d1-d7/a0-a6
 bra.w $6836

initial_rows:
 move.l state+4(pc),d0
 bra.w $69a2

window_source:
 movem.l d0-d7/a0-a6,-(sp)
 move.l d6,a2
 bsr ensure_window
 movem.l (sp)+,d0-d7/a0-a6
 move.l d6,a0
 moveq #0,d0 ; source mask now begins at viewport row zero
 bra.w $6b8e

ensure_window:
 ; a2=menu object. Native create_menu_bitmap owns this fixed-size bitmap.
 lea state(pc),a3
 moveq #0,d7
 move.w 42(a2),d7 ; requested absolute first row
 move.l 4(a3),d6 ; cache capacity
 tst.l d6
 beq ensure_done
 cmpa.l (a3),a2
 bne invalidate
 move.l 8(a2),a0
 move.l 20(a0),d0
 cmp.l 12(a3),d0
 bne invalidate
 move.l d7,d0
 sub.l 8(a3),d0
 beq ensure_done
 move.l d0,d5 ; signed row delta
 move.l d0,d1
 bpl abs_delta
 neg.l d1
abs_delta:
 cmp.l d6,d1
 bhs invalidate
 ; Scroll the off-screen one-bit cache, preserving rows already rendered.
 move.l d1,16(a3) ; number of newly exposed rows
 move.l 24(a2),a1
 move.l 52(a1),a0
 moveq #0,d4
 move.w 20(a0),d4
 move.l 4(a2),a0
 add.w 26(a0),d4 ; font height + leading
 move.l 28(a2),a0
 move.l a0,a1
 moveq #0,d0
 moveq #0,d1
 moveq #0,d2
 moveq #0,d3
 move.l 16(a3),d0
 mulu.w d4,d0
 tst.l d5
 bmi scroll_down
 move.l d0,d1
 bra shift_ready
scroll_down:
 move.l d0,d3
shift_ready:
 moveq #0,d0
 move.l d6,d5
 sub.l 16(a3),d5
 mulu.w d4,d5
 moveq #0,d4
 move.w 32(a2),d4 ; mask width
 move.l a2,-(sp)
 suba.l a2,a2
 move.l #$c0,d6
 moveq #1,d7
 move.l -52(a4),a6
 jsr -30(a6)
 jsr -228(a6)
 move.l (sp)+,a2
 moveq #0,d7
 move.w 42(a2),d7
 move.l d7,d0
 sub.l 8(a3),d0
 bmi draw_top
 move.l 4(a3),d5
 sub.l 16(a3),d5
 move.l 4(a3),d6
 bra draw_range
 draw_top:
 moveq #0,d5
 move.l 16(a3),d6
 bra draw_range
invalidate:
 moveq #0,d5
 move.l 4(a3),d6
 move.l a2,(a3)
 move.l 8(a2),a0
 move.l 20(a0),12(a3)
draw_range:
 ; Clear and draw only new rows into the off-screen text mask.
 move.l 24(a2),a1
 move.l 52(a1),a0
 moveq #0,d4
 move.w 20(a0),d4
 move.l 4(a2),a0
 add.w 26(a0),d4
 move.l d4,20(a3)
render_row:
 cmp.l d6,d5
 bhs rendered
 move.l d5,d1
 mulu.w d4,d1
 moveq #0,d0
 moveq #0,d2
 move.w 32(a2),d2
 subq.l #1,d2
 move.l d1,d3
 add.l d4,d3
 subq.l #1,d3
 move.l 24(a2),a1
 move.l -52(a4),a6
 ; The native mask RastPort is private and JAM1; use black for erasure.
 move.l d1,-(sp)
 move.l a1,-(sp)
 moveq #0,d0
 jsr -342(a6)
 move.l (sp)+,a1
 move.l (sp)+,d1
 moveq #0,d0
 jsr -306(a6)
 move.l 24(a2),a1
 moveq #1,d0
 jsr -342(a6)
 move.l 8(a2),a0
 move.l d5,d0
 add.l d7,d0
 cmp.l 16(a0),d0
 bhs row_done ; unused rows stay blank
 lsl.l #2,d0
 move.l 20(a0),a0
 move.l (a0,d0.l),a0
 move.l a0,24(a3)
 move.l 24(a2),a1
 move.l 52(a1),a0
 moveq #0,d0
 move.w 24(a0),d0 ; font xsize
 moveq #0,d1
 move.w 26(a0),d1 ; baseline
 addq.l #1,d1 ; same 1px inset as native rendering
 move.l d5,d2
 mulu.w d4,d2
 add.l d2,d1
 jsr -240(a6)
 move.l 24(a3),a0
 move.l 4(a0),d0 ; packed alias offset/length, exactly as native Text wrapper
 move.l (a0),a0
 move.l d0,d1
 swap d1
 and.l #$ffff,d1
 adda.l d1,a0
 and.l #$ffff,d0
 beq row_done
 move.l 24(a2),a1
 jsr -60(a6)
row_done:
 move.l 20(a3),d4
 addq.l #1,d5
 bra render_row
rendered:
 move.l -52(a4),a6
 jsr -228(a6) ; finish mask updates before direct display composition
 move.l d7,8(a3)
ensure_done:
 rts
 cnop 0,4
state: dcb.l 7,0
 cnop 0,4
 dc.b 'AVSVIEW1'
 dc.l PATCH_BASE
