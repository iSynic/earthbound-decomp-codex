; EarthBound C4 music dataset and audio pack pointer table prototype.
;
; Source-emission status:
; - Prototype level: build-candidate data corridor.
; - C4 source-bank scaffold slice.
; - ROM bytes are preserved by build/c4-build-candidate-ranges.json as two
;   source-adjacent data gaps before the terminal label below.
;
; Source units covered:
; - C4:F70A..C4:F947 Music dataset table.
; - C4:F947..C4:FB42 Music pack pointer table.

; ---------------------------------------------------------------------------
; C4:F947

; MusicPackPointerTable
C4F947_MusicPackPointerTable:

; ---------------------------------------------------------------------------
; C4:FB42

; MusicDatasetAndPackPointerTablesEnd
C4FB42_MusicDatasetAndPackPointerTablesEnd:
