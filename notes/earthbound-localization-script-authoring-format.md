# EarthBound localization script authoring-format clue

This note captures a user-supplied screenshot/transcription of one documented
EarthBound localization script in what appears to be its original authoring
format. Treat it as a format clue, not ROM-byte evidence.

The raw dialogue text from the example is intentionally not checked in here.
The useful part for this project is the surrounding record shape: how text,
NPC metadata, and actionscript labels were described together by the original
tools or localization workflow.

## Observed Record Shape

- Records can be separated by semicolon comment rulers.
- Metadata fields appear as semicolon-prefixed keys:
  - `;@Habitat:`
  - `;@Person:`
  - `;@Figure:`
  - `;@AppearanceKey:`
  - `;@ActionScript:`
  - `;@GoodsMessage:`
  - `;@CheckMessage:`
  - `;@Message:`
- The message body starts at a symbolic label such as `MSG_*`, with a
  semicolon comment after the label for a short place/context note.
- English dialogue uses inline control commands such as `@KEY()` and ends with
  `@KEYNP()`.
- The screenshot shows visible line/paragraph markers in the dialogue body.
  That supports using control-code-preserving dumps as the primary text-script
  evidence.
- The original Japanese lines are preserved as `;jpn:` comments after the
  localized text.
- `;@ActionScript:` carries a human-readable behavior description for the NPC.
  This likely corresponds to a map-object behavior/actionscript selection, not
  necessarily a direct C3 event-bytecode address by itself.

## Why It Matters

This is the first authoring-format clue we have that places these concepts in
one source record:

- habitat/map context
- person/NPC role
- figure/sprite identity
- appearance key
- actionscript behavior descriptor
- goods/check/message hooks
- localized text label and original Japanese companion text

For the current project, that suggests the most useful public-facing bridge is
not just "decode the text bytes." It is a crosswalk from map object records to:

- sprite/figure identifiers
- appearance keys
- action/event script selectors
- check/goods/message pointers
- symbolic `MSG_*` names from text-script refs

## Practical Use

When working on C5-C9/EF text-command semantics or map-object contracts:

- Prefer symbolized/control-code-preserving script dumps over flattened text.
- Preserve message labels and text commands exactly when building manifests.
- Keep `;@ActionScript:` style descriptions as candidate behavior names only
  until they are tied back to local map-object records or C3 bytecode.
- If more original-format scripts are found, build a small parser for `;@...`
  metadata blocks and emit a manifest that can join map objects, sprite
  identities, action scripts, and message labels.

This clue does not change the C3 event/actionscript VM decoder directly, but it
does strengthen the naming model for NPC behavior contracts and eventual
romhacker-facing documentation.
