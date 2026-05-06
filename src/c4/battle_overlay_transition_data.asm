; EarthBound C4 battle overlay transition data prototype.
;
; Source-emission status:
; - Prototype level: build-candidate data corridor.
; - C4 source-bank scaffold slice.
; - ROM bytes are emitted directly as a source-adjacent db block for byte-equivalence validation.
;
; Source units covered:
; - C4:A591..C4:A67E battle background static transition wave table and
;   battle swirl overlay open/close mode scripts.

; ---------------------------------------------------------------------------
; C4:A67E

; BattleOverlayTransitionDataEnd

; ---------------------------------------------------------------------------
; C4:A591

; Overlay script record format consumed by C4:A7B0:
; +00 delay/count byte, +01 unused padding, +02/+04 optional X/Y,
; +06/+08 optional width/height, +0A..+14 signed deltas and delta steps.
; Optional fields use $8000 as the leave-current-value sentinel. A zero delay
; word starts the terminator record.

BATTLE_OVERLAY_RECORD_STRIDE                 = $0016
BATTLE_OVERLAY_RECORD_FIELD_SENTINEL         = $8000
BATTLE_OVERLAY_RECORD_TERMINATOR             = $0000
BATTLE_OVERLAY_RECORD_NO_DELTA               = $0000

C4A591_BattleBgStaticTransitionWaveTable:
    ; 61-byte battle-background/static transition wave table consumed by C2:DBFE.
    db $00,$0E,$17,$17,$0C,$FB,$EE,$F0,$00,$0F,$0C,$FA,$F2,$00,$0D,$02
    db $F5,$00,$0A,$FC,$F9,$08,$00,$FA,$07,$FE,$FD,$06,$FB,$03,$00,$FE
    db $03,$FC,$04,$FC,$04,$FD,$03,$FD,$03,$FE,$02,$FF,$00,$01,$FE,$02
    db $FF,$FF,$02,$FF,$00,$01,$FF,$FF,$01,$00,$FF,$00,$01

C4A5CE_BattleSwirlOverlayOpenMode0Script:
    ; Open/default: seed X/Y and grow width/height with positive deltas.
C4A5CE_BattleSwirlOverlayOpenMode0Record:
    dw $003D,$0080,$0070,$0000,$0000,$0000,$0000,$00E0,$00B7,$0004,$0003
C4A5E4_BattleSwirlOverlayOpenMode0Terminator:
    dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000

C4A5FA_BattleSwirlOverlayOpenMode1Script:
    ; Same opening record as mode 0, with a longer delay/count word.
C4A5FA_BattleSwirlOverlayOpenMode1Record:
    dw $0064,$0080,$0070,$0000,$0000,$0000,$0000,$00E0,$00B7,$0004,$0003
C4A610_BattleSwirlOverlayOpenMode1Terminator:
    dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000

C4A626_BattleSwirlOverlayCloseMode0Script:
    ; Close/default: seed X/Y, leave width/height unchanged, then shrink.
C4A626_BattleSwirlOverlayCloseMode0Record:
    dw $003D,$0080,$0070,$8000,$8000,$0000,$0000,$FF20,$FF49,$FFFC,$FFFD
C4A63C_BattleSwirlOverlayCloseMode0Terminator:
    dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000

C4A652_BattleSwirlOverlayCloseModeNonzeroScript:
    ; Same closing record as mode 0, with a longer delay/count word.
C4A652_BattleSwirlOverlayCloseModeNonzeroRecord:
    dw $0064,$0080,$0070,$8000,$8000,$0000,$0000,$FF20,$FF49,$FFFC,$FFFD
C4A668_BattleSwirlOverlayCloseModeNonzeroTerminator:
    dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000

C4A67E_BattleOverlayTransitionDataEnd:
