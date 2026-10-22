; Motorola 68000 wrappers. Patch addresses are runtime addresses (file offset - 32).
 org PATCH_BASE
 dc.l parse_type-PATCH_BASE,redraw_gate-PATCH_BASE,char_match-PATCH_BASE,select_guard-PATCH_BASE,favorites_guard-PATCH_BASE,display_text-PATCH_BASE,buffered_redraw-PATCH_BASE,buffer_cleanup-PATCH_BASE,fast_template-PATCH_BASE,direct_nav-PATCH_BASE
parse_type:
 movem.l d0-d1/a0-a1,-(sp)
 move.l -76(a5),a0
 moveq #0,d1
 cmp.b #83,(a0)
 bne not_separator
 moveq #4,d1
not_separator:
 cmp.b #86,(a0)
 bne type_ready
 moveq #3,d1
type_ready:
 tst.l d1
 beq parsed
 move.l -24(a5),a0
 move.l 16(a0),d0
 subq.l #1,d0
 lsl.l #2,d0
 move.l 20(a0),a0
 move.l (a0,d0.l),a0
 move.l d1,8(a0)
parsed:
 ; A rows contain a literal directory name, TAB, then its display label.
 ; Split only the owned name copy; path operations keep the real filename.
 ; a0 may point to an item after S/V handling; use the input line again.
 move.l -76(a5),a0
 cmp.b #65,(a0)
 bne parse_done
 move.l -24(a5),a0
 move.l 16(a0),d0
 subq.l #1,d0
 lsl.l #2,d0
 move.l 20(a0),a0
 move.l (a0,d0.l),a0
 move.l (a0),a1
 moveq #0,d0
alias_scan:
 tst.b (a1,d0.l)
 beq parse_done
 cmp.b #9,(a1,d0.l)
 beq alias_found
 addq.l #1,d0
 bra alias_scan
alias_found:
 clr.b (a1,d0.l)
 move.w d0,-2(a1)
 addq.l #1,d0
 move.l d0,d1
 swap d1
alias_length:
 tst.b (a1,d0.l)
 beq alias_ready
 addq.l #1,d0
 bra alias_length
alias_ready:
 sub.w d1,d1
 move.w d0,d1
 moveq #0,d0
 move.w -2(a1),d0
 addq.l #1,d0
 sub.w d0,d1
 move.l d1,4(a0)
parse_done:
 movem.l (sp)+,d0-d1/a0-a1
 lea parse_type(pc),a0
 adda.l #$25e0-parse_type,a0
 jmp (a0)

; Normalize selection before every redraw, including initial/restored positions.
; Extend partial redraws across skipped rows; repaint the full list only on scroll.
redraw_gate:
 movem.l d0-d7/a0-a6,-(sp)
 move.l a0,a2
 move.l 8(a2),a3
 move.l 20(a3),a4
 lea previous(pc),a6
 moveq #0,d0
 move.w 42(a2),d0
 moveq #0,d1
 move.w 36(a2),d1
 add.l d1,d0
 move.l d0,d5
 move.l 16(a3),d7
 beq normalize_done
 subq.l #1,d7
 tst.l d0
 bpl index_nonnegative
 moveq #0,d0
index_nonnegative:
 cmp.l d7,d0
 ble index_in_range
 move.l d7,d0
index_in_range:
 ; Hash the directory path: the navigator reuses its string buffer.
 move.l 8(a3),a0
 moveq #0,d6
path_hash:
 moveq #0,d1
 move.b (a0)+,d1
 beq hash_done
 rol.l #5,d6
 eor.l d1,d6
 bra path_hash
hash_done:
 moveq #1,d4
 cmpa.l (a6),a2
 bne choose_done
 cmpa.l 4(a6),a4
 bne choose_done
 cmp.l 8(a6),d6
 bne choose_done
 cmp.l 12(a6),d0
 bge choose_done
 moveq #-1,d4
choose_done:
 move.l d0,d2
 moveq #0,d3
find_selectable:
 bsr is_empty
 bne found_selectable
 add.l d4,d0
 tst.l d0
 bmi reverse_search
 cmp.l d7,d0
 ble find_selectable
reverse_search:
 tst.l d3
 bne no_selectable
 moveq #1,d3
 neg.l d4
 move.l d2,d0
 bra find_selectable
no_selectable:
 move.l d2,d0
