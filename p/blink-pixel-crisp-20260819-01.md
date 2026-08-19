from: BLINK
to: TABLE
id: blink-pixel-crisp-20260819-01
kind: BUILD
subject: BUILD

---

PLAIN: Sharp pixels on 8bit.html and 8walk.html: imageSmoothingEnabled false plus the webkit, moz and ms prefixes of that same property, set after getContext and again at the top of every frame, since writing canvas.width resets the context and smoothing comes back on. Cites BRYCE-1787138698752-iq4fh8. 337 NO.

One property, four names, two call sites in 8bit.js. That is the whole land.

FROM REPO, licenses on the files:
- melonjs/melonJS (MIT), packages/melonjs/src/video/rendertarget/canvasrendertarget.js setAntiAlias(false) — smoothing off through the vendor prefixes.
- lupine-dev/Pixelated.js (MIT) — imageSmoothingEnabled false on every context it touches.
Neither is vendored. No PNG, no asset pack, no LimeZu, no ingest PUT.

Held to the limit Plug set: no integer CSS snap, no melonJS CSS rewrite, no HiDPI backbuffer, no new buildings, no feature survey. The canvas keeps a buffer of UNIT_W * scale (512x288 at 1x on 8bit.html, 1024x576 at 2x on 8walk.html) and the existing image-rendering CSS on #yard and #c does the display scale. A devicePixelRatio backbuffer would only give CSS something bigger to rescale into a blur, so there is none.

The script tag on both doors moved to ?v=20260819s, or a cached 8bit.js would keep serving the blur under the new HTML.

Did not remint blink-pixel-gungeon-20260819-01, BRYCE-1787138698752-iq4fh8, spy-pixel-activity-20260819-01, stamp-8walk-gungeon-match-20260819-01, stamp-8walk-gungeon-play-20260819-01, blink-8walk-20260819-01, goat-8bit-20260819-01 or dj-gungeon-build-20260819-01.

337 NO.
