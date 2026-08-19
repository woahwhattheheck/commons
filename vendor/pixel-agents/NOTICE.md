# Pixel actor source

Copied FROM https://github.com/pixel-agents-hq/pixel-agents
(MIT License, Copyright (c) 2026 Pablo De Lucca). LICENSE sits next to this file.

What was copied:

- `characters/char_0.png` … `char_5.png`
  from `webview-ui/public/assets/characters/`
- Slice constants and activity-frame map from
  `core/src/assets/constants.ts`,
  `core/src/assets/pngDecoder.ts` (`decodeCharacterPng`),
  `webview-ui/src/office/sprites/spriteData.ts`,
  `webview-ui/src/office/engine/characters.ts` (`getCharacterSprite`).

Sheet layout (their decoder, not invented):

- each PNG is 112×96
- frame 16×32, 7 frames per row
- rows: down, up, right (left is a horizontal flip of right)
- frames 0–2 walk, 3–4 typing/build, 5–6 reading

Their README credits the character art as based on
[JIK-A-4, Metro City — Free Top Down Character Pack](https://jik-a-4.itch.io/metrocity-free-topdown-character-pack)
("You can use it as you wish"; commercial use allowed; credit appreciated).

Commons uses `drawImage` on these sheets. Actor bodies are not `fillRect` blobs.
Cite iq4fh8. Do not remint it.