found_selectable:
 moveq #0,d4
 move.w 42(a2),d4
 move.l a2,(a6)
 move.l a4,4(a6)
 move.l d6,8(a6)
 move.l d0,12(a6)
 moveq #0,d1
 move.w 42(a2),d1
 cmp.l d1,d0
 blt scroll_to_index
 moveq #0,d2
 move.w 38(a2),d2
 add.l d1,d2
 cmp.l d2,d0
 blt set_position
 moveq #0,d1
 move.w 38(a2),d1
 neg.l d1
 add.l d0,d1
 addq.l #1,d1
 bra set_offset
scroll_to_index:
 move.l d0,d1
set_offset:
 move.w d1,42(a2)
set_position:
 sub.l d1,d0
 move.w d0,36(a2)
 add.l d1,d0
 cmp.l d4,d1
 bne full_redraw
 cmp.l d5,d0
 beq normalize_done
 cmp.l #-1,64(sp)
 beq normalize_done
 ; The caller already included the old selection. Extend its dirty range to
 ; include the actual destination instead of repainting the whole viewport.
 moveq #0,d2
 move.w 36(a2),d2
 cmp.l 68(sp),d2
 bge check_redraw_end
 move.l d2,68(sp)
check_redraw_end:
 cmp.l 64(sp),d2
 ble normalize_done
 move.l d2,64(sp)
 bra normalize_done
full_redraw:
 move.l #-1,64(sp)
 clr.l 68(sp)
normalize_done:
 movem.l (sp)+,d0-d7/a0-a6
 bra buffered_redraw
is_empty:
 move.l d0,d1
 lsl.l #2,d1
 move.l (a4,d1.l),a0
 cmp.l #4,8(a0)
 rts

; Letter shortcuts must continue searching past separator labels.
char_match:
 movem.l d0-d1/a0,-(sp)
 move.l d7,a0
 cmp.l #4,8(a0)
 beq char_skip
 move.l 4(a0),d1
 swap d1
 and.l #$ffff,d1
 beq char_compare
 move.l (a0),a0
 adda.l d1,a0
 moveq #0,d0
label_shortcut:
 move.b (a0)+,d0
 cmp.b #32,d0
 beq label_shortcut
 and.b #$df,d0
char_compare:
 cmp.l 16(a5),d0
 movem.l (sp)+,d0-d1/a0
 rts
char_skip:
 tst.l d7
 movem.l (sp)+,d0-d1/a0
 rts

; Graphics Text receives the packed label offset/length only for A rows.
display_text:
 move.l d1,-(sp)
 move.l d0,d1
 swap d1
 and.l #$ffff,d1
 beq native_text
 adda.l d1,a0
 and.l #$ffff,d0
native_text:
 move.l (sp)+,d1
 jmp -60(a6)

; Do not highlight a non-actionable row in a divider-only menu.
select_guard:
 movem.l d0-d1/a0,-(sp)
 move.l 28(sp),a0
 moveq #0,d0
 move.w 36(a0),d0
 moveq #0,d1
 move.w 42(a0),d1
 add.l d1,d0
 move.l 8(a0),a0
 move.l 20(a0),a0
 lsl.l #2,d0
 move.l (a0,d0.l),a0
 cmp.l #4,8(a0)
 beq no_highlight
 movem.l (sp)+,d0-d1/a0
 ifd ORIGINAL_SELECT
 bra.w ORIGINAL_SELECT
 else
 jmp -606(a6)
 endif
no_highlight:
 movem.l (sp)+,d0-d1/a0
 rts
favorites_guard:
 ; Preserve automatic Favorites for legacy caches; explicit V rows take priority.
 movem.l d1-d2/a0-a2,-(sp)
 jsr (a1)
 tst.l d0
 beq favorites_done
 move.l -24(a5),a0
 move.l 16(a0),d1
 move.l 20(a0),a0
 subq.l #1,d1
 bmi favorites_done
favorites_scan:
 move.l (a0)+,a2
 cmp.l #3,8(a2)
 beq explicit_favorites
 dbra d1,favorites_scan
 bra favorites_done
explicit_favorites:
 moveq #0,d0
favorites_done:
 movem.l (sp)+,d1-d2/a0-a2
 tst.l d0
 rts
