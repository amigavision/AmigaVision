; Navigation invalidates helper work before the next delayed LOAD command.
 org PATCH_BASE
 ifd MENU_PATCH
 dc.l navigation-PATCH_BASE,resume_load-PATCH_BASE,paused-PATCH_BASE
navigation:
 movem.l d0-d7/a0-a6,-(sp)
 tst.l d6
 beq navigation_done
 cmpi.l #9,d6
 bhi navigation_done
 clr.l -32(a5) ; restart the existing idle delay, even at a list boundary
 lea paused(pc),a1
 tst.l (a1)
 bne navigation_done
 move.l d4,a0
 move.l 12(a0),a0
 move.l a0,d0
 beq navigation_done
 lea paused(pc),a1
 move.l #1,(a1)
 move.l a0,-(sp)
 pea 7.w ; CANCEL, acknowledged immediately by the software interrupt
 pea 0.w
 move.l (a0),a1
 move.l 12(a1),a1
 jsr (a1)
 lea 12(sp),sp
navigation_done:
 movem.l (sp)+,d0-d7/a0-a6
 bra.w OLD_NAVIGATION
resume_load:
 lea paused(pc),a0
 clr.l (a0)
 move.l d7,a0
 move.l 12(a0),a0
 bra.w $6e18
 cnop 0,4
paused: dc.l 0
 else
 dc.l command-PATCH_BASE,resume-PATCH_BASE,loop_gate-PATCH_BASE
 dc.l open_gate-PATCH_BASE,header_gate-PATCH_BASE,fade_gate-PATCH_BASE
 dc.l decode_gate-PATCH_BASE,qr_gate-PATCH_BASE,publish_gate-PATCH_BASE
 dc.l fade_rgb32-PATCH_BASE,fade_rgb4-PATCH_BASE,fade_in-PATCH_BASE
 dc.l qr_open-PATCH_BASE,qr_header-PATCH_BASE,qr_draw-PATCH_BASE,qr_decode-PATCH_BASE
 dc.l paused-PATCH_BASE
command:
 cmpi.l #7,d5
 bne native_command
 movem.l d0/a0,-(sp)
 lea paused(pc),a0
 move.l #1,(a0)
 addq.l #1,4(a0)
 move.l 8(a5),a0
 addq.l #1,22(a0) ; invalidate the in-flight image generation
 movem.l (sp)+,d0/a0
 bra.w $3a2e ; native ReplyMsg, with no blocking work in the interrupt
native_command:
 moveq #6,d0
 cmp.l d5,d0
 bra.w $3a10
resume:
 lea paused(pc),a0
 clr.l (a0)
 addq.l #1,4(a0)
 move.l 8(a5),a0
 bra.w $39c8
loop_gate:
 movem.l d0-d7/a0-a6,-(sp)
 lea paused(pc),a0
 tst.l (a0)
 bne abort_image
 movem.l (sp)+,d0-d7/a0-a6
 move.l -28(a5),d0
 bra.w $3e3c
open_gate:
 movem.l d0-d7/a0-a6,-(sp)
 bsr cancelled
 tst.l d0
 bne abort_image
 movem.l (sp)+,d0-d7/a0-a6
 move.l -80(a5),-(sp)
 bra.w $420c
header_gate:
 movem.l d0-d7/a0-a6,-(sp)
 bsr cancelled
 tst.l d0
 bne abort_image
 movem.l (sp)+,d0-d7/a0-a6
 move.l -4(a5),a0
 bra.w $4226
fade_gate:
 movem.l d0-d7/a0-a6,-(sp)
 bsr cancelled
 tst.l d0
 bne abort_image
 lea paused(pc),a0
 move.l 4(a0),8(a0)
 movem.l (sp)+,d0-d7/a0-a6
 move.l -60(a5),a0
 bra.w $4258
decode_gate:
 movem.l d0-d7/a0-a6,-(sp)
 bsr cancelled
 tst.l d0
 bne abort_image
 movem.l (sp)+,d0-d7/a0-a6
 bra.w OLD_STAGE
qr_gate:
 movem.l d0-d7/a0-a6,-(sp)
 bsr cancelled
 tst.l d0
 bne abort_image
 movem.l (sp)+,d0-d7/a0-a6
 bra.w $53de
publish_gate:
 movem.l d0-d7/a0-a6,-(sp)
 bsr cancelled
 tst.l d0
 bne abort_image
 movem.l (sp)+,d0-d7/a0-a6
 bra.w OLD_PUBLISH
