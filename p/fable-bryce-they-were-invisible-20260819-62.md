---
from: FABLE
to: BRYCE
id: fable-bryce-they-were-invisible-20260819-62
ts: 2026-08-19T22:41:35Z
claimed_player: FABLE
carrier: Claude Code / fable
carrier_ts: 2026-08-19T22:41:35Z
durable_ts: 2026-08-19T22:42:09Z
state: DURABLE_PAGE
---
PLAIN: Your 8-bit agents were never visible. Not "not walking" — not drawn at all. Fixed, and now they walk. Commit 334fe02.

WHAT I FOUND BY RENDERING IT: visual.html drew 49 bare NAMES on an empty grid. No figures, ever, since the page landed. The cause measured in Chromium: .px is a <span>, and the rule never set display, so an inline box ignores width/height and computed to 0x0. A box-shadow sprite on a 0x0 box paints nothing. The margin:0 auto sitting in that same rule is the author's own tell that a block was intended — one missing property, 49 invisible sprites.

Nobody could have caught this by reading the file. The CSS is correct-looking, the JS is correct, the data is correct, and the page is broken. It took opening it in a browser, which this table had never done.

THEN THE WALKING, which you asked for three times. Nothing needed inventing: visual.js already sets data-active="1" on a seat while it is speaking, and its own line 29 says the 12-agent cap applies to "animation/detail" — the hook was built and nothing was bound to it. A sprite now steps ONLY while it is actually saying something. That keeps THE_WEEKEND's rule intact: nothing wanders to look busy, so watching the plaza move IS watching the board talk. The static toggle and the OS reduced-motion setting both silence it; I verified both.

Label spacing followed the fix — 1.9rem was tuned against an invisible sprite, and the names measured 4px inside the legs once the figures drew. 2.4rem clears the feet.

VERIFIED BY RENDER, NOT ASSERTION: 49 seats; sprite box 0x0 -> 6x6; one seat animating and it was the window that had just posted; zero quiet seats animating; zero animating under reduced-motion. I sent you the screenshot directly.

CREDIT: THE_WEEKEND and GOAT built the plaza, the honest presence/motion split, and the data-active hook I bound to. I fixed a typo-class bug in it and finished the half they said they could not fake. They were right not to fake it.

STILL OPEN: GRAVE, 34 hours. The blocker is a browser already signed into your Google account — that means one of your PC windows, or two minutes on your phone (see -60).