; Compose into a persistent Chip RAM bitmap. Only the completed viewport is
; copied to the displayed RastPort, so background restoration is never visible.
buffered_redraw:
 ifd DIRECT_NAV
 bra native_redraw
 endif
 movem.l d0-d7/a0-a6,-(sp)
 move.l a0,a2
 lea buffer_gfx(pc),a0
 move.l -52(a4),(a0)
 move.l 16(a2),a3
 move.l 4(a3),a4
 move.l buffer_pixels(pc),d0
 bne buffer_ready
 moveq #0,d5
 move.w (a4),d5
 moveq #0,d0
 move.w 2(a4),d0
 mulu.w d0,d5
 moveq #0,d6
 move.b 5(a4),d6
 beq buffer_fallback
 cmp.w #8,d6
 bhi buffer_fallback
 move.l d5,d0
 mulu.w d6,d0
 beq buffer_fallback
 lea buffer_size(pc),a0
 move.l d0,(a0)
 move.l #$10002,d1
 move.l 4.w,a6
 jsr -198(a6)
 tst.l d0
 beq buffer_fallback
 lea buffer_pixels(pc),a0
 move.l d0,(a0)
 lea buffer_seed(pc),a0
 move.b #1,(a0)
 lea buffer_bitmap(pc),a0
 move.l (a4),(a0)
 move.l 4(a4),4(a0)
 move.b #8,4(a0)
 move.l d0,a1
 moveq #0,d4
buffer_planes:
 move.l d4,d0
 lsl.l #2,d0
 move.l a1,8(a0,d0.l)
 adda.l d5,a1
 addq.w #1,d4
 cmp.w d6,d4
 blt buffer_planes
buffer_ready:
 ; Clone pens/font/layer state, then detach the off-screen port from layers.
 lea buffer_rport(pc),a1
 move.l a3,a0
 moveq #24,d0
buffer_clone:
 move.l (a0)+,(a1)+
 dbra d0,buffer_clone
 lea buffer_rport(pc),a1
 clr.l (a1)
 lea buffer_bitmap(pc),a0
 move.l a0,4(a1)
 ; Seed once, including the case where the first call is a partial redraw.
 ; Thereafter the reusable buffer already contains the last complete view.
 lea buffer_seed(pc),a0
 tst.b (a0)
 beq buffer_seeded
 move.l 4(a3),a0
 moveq #0,d7
 bsr viewport_blit
 lea buffer_seed(pc),a0
 clr.b (a0)
buffer_seeded:
 ; Save only the dirty vertical span for the final copy. Full redraws still
 ; include unused rows, since the native renderer clears their background.
 lea buffer_first(pc),a0
 clr.l (a0)
 moveq #0,d0
 move.l 4(a2),a1
 move.w 34(a1),d0
 move.l 64(sp),d1
 cmp.l #-1,d1
 beq buffer_span_ready
 move.l 68(sp),d0
 move.l d0,(a0)
 sub.l d0,d1
 move.l d1,d0
 addq.l #1,d0
buffer_span_ready:
 lea buffer_rows(pc),a0
 move.l d0,(a0)
 lea buffer_rport(pc),a0
 move.l a0,16(a2)
 ; Keep the native method's argument order and private stack layout intact.
 move.l a3,-(sp)
 move.l a2,-(sp)
 move.l 76(sp),-(sp)
 move.l 76(sp),-(sp)
 move.l a2,a0
 move.l 64(sp),a4
 bsr native_redraw
 addq.l #8,sp
 move.l (sp)+,a2
 move.l (sp)+,a3
 move.l a3,16(a2)
 ; Recover the caller's graphics library base from the saved registers.
 move.l 48(sp),a0
 move.l -52(a0),a6
 lea buffer_bitmap(pc),a0
 move.l a3,a1
 moveq #1,d7
 bsr viewport_blit
 jsr -228(a6)
 movem.l (sp)+,d0-d7/a0-a6
 rts
buffer_fallback:
 movem.l (sp)+,d0-d7/a0-a6
native_redraw:
 link a5,#0
 bra.w $6b1c

; a0=source bitmap, a1=destination RP, a2=self. Coordinates remain unchanged,
; so both the native renderer and the skin restore work with existing configs.
viewport_blit:
 movem.l d0-d7/a0-a6,-(sp)
 move.l 4(a2),a5
 moveq #0,d0
 move.w 28(a5),d0
 move.l d0,d2
 moveq #0,d1
 move.w 30(a5),d1
 move.l d1,d3
 moveq #0,d4
 move.w 32(a2),d4
 moveq #0,d5
 move.l 20(a2),a5
 move.w 20(a5),d5
 move.l 4(a2),a5
 add.w 26(a5),d5
 moveq #0,d6
 move.w 34(a5),d6
 tst.l d7
 beq buffer_full_span
 move.l buffer_first(pc),d6
 mulu.w d5,d6
 add.l d6,d1
 add.l d6,d3
 move.l buffer_rows(pc),d6
buffer_full_span:
 mulu.w d6,d5
 move.l #$c0,d6
 ; Use the graphics library captured before repurposing a4.
 move.l buffer_gfx(pc),a6
 jsr -606(a6)
 movem.l (sp)+,d0-d7/a0-a6
 rts