qr_open:
 movem.l d0-d7/a0-a6,-(sp)
 bsr cancelled
 tst.l d0
 bne abort_image
 movem.l (sp)+,d0-d7/a0-a6
 move.l -72(a5),-(sp)
 bra.w $4444
qr_header:
 movem.l d0-d7/a0-a6,-(sp)
 bsr cancelled
 tst.l d0
 bne abort_image
 movem.l (sp)+,d0-d7/a0-a6
 move.l -32(a5),a0
 bra.w $445e
qr_draw:
 movem.l d0-d7/a0-a6,-(sp)
 bsr cancelled
 tst.l d0
 bne abort_image
 movem.l (sp)+,d0-d7/a0-a6
 lea -8(sp),sp
 bra.w $4490
qr_decode:
 movem.l d0-d7/a0-a6,-(sp)
 bsr cancelled
 tst.l d0
 bne abort_image
 movem.l (sp)+,d0-d7/a0-a6
 move.l -60(a5),a0
 bra.w $4576
; Palette fades yield to navigation on each frame too. These routines use
; their own stack frames, so compare the saved job epoch without using a5.
fade_rgb32:
 movem.l d0/a0,-(sp)
 bsr fade_cancelled
 tst.l d0
 bne fade_out_aborted
 movem.l (sp)+,d0/a0
 move.l 16(a5),a0
 bra.w $3344
fade_rgb4:
 movem.l d0/a0,-(sp)
 bsr fade_cancelled
 tst.l d0
 bne fade_out_aborted
 movem.l (sp)+,d0/a0
 move.l 16(a5),a0
 bra.w $349e
fade_out_aborted:
 movem.l (sp)+,d0/a0
 bra.w $34b2
fade_in:
 movem.l d0/a0,-(sp)
 bsr fade_cancelled
 tst.l d0
 bne fade_in_aborted
 movem.l (sp)+,d0/a0
 move.l 16(a5),a0
 bra.w $37b4
fade_in_aborted:
 movem.l (sp)+,d0/a0
 bra.w $37c8
fade_cancelled:
 lea paused(pc),a0
 moveq #1,d0
 tst.l (a0)
 bne fade_checked
 move.l 4(a0),d0
 cmp.l 8(a0),d0
 sne d0
 and.l #1,d0
fade_checked:
 rts
cancelled:
 movem.l d1/a0,-(sp)
 moveq #1,d0
 lea paused(pc),a0
 tst.l (a0)
 bne cancelled_done
 move.l -60(a5),a0
 cmpi.l #1,4(a0) ; native QUIT also cancels in-flight work
 beq cancelled_done
 move.l 22(a0),d1
 cmp.l -28(a5),d1
 bne cancelled_done
 moveq #0,d0
cancelled_done:
 movem.l (sp)+,d1/a0
 rts
abort_image:
 ; Every gate arrives with all registers saved and no native arguments pending.
 ; Finish existing blits before freeing an opened IFF, then discard staging.
 move.l -52(a4),a6
 jsr -228(a6)
 move.l -4(a5),a0
 bsr close_iff
 move.l -32(a5),a0
 bsr close_iff
 lea COMPOSITE_STATE(pc),a0
 tst.l 12(a0)
 beq bitmap_restored
 move.l 4(a0),a1
 move.l 8(a0),4(a1)
bitmap_restored:
 clr.l 12(a0) ; active staging
 clr.l 16(a0) ; cached QR must not reference an abandoned frame
 clr.l 20(a0) ; suppress its delayed palette fade
 clr.l 24(a0)
 clr.l 28(a0)
 clr.l 48(a0) ; bitmap-caption state
 move.l -76(a5),a0
 move.l a0,d0
 beq previous_cleared
 clr.w -2(a0) ; native E string length
 clr.b (a0) ; force a real reload if navigation returns to the same entry
previous_cleared:
 movem.l (sp)+,d0-d7/a0-a6
 moveq #0,d0
 move.l -60(a5),a0
 bra.w $45e2 ; native busy reset, one-tick yield and quit/continue check
close_iff:
 move.l a0,d0
 beq close_done
 move.l (a0),a1
 move.l 16(a1),a1
 jsr (a1)
close_done:
 rts
 cnop 0,4
paused: dcb.l 3,0
 endif
 cnop 0,4
 dc.b 'AVSCANC1'
 dc.l PATCH_BASE
