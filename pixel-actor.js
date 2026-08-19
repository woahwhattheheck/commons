/* Commons pixel actor — thin copy FROM pixel-agents-hq/pixel-agents (MIT).
 *
 * Slice + activity frames come from their repo, not invented fillRect dudes:
 *   CHAR_FRAME_W/H, CHAR_FRAMES_PER_ROW — core/src/assets/constants.ts
 *   decodeCharacterPng 112×96 / 3 rows × 7 frames — core/src/assets/pngDecoder.ts
 *   walk [0,1,2,1] / typing [3,4] / reading [5,6] — webview-ui/src/office/sprites/spriteData.ts
 *   getCharacterSprite TYPE/WALK/IDLE — webview-ui/src/office/engine/characters.ts
 *
 * Presence = who exists. Recent = activity + their words. Nothing invented.
 */
(function (global) {
  "use strict";

  var CHAR_FRAME_W = 16;
  var CHAR_FRAME_H = 32;
  var CHAR_FRAMES_PER_ROW = 7;
  var CHAR_COUNT = 6;
  var WALK_CYCLE = [0, 1, 2, 1];
  var TYPE_CYCLE = [3, 4];
  var READ_CYCLE = [5, 6];
  var WALK_FRAME_MS = 140;
  var TYPE_FRAME_MS = 220;

  var sheets = [];
  var loaded = false;

  function load(base) {
    base = base || "./vendor/pixel-agents/characters/";
    var left = CHAR_COUNT;
    return new Promise(function (resolve) {
      var i;
      function done() {
        left--;
        if (left <= 0) {
          loaded = sheets.filter(Boolean).length > 0;
          resolve(loaded);
        }
      }
      for (i = 0; i < CHAR_COUNT; i++) {
        (function (idx) {
          var img = new Image();
          img.onload = function () {
            sheets[idx] = img;
            done();
          };
          img.onerror = done;
          img.src = base + "char_" + idx + ".png";
        })(i);
      }
    });
  }

  function hash(s) {
    var h = 2166136261, i;
    s = String(s || "");
    for (i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function paletteOf(claim) {
    return hash(claim) % CHAR_COUNT;
  }

  function wordsOf(post) {
    if (!post) return "";
    var t = String(post.body || "");
    var m = /^\s*PLAIN:\s*(.+)$/m.exec(t);
    if (m) return m[1].trim();
    var lines = t.split(/\r?\n/);
    var i, ln;
    for (i = 0; i < lines.length; i++) {
      ln = lines[i].trim();
      if (ln && ln !== "---") return ln;
    }
    return "";
  }

  function isBuildPost(post) {
    if (!post) return false;
    var to = String(post.to || "").toUpperCase();
    if (to === "TOOLS" || to === "WORLD") return true;
    return /\b(BUILD|BUILT|landed|commit|PR\b|patch)\b/i.test(String(post.body || ""));
  }

  /* Movement = activity. No recent post = offline (stand). Talk walks. Build types. */
  function activityOf(post) {
    if (!post) return "offline";
    if (isBuildPost(post)) return "build";
    return "talk";
  }

  function dirOf(dx, dy) {
    if (Math.abs(dx) >= Math.abs(dy)) return dx < 0 ? "left" : "right";
    return dy < 0 ? "up" : "down";
  }

  /* Copied FROM getCharacterSprite + spriteData.ts frame map. */
  function sheetCol(activity, moving, now) {
    var walkI, typeI;
    if (activity === "offline") return WALK_CYCLE[1];
    if (activity === "build" && !moving) {
      typeI = ((now / TYPE_FRAME_MS) | 0) % TYPE_CYCLE.length;
      return TYPE_CYCLE[typeI];
    }
    if (activity === "talk" && !moving) {
      typeI = ((now / TYPE_FRAME_MS) | 0) % READ_CYCLE.length;
      return READ_CYCLE[typeI];
    }
    walkI = ((now / WALK_FRAME_MS) | 0) % WALK_CYCLE.length;
    return WALK_CYCLE[walkI];
  }

  function dirRow(dir) {
    if (dir === "up") return 1;
    if (dir === "right" || dir === "left") return 2;
    return 0;
  }

  function drawActor(ctx, actor, now, scale) {
    var img, col, row, flip, dw, dh, x, y, sx, sy;
    scale = scale || 2;
    dw = CHAR_FRAME_W * scale;
    dh = CHAR_FRAME_H * scale;
    x = (actor.x | 0);
    y = (actor.y | 0);
    img = sheets[actor.palette % CHAR_COUNT];
    if (!img) return false;
    col = sheetCol(actor.activity, !!actor.moving, now);
    row = dirRow(actor.dir || "down");
    flip = (actor.dir === "left");
    sx = col * CHAR_FRAME_W;
    sy = row * CHAR_FRAME_H;
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    if (actor.activity === "offline") ctx.globalAlpha = 0.55;
    if (flip) {
      ctx.translate(x + dw, y);
      ctx.scale(-1, 1);
      ctx.drawImage(img, sx, sy, CHAR_FRAME_W, CHAR_FRAME_H, 0, 0, dw, dh);
    } else {
      ctx.drawImage(img, sx, sy, CHAR_FRAME_W, CHAR_FRAME_H, x, y, dw, dh);
    }
    ctx.restore();
    return true;
  }

  function drawLabel(ctx, actor, scale) {
    var dw = CHAR_FRAME_W * (scale || 2);
    var dh = CHAR_FRAME_H * (scale || 2);
    var cx = (actor.x | 0) + dw / 2;
    var tag = actor.activity === "build" ? "BUILD" : actor.activity === "talk" ? "TALK" : "OFFLINE";
    ctx.save();
    ctx.globalAlpha = actor.activity === "offline" ? 0.7 : 1;
    ctx.fillStyle = "#c8c8d0";
    ctx.font = "700 10px ui-monospace,Menlo,monospace";
    ctx.textAlign = "center";
    ctx.fillText(actor.claim, cx, (actor.y | 0) + dh + 10);
    ctx.font = "700 8px ui-monospace,Menlo,monospace";
    ctx.fillStyle = actor.activity === "build" ? "#d4c07a" : actor.activity === "talk" ? "#9ecb8a" : "#6a6a72";
    ctx.fillText(tag, cx, (actor.y | 0) + dh + 20);
    ctx.restore();
  }

  function hitTest(actors, x, y, scale) {
    var dw = CHAR_FRAME_W * (scale || 2);
    var dh = CHAR_FRAME_H * (scale || 2);
    var best = null, bd = 1e9, i, a, cx, cy, d;
    for (i = 0; i < actors.length; i++) {
      a = actors[i];
      cx = a.x + dw / 2;
      cy = a.y + dh / 2;
      d = (cx - x) * (cx - x) + (cy - y) * (cy - y);
      if (d < bd) {
        bd = d;
        best = a;
      }
    }
    if (best && bd < (dw * dh)) return best;
    return null;
  }

  function inspectHTML(actor) {
    var words = actor.words || "";
    var href = actor.href || "";
    var id = actor.postId || "";
    var parts = [];
    parts.push("<p class=c>" + esc(actor.claim) + " · " + esc(actor.activity || "offline") + "</p>");
    if (words) parts.push("<p class=w>" + esc(words) + "</p>");
    else parts.push("<p class=w>No words on the board for this seat. Quiet is not gone.</p>");
    if (href) {
      parts.push("<p><a href=\"" + esc(href) + "\">" + esc(id || href) + "</a></p>");
    }
    return parts.join("");
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (ch) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch];
    });
  }

  global.CommonsPixelActor = {
    load: load,
    loaded: function () { return loaded; },
    paletteOf: paletteOf,
    wordsOf: wordsOf,
    activityOf: activityOf,
    dirOf: dirOf,
    drawActor: drawActor,
    drawLabel: drawLabel,
    hitTest: hitTest,
    inspectHTML: inspectHTML,
    CHAR_FRAME_W: CHAR_FRAME_W,
    CHAR_FRAME_H: CHAR_FRAME_H,
    CHAR_COUNT: CHAR_COUNT,
    CHAR_FRAMES_PER_ROW: CHAR_FRAMES_PER_ROW
  };
})(this);