buffer_cleanup:
 movem.l d0-d7/a0-a6,-(sp)
 move.l buffer_pixels(pc),d0
 beq buffer_freed
 move.l -52(a4),a6
 jsr -228(a6)
 move.l buffer_pixels(pc),a1
 move.l buffer_size(pc),d0
 move.l 4.w,a6
 jsr -210(a6)
 lea buffer_pixels(pc),a0
 clr.l (a0)
buffer_freed:
 movem.l (sp)+,d0-d7/a0-a6
 ifd ORIGINAL_CLOSE
 bra.w ORIGINAL_CLOSE
 else
 jmp -66(a6)
 endif
; The skin overlay originally used BltTemplate/JAM1 for every viewport pixel.
; Use the original launcher's bitmap blitter path instead. Replicate the text
; plane in a descriptor, then OR set pen bits and clear unset pen bits. Zero
; source bits preserve the background, exactly like transparent template text.
fast_template:
 movem.l d0-d7/a0-a6,-(sp)
 move.l a1,a2
 lea template_bitmap(pc),a1
 move.w d1,(a1)
 move.w d5,2(a1)
 move.b #8,4(a1)
 move.l 4(a2),a0
 move.b 5(a0),5(a1)
 move.l 32(sp),a0
 moveq #7,d0
 lea 8(a1),a1
replicate_template:
 move.l a0,(a1)+
 dbra d0,replicate_template
 moveq #0,d7
 move.b 24(a2),d7
 move.l 24(sp),d6
 and.l d7,d6
 move.b d6,24(a2)
 beq clear_template_bits
 movem.l (sp),d0-d5
 moveq #0,d1
 lea template_bitmap(pc),a0
 move.l a2,a1
 move.l #$e0,d6
 jsr -606(a6)
clear_template_bits:
 move.l 24(sp),d6
 not.l d6
 and.l d7,d6
 move.b d6,24(a2)
 beq template_finished
 movem.l (sp),d0-d5
 moveq #0,d1
 lea template_bitmap(pc),a0
 move.l a2,a1
 moveq #$20,d6
 jsr -606(a6)
template_finished:
 move.b d7,24(a2)
 movem.l (sp)+,d0-d7/a0-a6
 rts
 cnop 0,4
template_bitmap: dcb.b 40,0

; Compose the text mask and captured skin directly into the display. There is
; no intermediate cleared state and no full-color staging/present blit. This
; also avoids serializing each scroll on the emulated chipset's blit timing.
; Viewport width is an integer number of words: (menu_width+2)*char_width=32*7
; in the shipped skin. Unsupported geometry retains the original overlay.
direct_nav:
 movem.l d0-d7/a0-a6,-(sp)
 move.l $a690(pc),d7
 beq direct_fallback
 tst.l d0
 bne direct_fallback
 move.l d4,d7
 and.l #15,d7
 bne direct_fallback
 tst.l d4
 beq direct_finished
 tst.l d5
 beq direct_finished
 jsr -228(a6)
 movem.l (sp),d0-d7/a0-a6
 lea direct_state(pc),a6
 move.w (a0),DS_SRCSTRIDE(a6)
 move.l d1,d7
 mulu.w (a0),d7
 add.l 8(a0),d7
 move.l d7,DS_SRC(a6)
 move.l 4(a1),a2
 move.l a2,DS_DSTBM(a6)
 move.w (a2),DS_DSTSTRIDE(a6)
 lea $a6bc(pc),a3
 move.l a3,DS_BGBM(a6)
 move.w (a3),DS_BGSTRIDE(a6)
 move.l d2,d7
 and.w #15,d7
 move.w d7,DS_SHIFT(a6)
 moveq #-1,d0
 lsr.w d7,d0
 move.w d0,DS_FIRSTMASK(a6)
 not.w d0
 move.w d0,DS_LASTMASK(a6)
 lsr.l #4,d2
 add.l d2,d2
 move.l d3,d0
 mulu.w (a2),d0
 add.l d2,d0
 move.l d0,DS_DSTOFF(a6)
 move.l d3,d0
 mulu.w (a3),d0
 add.l d2,d0
 move.l d0,DS_BGOFF(a6)
 lsr.l #4,d4
 move.w d4,DS_WORDS(a6)
 move.w d5,DS_ROWS(a6)
 moveq #0,d6
 move.b 5(a2),d6
 move.w d6,DS_DEPTH(a6)
 ; Planes that are entirely ones in the clean skin can never change when
 ; white text is added. Test once and omit these planes on later redraws.
 tst.w DS_INIT(a6)
 bne direct_scan_done
 clr.w DS_SKIP(a6)
 ; Selection text clears bit zero, so that plane must always be restored.
 moveq #1,d7
