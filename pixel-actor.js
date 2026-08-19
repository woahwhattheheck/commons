/* Commons pixel actor — copy FROM OSS, not invented fillRect dudes.
 *
 * 1. ringhyacinth/Star-Office-UI (closest match)
 *    guest_role_N 128×64 / 32×32 / 4×2 walk — frontend/guest_role_N.png
 *    work states idle/writing/researching/executing/syncing/error — frontend/index.html
 *    Phaser engine NOT vendored.
 *
 * 2. clintonshane84/point-and-click-adventure-game-builder
 *    GameRuntime.ts: click object → show_dialog (their words).
 *
 * 3. pixel-agents-hq/pixel-agents Metro City 16×32 sheets remain as fallback.
 *
 * Presence = who exists. Recent = activity + their words. Nothing invented.
 */
(function (global) {
  "use strict";

  var STAR_FRAME_W = 32;
  var STAR_FRAME_H = 32;
  var STAR_COLS = 4;
  var STAR_COUNT = 6;
  var METRO_FRAME_W = 16;
  var METRO_FRAME_H = 32;
  var METRO_COLS = 7;
  var METRO_WALK = [0, 1, 2, 1];
  var METRO_TYPE = [3, 4];
  var METRO_READ = [5, 6];
  var WALK_FRAME_MS = 140;
  var TYPE_FRAME_MS = 220;

  /* Copied FROM Star-Office-UI frontend/index.html state table. */
  var STAR_STATES = {
    idle: { name: "idle", area: "breakroom", tag: "OFFLINE" },
    writing: { name: "writing", area: "writing", tag: "BUILD" },
    researching: { name: "researching", area: "researching", tag: "TALK" },
    executing: { name: "executing", area: "writing", tag: "BUILD" },
    syncing: { name: "syncing", area: "writing", tag: "BUILD" },
    error: { name: "error", area: "error", tag: "OFFLINE" }
  };

  var sheets = [];
  var pack = "";
  var loaded = false;
  var dialog = null;

  function loadImages(base, prefix, count, ext) {
    var left = count;
    var out = [];
    return new Promise(function (resolve) {
      function done() {
        left--;
        if (left <= 0) resolve(out.filter(Boolean));
      }
      var i;
      for (i = 1; i <= count; i++) {
        (function (idx) {
          var img = new Image();
          img.onload = function () {
            out[idx - 1] = img;
            done();
          };
          img.onerror = done;
          img.src = base + prefix + idx + "." + ext;
        })(i);
      }
    });
  }

  function load(opts) {
    opts = opts || {};
    var starBase = (typeof opts === "string") ? "" : (opts.star || "./vendor/star-office-ui/characters/");
    var metroBase = (typeof opts === "string") ? opts : (opts.metro || "./vendor/pixel-agents/characters/");
    if (typeof opts === "string") starBase = "./vendor/star-office-ui/characters/";
    return loadImages(starBase, "guest_role_", STAR_COUNT, "png").then(function (star) {
      if (star.length) {
        sheets = star;
        pack = "star";
        loaded = true;
        return true;
      }
      return loadImages(metroBase, "char_", STAR_COUNT, "png").then(function (metro) {
        /* pixel-agents files are char_0..5 */
        return loadMetroZero(metroBase).then(function (m0) {
          sheets = m0.length ? m0 : metro;
          pack = sheets.length ? "metro" : "";
          loaded = sheets.length > 0;
          return loaded;
        });
      });
    });
  }

  function loadMetroZero(base) {
    var left = 6;
    var out = [];
    return new Promise(function (resolve) {
      function done() {
        left--;
        if (left <= 0) resolve(out.filter(Boolean));
      }
      var i;
      for (i = 0; i < 6; i++) {
        (function (idx) {
          var img = new Image();
          img.onload = function () {
            out[idx] = img;
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
    return hash(claim) % STAR_COUNT;
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

  /* Star-Office work state. Commons labels stay TALK / BUILD / OFFLINE. */
  function starStateOf(post) {
    if (!post) return "idle";
    if (isBuildPost(post)) return "writing";
    return "researching";
  }

  function activityOf(post) {
    var st = starStateOf(post);
    if (st === "writing" || st === "executing" || st === "syncing") return "build";
    if (st === "researching") return "talk";
    return "offline";
  }

  function dirOf(dx, dy) {
    if (Math.abs(dx) >= Math.abs(dy)) return dx < 0 ? "left" : "right";
    return dy < 0 ? "up" : "down";
  }

  function frameW() { return pack === "star" ? STAR_FRAME_W : METRO_FRAME_W; }
  function frameH() { return pack === "star" ? STAR_FRAME_H : METRO_FRAME_H; }

  function sheetRect(actor, now) {
    var col, row, flip, fw, fh;
    fw = frameW();
    fh = frameH();
    flip = false;
    if (pack === "star") {
      /* guest_role: row 0 face right, row 1 face left. 4-frame walk. */
      row = (actor.dir === "left") ? 1 : 0;
      if (actor.activity === "offline") col = 1;
      else col = ((now / WALK_FRAME_MS) | 0) % STAR_COLS;
      return { sx: col * fw, sy: row * fh, fw: fw, fh: fh, flip: false };
    }
    col = METRO_WALK[1];
    if (actor.activity === "build" && !actor.moving) col = METRO_TYPE[((now / TYPE_FRAME_MS) | 0) % METRO_TYPE.length];
    else if (actor.activity === "talk" && !actor.moving) col = METRO_READ[((now / TYPE_FRAME_MS) | 0) % METRO_READ.length];
    else if (actor.moving || actor.activity === "talk") col = METRO_WALK[((now / WALK_FRAME_MS) | 0) % METRO_WALK.length];
    row = actor.dir === "up" ? 1 : (actor.dir === "right" || actor.dir === "left") ? 2 : 0;
    flip = actor.dir === "left";
    return { sx: col * fw, sy: row * fh, fw: fw, fh: fh, flip: flip };
  }

  function drawActor(ctx, actor, now, scale) {
    var img, r, dw, dh, x, y;
    scale = scale || 2;
    img = sheets[actor.palette % sheets.length];
    if (!img) return false;
    r = sheetRect(actor, now);
    dw = r.fw * scale;
    dh = r.fh * scale;
    x = (actor.x | 0);
    y = (actor.y | 0);
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    if (actor.activity === "offline") ctx.globalAlpha = 0.55;
    if (r.flip) {
      ctx.translate(x + dw, y);
      ctx.scale(-1, 1);
      ctx.drawImage(img, r.sx, r.sy, r.fw, r.fh, 0, 0, dw, dh);
    } else {
      ctx.drawImage(img, r.sx, r.sy, r.fw, r.fh, x, y, dw, dh);
    }
    ctx.restore();
    return true;
  }

  function drawLabel(ctx, actor, scale) {
    var dw = frameW() * (scale || 2);
    var dh = frameH() * (scale || 2);
    var cx = (actor.x | 0) + dw / 2;
    var tag = actor.activity === "build" ? "BUILD" : actor.activity === "talk" ? "TALK" : "OFFLINE";
    var st = actor.starState || (actor.activity === "build" ? "writing" : actor.activity === "talk" ? "researching" : "idle");
    ctx.save();
    ctx.globalAlpha = actor.activity === "offline" ? 0.7 : 1;
    ctx.fillStyle = "#c8c8d0";
    ctx.font = "700 10px ui-monospace,Menlo,monospace";
    ctx.textAlign = "center";
    ctx.fillText(actor.claim, cx, (actor.y | 0) + dh + 10);
    ctx.font = "700 8px ui-monospace,Menlo,monospace";
    ctx.fillStyle = actor.activity === "build" ? "#d4c07a" : actor.activity === "talk" ? "#9ecb8a" : "#6a6a72";
    ctx.fillText(tag + " · " + st, cx, (actor.y | 0) + dh + 20);
    ctx.restore();
  }

  function hitTest(actors, x, y, scale) {
    var dw = frameW() * (scale || 2);
    var dh = frameH() * (scale || 2);
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

  /* Copied FROM point-and-click GameRuntime.ts: click → show_dialog.
     handleClick: if dialogText, clear and return; else getObjectAt → trigger click.
     renderDialog: bottom bar, "Click to continue". */
  function showDialog(actor) {
    dialog = actor ? {
      from: actor.claim || "",
      text: actor.words || "",
      starState: actor.starState || (actor.activity === "build" ? "writing" : actor.activity === "talk" ? "researching" : "idle"),
      href: actor.href || "",
      postId: actor.postId || ""
    } : null;
    return inspectHTML(actor);
  }

  function dismissDialog() {
    dialog = null;
    return "";
  }

  function drawDialogOverlay(ctx, W, H) {
    if (!dialog) return;
    var text = String(dialog.text || "").replace(/\s+/g, " ").trim();
    var pad = 8;
    var boxH = 56;
    var x = 8;
    var y = H - boxH - 8;
    var w = W - 16;
    ctx.save();
    ctx.fillStyle = "rgba(8,12,10,0.92)";
    ctx.fillRect(x, y, w, boxH);
    ctx.strokeStyle = "rgba(196,181,160,0.55)";
    ctx.strokeRect(x + 0.5, y + 0.5, w - 1, boxH - 1);
    ctx.fillStyle = "#c4b5a0";
    ctx.font = "10px ui-monospace,monospace";
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillText((dialog.from || "?") + "  [" + (dialog.starState || "idle") + "]", x + pad, y + 6);
    ctx.fillStyle = "#e7e5e4";
    ctx.font = "11px ui-sans-serif,system-ui,sans-serif";
    if (text) {
      ctx.fillText(text.length > 92 ? text.slice(0, 91) + "…" : text, x + pad, y + 22);
    } else {
      ctx.fillText("No words on the board for this seat. Quiet is not gone.", x + pad, y + 22);
    }
    ctx.fillStyle = "#78716c";
    ctx.font = "10px ui-monospace,monospace";
    ctx.fillText("▶ Click to continue  ·  GameRuntime show_dialog", x + pad, y + 38);
    ctx.restore();
  }

  function inspectHTML(actor) {
    var words = actor && actor.words ? actor.words : "";
    var href = actor && actor.href ? actor.href : "";
    var id = actor && actor.postId ? actor.postId : "";
    var st = actor && (actor.starState || actor.activity) ? (actor.starState || actor.activity) : "idle";
    var parts = [];
    parts.push("<p class=c>" + esc(actor.claim) + " · " + esc(st) + "</p>");
    if (words) parts.push("<p class=w>" + esc(words) + "</p>");
    else parts.push("<p class=w>No words on the board for this seat. Quiet is not gone.</p>");
    if (href) parts.push("<p><a href=\"" + esc(href) + "\">" + esc(id || href) + "</a></p>");
    parts.push("<p class=hint>click again to close — point-and-click show_dialog</p>");
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
    pack: function () { return pack; },
    paletteOf: paletteOf,
    wordsOf: wordsOf,
    activityOf: activityOf,
    starStateOf: starStateOf,
    dirOf: dirOf,
    drawActor: drawActor,
    drawLabel: drawLabel,
    drawDialogOverlay: drawDialogOverlay,
    hitTest: hitTest,
    dialog: function () { return dialog; },
    showDialog: showDialog,
    dismissDialog: dismissDialog,
    inspectHTML: inspectHTML,
    STAR_STATES: STAR_STATES,
    frameW: frameW,
    frameH: frameH
  };
})(this);
