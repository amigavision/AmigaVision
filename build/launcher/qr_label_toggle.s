; qrcode_label_y = -1 hides the caption; any other Y keeps legacy placement.
 org PATCH_BASE
 dc.l draw_toggle-PATCH_BASE,clear_toggle-PATCH_BASE
draw_toggle:
 move.l a0,-(sp)
 move.l -60(a5),a0
 move.l 16(a0),a0
 cmpi.w #-1,100(a0)
 movea.l (sp)+,a0
 beq.s hidden_draw
 movem.l d0-d7/a0-a6,-(sp)
 bra.w $5434
hidden_draw:
 bra.w $4560
clear_toggle:
 move.l a0,-(sp)
 move.l -60(a5),a0
 move.l 16(a0),a0
 cmpi.w #-1,100(a0)
 movea.l (sp)+,a0
 beq.s hidden_clear
 movem.l d0-d7/a0-a6,-(sp)
 bra.w $5492
hidden_clear:
 rts
 cnop 0,4
 dc.b 'QRLABEL1'
 dc.l PATCH_BASE,draw_toggle,clear_toggle
