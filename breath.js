/* breath.js — measure the image, not the file.
   Browser decodes the PNG. We box the change and show the pictures.
   Do not trust a coded zero from a file watch. */
(function () {
  "use strict";

  function loadImage(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () { resolve({ img: img, url: url, name: file.name }); };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        reject(new Error(file.name + " would not decode"));
      };
      img.src = url;
    });
  }

  function raster(img) {
    var c = document.createElement("canvas");
    c.width = img.width;
    c.height = img.height;
    var ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(img, 0, 0);
    return ctx.getImageData(0, 0, img.width, img.height);
  }

  function diffPixels(a, b) {
    var n = 0, i, x, y, w = a.width, h = a.height;
    var minX = w, minY = h, maxX = -1, maxY = -1;
    var out = new ImageData(w, h);
    var A = a.data, B = b.data, D = out.data;
    for (y = 0; y < h; y++) {
      for (x = 0; x < w; x++) {
        i = (y * w + x) * 4;
        var dr = Math.abs(A[i] - B[i]);
        var dg = Math.abs(A[i + 1] - B[i + 1]);
        var db = Math.abs(A[i + 2] - B[i + 2]);
        var same = dr + dg + db === 0 && A[i + 3] === B[i + 3];
        if (same) {
          D[i] = D[i + 1] = D[i + 2] = 16;
          D[i + 3] = 255;
        } else {
          n++;
          if (x < minX) minX = x;
          if (y < minY) minY = y;
          if (x > maxX) maxX = x;
          if (y > maxY) maxY = y;
          var v = Math.min(255, Math.max(dr, dg, db) * 3 + 60);
          D[i] = v;
          D[i + 1] = v;
          D[i + 2] = v;
          D[i + 3] = 255;
        }
      }
    }
    return {
      n: n,
      tot: w * h,
      box: n ? { x0: minX, y0: minY, x1: maxX, y1: maxY } : null,
      image: out
    };
  }

  function drawFramed(canvas, img, box) {
    var ctx = canvas.getContext("2d");
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0);
    if (!box) return;
    ctx.strokeStyle = "#e08060";
    ctx.lineWidth = Math.max(2, Math.round(Math.min(img.width, img.height) / 200));
    ctx.strokeRect(box.x0 + 0.5, box.y0 + 0.5, box.x1 - box.x0, box.y1 - box.y0);
  }

  function drawDiff(canvas, image) {
    canvas.width = image.width;
    canvas.height = image.height;
    canvas.getContext("2d").putImageData(image, 0, 0);
  }

  function mount(opts) {
    var inhale = opts.inhale, exhale = opts.exhale, go = opts.go, out = opts.out;
    var aCan = opts.a, bCan = opts.b, dCan = opts.diff;

    function run() {
      var fa = inhale.files && inhale.files[0];
      var fb = exhale.files && exhale.files[0];
      if (!fa || !fb) {
        out.textContent = "Drop one inhale and one exhale. Screenshots. Then look.";
        return;
      }
      out.textContent = "decoding pictures…";
      Promise.all([loadImage(fa), loadImage(fb)]).then(function (pair) {
        var A = pair[0], B = pair[1];
        if (A.img.width !== B.img.width || A.img.height !== B.img.height) {
          out.innerHTML = "SIZE MISMATCH " + A.img.width + "×" + A.img.height +
            " vs " + B.img.width + "×" + B.img.height +
            " — window resized, NOT comparable. Open both pictures anyway.";
          drawFramed(aCan, A.img, null);
          drawFramed(bCan, B.img, null);
          return;
        }
        var d = diffPixels(raster(A.img), raster(B.img));
        drawFramed(aCan, A.img, d.box);
        drawFramed(bCan, B.img, d.box);
        drawDiff(dCan, d.image);
        var pct = (100 * d.n / Math.max(d.tot, 1)).toFixed(4);
        var box = d.box
          ? ("bounding box of the change: x " + d.box.x0 + ".." + d.box.x1 +
             "   y " + d.box.y0 + ".." + d.box.y1 +
             "<br>NOW OPEN BOTH IMAGES AND LOOK AT THAT BOX.")
          : "no pixel differed in this decode.";
        out.innerHTML = A.name + " vs " + B.name + " — " +
          d.n.toLocaleString() + " / " + d.tot.toLocaleString() +
          " px differ (" + pct + "%)<br>" + box;
      }).catch(function (err) {
        out.textContent = err.message;
      });
    }

    go.addEventListener("click", function (e) {
      e.preventDefault();
      run();
    });
    inhale.addEventListener("change", run);
    exhale.addEventListener("change", run);
  }

  window.BREATH = { mount: mount };
})();
