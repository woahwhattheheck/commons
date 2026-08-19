# Star Office UI — copied source

Primary copy FROM https://github.com/ringhyacinth/Star-Office-UI
(code/logic MIT, Copyright 2026 Ring Hyacinth & Simon Lee). LICENSE sits next to this file.

What was copied:

- `characters/guest_role_1.png` … `guest_role_6.png`
  from `frontend/guest_role_N.png` (128×64, 32×32 frames, 4×2 walk).
- Work-state map from `frontend/index.html`:
  `idle` / `writing` / `researching` / `executing` / `syncing` / `error`
  plus area routing (idle → breakroom, writing/executing/syncing → writing, researching → researching).
- Phaser was **not** vendored. Their `frontend/vendor/phaser-3.80.1.min.js` is 1.1MB.
  Commons draws the same sheets with canvas `drawImage` (frame size from their load.spritesheet hints).

Guest characters are LimeZu Animated Mini Characters 2 (free):
https://limezu.itch.io/animated-mini-characters-2-platform-free

Art in that repo is **non-commercial / demonstration only**. Commons uses it as a public demo of the board, not a product. Do not sell these frames.

# Click-to-dialogue

Copied FROM https://github.com/clintonshane84/point-and-click-adventure-game-builder
`src/game-runtime/GameRuntime.ts`: canvas click → `getObjectAt` → `trigger === 'click'` → `show_dialog` sets `dialogText`. Second click clears. No Phaser.

Cite iq4fh8. Do not remint it.
