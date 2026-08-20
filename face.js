/* face.js — draw the 48 AUTOFAB0 columns. Do not narrow them.
   glyphs.json is the font on HEAD. The 65-byte string is the sentence. */
(function () {
  "use strict";

  function hexToBits(hex, depth) {
    var out = [], i, byte, bit;
    for (i = 0; i < hex.length; i += 2) {
      byte = parseInt(hex.slice(i, i + 2), 16);
      for (bit = 7; bit >= 0; bit--) out.push((byte >> bit) & 1);
    }
    return out.slice(0, depth);
  }

  function drawGlyph(canvas, bits, wrap, scale, on, off) {
    var rows = Math.ceil(bits.length / wrap);
    var ctx = canvas.getContext("2d");
    canvas.width = wrap * scale;
    canvas.height = rows * scale;
    ctx.fillStyle = off;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = on;
    var i, x, y;
    for (i = 0; i < bits.length; i++) {
      if (!bits[i]) continue;
      x = (i % wrap) * scale;
      y = Math.floor(i / wrap) * scale;
      ctx.fillRect(x, y, scale, scale);
    }
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function hexPairs(hex) {
    return hex.replace(/(.{2})/g, "$1 ").trim();
  }

  function mount(opts) {
    var sheet = opts.sheet, sentenceEl = opts.sentence, mailEl = opts.mail, statusEl = opts.status;
    var wrap = opts.wrap || 32, scale = opts.scale || 2;
    statusEl.textContent = "reading glyphs.json…";
    fetch("./glyphs.json?v=" + Date.now(), { cache: "no-store", credentials: "omit" })
      .then(function (r) {
        if (!r.ok) throw new Error("glyphs.json " + r.status);
        return r.json();
      })
      .then(function (data) {
        var glyphs = data.glyphs || [];
        if (glyphs.length !== 48) {
          statusEl.textContent = "glyphs.json has " + glyphs.length + " columns — expected 48. Not narrowed here; check the file.";
        } else {
          statusEl.textContent = data.source + " · " + data.source_bytes.toLocaleString() +
            " B · tile " + data.tile.join("×") + " · K=" + data.K +
            " · 48 distinct · string " + data.string_zlib_bytes + " B · table " +
            data.table_zlib_bytes + " B · " + data.address_space;
        }
        sheet.innerHTML = "";
        glyphs.forEach(function (g) {
          var bits = hexToBits(g.hex, data.K);
          var fig = document.createElement("figure");
          var canvas = document.createElement("canvas");
          canvas.setAttribute("aria-label", "glyph " + g.i);
          drawGlyph(canvas, bits, wrap, scale, "#e8c36a", "#101012");
          var cap = document.createElement("figcaption");
          cap.textContent = g.i + " · ×" + g.count + " · " + g.ones + " ones";
          fig.appendChild(canvas);
          fig.appendChild(cap);
          sheet.appendChild(fig);
        });
        sentenceEl.innerHTML = "";
        (data.sentence || []).forEach(function (idx, n) {
          var g = glyphs[idx];
          if (!g) return;
          var cell = document.createElement("span");
          cell.className = "cell";
          cell.title = "cell " + n + " = glyph " + idx;
          var canvas = document.createElement("canvas");
          drawGlyph(canvas, hexToBits(g.hex, data.K), 64, 1, "#c8d4c8", "#0d100e");
          var lab = document.createElement("b");
          lab.textContent = idx;
          cell.appendChild(canvas);
          cell.appendChild(lab);
          sentenceEl.appendChild(cell);
        });
        mailEl.innerHTML = "<p>65 bytes. This is the mailed sentence (zlib of the 200-cell stream). " +
          "The column dictionary stays on HEAD as <a href=\"./glyphs.json\">glyphs.json</a>. " +
          "Send the sentence; keep the font. Portable alphabet, not zip-the-computer.</p><pre>" +
          esc(hexPairs(data.string_zlib_hex || "")) + "</pre>";
      })
      .catch(function (err) {
        statusEl.textContent = "could not read glyphs.json: " + err.message;
      });
  }

  window.FACE48 = { mount: mount };
})();