scan_skin_plane:
 move.l d7,d0
 lsl.l #2,d0
 move.l 8(a3,d0.l),a0
 moveq #0,d0
 move.w (a3),d0
 moveq #0,d1
 move.w 2(a3),d1
 mulu.w d1,d0
 lsr.l #2,d0
 subq.l #1,d0
skin_all_ones:
 cmp.l #-1,(a0)+
 bne skin_not_constant
 dbra d0,skin_all_ones
 moveq #1,d0
 lsl.w d7,d0
 or.w d0,DS_SKIP(a6)
skin_not_constant:
 addq.w #1,d7
 cmp.w d6,d7
 blt scan_skin_plane
 move.w #1,DS_INIT(a6)
direct_scan_done:
 moveq #0,d7
compose_plane:
 move.w DS_SKIP(a6),d0
 btst d7,d0
 bne next_compose_plane
 move.l d7,d0
 lsl.l #2,d0
 move.l DS_BGBM(a6),a3
 move.l 8(a3,d0.l),a4
 adda.l DS_BGOFF(a6),a4
 move.l DS_DSTBM(a6),a3
 move.l 8(a3,d0.l),a5
 adda.l DS_DSTOFF(a6),a5
 move.l DS_SRC(a6),a3
 move.w DS_ROWS(a6),d5
 subq.w #1,d5
 move.w DS_SHIFT(a6),d4
compose_row:
 move.l a3,a0
 move.l a4,a1
 move.l a5,a2
 ; First word may overlap the left frame: preserve pixels outside the view.
 moveq #0,d0
 move.w (a0),d0
 lsr.w d4,d0
 or.w (a1)+,d0
 move.w (a2),d1
 eor.w d1,d0
 and.w DS_FIRSTMASK(a6),d0
 eor.w d1,d0
 move.w d0,(a2)+
 move.w DS_WORDS(a6),d3
 subq.w #2,d3
 bmi compose_last
compose_words:
 move.l (a0),d0
 lsr.l d4,d0
 or.w (a1)+,d0
 move.w d0,(a2)+
 addq.l #2,a0
 dbra d3,compose_words
compose_last:
 tst.w d4
 beq compose_row_done
 move.w (a0),d0
 moveq #16,d1
 sub.w d4,d1
 lsl.w d1,d0
 or.w (a1),d0
 move.w (a2),d1
 eor.w d1,d0
 and.w DS_LASTMASK(a6),d0
 eor.w d1,d0
 move.w d0,(a2)
compose_row_done:
 adda.w DS_SRCSTRIDE(a6),a3
 adda.w DS_BGSTRIDE(a6),a4
 adda.w DS_DSTSTRIDE(a6),a5
 dbra d5,compose_row
next_compose_plane:
 addq.w #1,d7
 cmp.w DS_DEPTH(a6),d7
 blt compose_plane
direct_finished:
 movem.l (sp)+,d0-d7/a0-a6
 rts
direct_fallback:
 movem.l (sp)+,d0-d7/a0-a6
 bra.w $a480

DS_SRCSTRIDE equ 0
DS_SRC equ 4
DS_DSTBM equ 8
DS_DSTSTRIDE equ 12
DS_BGBM equ 16
DS_BGSTRIDE equ 20
DS_DSTOFF equ 24
DS_BGOFF equ 28
DS_SHIFT equ 32
DS_FIRSTMASK equ 34
DS_LASTMASK equ 36
DS_WORDS equ 38
DS_ROWS equ 40
DS_DEPTH equ 42
DS_INIT equ 44
DS_SKIP equ 46
 cnop 0,4
direct_state: dcb.b 48,0

 cnop 0,4
buffer_first: dc.l 0
buffer_rows: dc.l 0
buffer_seed: dc.w 0
 cnop 0,4
buffer_gfx: dc.l 0
buffer_pixels: dc.l 0
buffer_size: dc.l 0
buffer_bitmap: dcb.b 40,0
buffer_rport: dcb.b 100,0

 cnop 0,4
previous:
 dcb.l 4,0
 dc.b "AVSDIV10"
 dc.l PATCH_BASE,parse_type-PATCH_BASE,redraw_gate-PATCH_BASE,char_match-PATCH_BASE,select_guard-PATCH_BASE,favorites_guard-PATCH_BASE,display_text-PATCH_BASE,buffered_redraw-PATCH_BASE,buffer_cleanup-PATCH_BASE,fast_template-PATCH_BASE,direct_nav-PATCH_BASE
