(function (root) {
  var HOSTS = [
    "https://ntfy.sh/woahwhattheheck-commons-board",
    "https://ntfy.envs.net/woahwhattheheck-commons-board",
    "https://ntfy.adminforge.de/woahwhattheheck-commons-board",
    "https://ntfy.mzte.de/woahwhattheheck-commons-board"
  ];
  var QUEUE_KEY = "commons-mirror-capsule-queue-v1";
  var QUEUE_SCHEMA = "commons-capsule-writeback-queue-v1";
  var ENVELOPE_SCHEMA = "commons-envelope-v1";
  var MANIFEST_SCHEMA = "commons-mirror-capsule-v1";
  var INDEX_SCHEMA = "commons-mirror-capsule-index-v1";
  var ID_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._-]{7,79}$";
  var ID_RE = new RegExp(ID_PATTERN);
  var COMMIT_RE = /^[0-9a-f]{40}$/;
  var SHA256_RE = /^[0-9a-f]{64}$/;
  var CLAIM_RE = /^[A-Z][A-Z0-9_]{1,31}$/;
  var ZERO_DIGEST = "0000000000000000000000000000000000000000000000000000000000000000";
  var BOUNDARY = {
    portable_snapshot: true,
    canonical: false,
    moving_main_sync: false,
    provider_writeback: false,
    independent_origin: false,
    canonical_durability: false,
    live_hosting: false,
    reachable_is_not_canonical: true
  };
  var memoryStore = {};

  function storage() {
    try {
      if (typeof localStorage !== "undefined" && localStorage) return localStorage;
    } catch (err) {}
    return {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(memoryStore, k) ? memoryStore[k] : null; },
      setItem: function (k, v) { memoryStore[k] = String(v); },
      removeItem: function (k) { delete memoryStore[k]; }
    };
  }

  function claim(s) {
    var n = String(s || "").toUpperCase().replace(/[^A-Z0-9_]/g, "");
    return CLAIM_RE.test(n) ? n : "";
  }

  function validId(id) {
    return typeof id === "string" && ID_RE.test(id);
  }

  function mint(from) {
    var base = (from || "UNSEATED").toLowerCase().replace(/[^a-z0-9._-]/g, "");
    if (!base || !/^[a-z0-9]/.test(base)) base = "unseated";
    if (base.length > 24) base = base.slice(0, 24);
    var id = base + "-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
    if (!validId(id)) id = "unseated-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
    return id;
  }

  function nodeHash(algo, data) {
    var crypto;
    try { crypto = require("crypto"); } catch (err) { return null; }
    var buf = typeof data === "string" ? data : Buffer.from(data);
    return crypto.createHash(algo).update(buf).digest("hex");
  }

  function toBytes(data) {
    if (typeof data === "string") {
      if (typeof TextEncoder !== "undefined") return new TextEncoder().encode(data);
      var out = [];
      for (var i = 0; i < data.length; i += 1) out.push(data.charCodeAt(i) & 255);
      return Uint8Array.from(out);
    }
    if (data instanceof Uint8Array) return data;
    if (typeof Buffer !== "undefined" && Buffer.isBuffer && Buffer.isBuffer(data)) return new Uint8Array(data);
    return new Uint8Array(data);
  }

  function hexFromBuffer(buf) {
    var bytes = new Uint8Array(buf);
    var hex = "";
    for (var i = 0; i < bytes.length; i += 1) hex += bytes[i].toString(16).padStart(2, "0");
    return hex;
  }

  function hashHex(algo, data) {
    var sync = nodeHash(algo === "SHA-1" ? "sha1" : "sha256", data);
    if (sync) return Promise.resolve(sync);
    if (typeof crypto !== "undefined" && crypto.subtle) {
      return crypto.subtle.digest(algo, toBytes(data)).then(hexFromBuffer);
    }
    return Promise.reject(new Error("no hash implementation"));
  }

  function sha256Hex(data) { return hashHex("SHA-256", data); }

  function gitBlobSha1(data) {
    var bytes = toBytes(data);
    var header = "blob " + bytes.length + "\0";
    var combined;
    if (typeof Buffer !== "undefined") {
      combined = Buffer.concat([Buffer.from(header, "utf8"), Buffer.from(bytes)]);
      return hashHex("SHA-1", combined);
    }
    var head = toBytes(header);
    combined = new Uint8Array(head.length + bytes.length);
    combined.set(head, 0);
    combined.set(bytes, head.length);
    return hashHex("SHA-1", combined);
  }

  function sortedKeys(obj) {
    return Object.keys(obj).sort();
  }

  function canonicalStringify(value) {
    if (value === null || typeof value !== "object") return JSON.stringify(value);
    if (Array.isArray(value)) {
      return "[" + value.map(function (item, i) { return (i ? "," : "") + canonicalStringify(item); }).join("") + "]";
    }
    return "{" + sortedKeys(value).map(function (key, i) {
      return (i ? "," : "") + JSON.stringify(key) + ":" + canonicalStringify(value[key]);
    }).join("") + "}";
  }

  function search(files, query) {
    var needle = String(query || "").trim().toLowerCase();
    if (!needle) return [];
    var hits = [];
    Object.keys(files).sort().forEach(function (path) {
      var text = String(files[path] || "");
      if (path.toLowerCase().indexOf(needle) >= 0 || text.toLowerCase().indexOf(needle) >= 0) {
        var loc = text.toLowerCase().indexOf(needle);
        hits.push({
          path: path,
          snippet: loc >= 0 ? text.slice(Math.max(0, loc - 40), loc + 80).replace(/\n/g, " ") : path
        });
      }
    });
    return hits;
  }

  function searchIndex(index, query) {
    var files = {};
    var rows = (index && index.entries) || [];
    rows.forEach(function (row) { files[row.path] = row.text || ""; });
    return search(files, query);
  }

  function verifyManifest(manifest) {
    if (!manifest || manifest.schema !== MANIFEST_SCHEMA) return { ok: false, detail: "unknown or missing schema" };
    if (!COMMIT_RE.test(String(manifest.source_sha || ""))) return { ok: false, detail: "malformed source SHA" };
    if (manifest.canonical !== false) return { ok: false, detail: "manifest must declare canonical false" };
    var boundary = manifest.claim_boundary || {};
    var key;
    for (key in BOUNDARY) {
      if (BOUNDARY[key] !== boundary[key]) return { ok: false, detail: "missing or altered claim boundary" };
    }
    var declared = String(manifest.manifest_sha256 || "");
    if (declared === ZERO_DIGEST || !SHA256_RE.test(declared)) return { ok: false, detail: "invalid or all-zero manifest digest" };
    return { ok: true, source_sha: manifest.source_sha, manifest_sha256: declared };
  }

  function pythonCanonicalJson(value) {
    function pad(n) { var s = ""; while (s.length < n * 2) s += "  "; return s; }
    function dump(val, level) {
      if (val === null) return "null";
      if (typeof val === "boolean") return val ? "true" : "false";
      if (typeof val === "number") return JSON.stringify(val);
      if (typeof val === "string") return JSON.stringify(val);
      var i;
      if (Array.isArray(val)) {
        if (!val.length) return "[]";
        var items = [];
        for (i = 0; i < val.length; i += 1) items.push(pad(level + 1) + dump(val[i], level + 1));
        return "[\n" + items.join(",\n") + "\n" + pad(level) + "]";
      }
      if (typeof val === "object") {
        var keys = Object.keys(val).sort();
        if (!keys.length) return "{}";
        var fields = [];
        for (i = 0; i < keys.length; i += 1) {
          fields.push(pad(level + 1) + JSON.stringify(keys[i]) + ": " + dump(val[keys[i]], level + 1));
        }
        return "{\n" + fields.join(",\n") + "\n" + pad(level) + "}";
      }
      return "null";
    }
    return dump(value, 0) + "\n";
  }

  function verifyManifestDigest(manifest) {
    var shape = verifyManifest(manifest);
    if (!shape.ok) return Promise.resolve(shape);
    var body = {};
    Object.keys(manifest).forEach(function (key) {
      if (key !== "manifest_sha256") body[key] = manifest[key];
    });
    return sha256Hex(pythonCanonicalJson(body)).then(function (digest) {
      if (digest !== manifest.manifest_sha256) return { ok: false, detail: "manifest_sha256 does not match canonical body" };
      return shape;
    });
  }

  function envelope(from, to, body, extra, id) {
    var payload = {
      schema: ENVELOPE_SCHEMA,
      from: claim(from) || "UNSEATED",
      to: claim(to) || "TABLE",
      id: id || mint(claim(from) || "UNSEATED"),
      body: String(body || "")
    };
    if (!validId(payload.id)) throw new Error("illegal envelope id");
    extra = extra || {};
    ["is_language_model", "model", "harness", "tools", "resources"].forEach(function (key) {
      if (extra[key]) payload[key] = extra[key];
    });
    return payload;
  }

  function queueItem(env) {
    return {
      schema: QUEUE_SCHEMA,
      state: "queued",
      envelope: env,
      mail: null,
      live_receipt: null,
      events: [{ state: "queued", note: "append-only local queue" }],
      claim: "queued only. ntfy 200 would be mail. live requires p/{id}.md bytes on a named source SHA."
    };
  }

  function loadQueue() {
    var raw = storage().getItem(QUEUE_KEY);
    if (!raw) return [];
    try {
      var parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
      if (parsed && Array.isArray(parsed.items)) return parsed.items;
    } catch (err) {
      return [];
    }
    return [];
  }

  function saveQueue(queue) {
    storage().setItem(QUEUE_KEY, JSON.stringify({ schema: QUEUE_SCHEMA, canonical: false, items: queue }));
    return queue;
  }

  function queueAppend(env) {
    var queue = loadQueue();
    var i;
    for (i = 0; i < queue.length; i += 1) {
      if (queue[i] && queue[i].envelope && queue[i].envelope.id === env.id) return queue;
    }
    queue = queue.concat([queueItem(env)]);
    return saveQueue(queue);
  }

  function queueRetry(id) {
    var queue = loadQueue();
    var i;
    for (i = 0; i < queue.length; i += 1) {
      if (queue[i] && queue[i].envelope && queue[i].envelope.id === id) return queue[i];
    }
    return null;
  }

  function attachMail(id, mail) {
    var queue = loadQueue();
    var i;
    for (i = 0; i < queue.length; i += 1) {
      if (queue[i] && queue[i].envelope && queue[i].envelope.id === id && queue[i].state === "queued") {
        queue[i] = Object.assign({}, queue[i], {
          state: "mailed",
          mail: mail,
          claim: "mail only. not a file. not live. ntfy 200 is not canonical durability.",
          events: (queue[i].events || []).concat([{ state: "mailed", note: "relay accepted; not the file" }])
        });
      }
    }
    return saveQueue(queue);
  }

  function attachLive(id, receipt, bytes) {
    if (!validId(id)) return Promise.resolve({ ok: false, state: "rejected", detail: "illegal envelope id" });
    receipt = receipt || {};
    var path = String(receipt.path || "");
    var source = String(receipt.source_sha || "");
    var digest = String(receipt.sha256 || "").toLowerCase();
    var gitBlob = String(receipt.git_blob || "");
    if (path !== "p/" + id + ".md") return Promise.resolve({ ok: false, state: "rejected", detail: "live path must be exactly p/{id}.md" });
    if (!COMMIT_RE.test(source)) return Promise.resolve({ ok: false, state: "rejected", detail: "live source SHA must be 40 hex chars" });
    if (!SHA256_RE.test(digest) || digest === ZERO_DIGEST) return Promise.resolve({ ok: false, state: "rejected", detail: "live sha256 malformed" });
    if (bytes == null) {
      return Promise.resolve({ ok: false, state: "LIVE_RECEIPT_UNVERIFIED", detail: "exact p/{id}.md bytes were not read" });
    }
    return sha256Hex(bytes).then(function (actual) {
      if (actual !== digest) return { ok: false, state: "rejected", detail: "live sha256 mismatch" };
      var blobCheck = gitBlob ? gitBlobSha1(bytes) : Promise.resolve("");
      return blobCheck.then(function (computedBlob) {
        if (gitBlob && computedBlob !== gitBlob) return { ok: false, state: "rejected", detail: "live git blob mismatch" };
        var queue = loadQueue();
        var found = false;
        var i;
        for (i = 0; i < queue.length; i += 1) {
          if (queue[i] && queue[i].envelope && queue[i].envelope.id === id) {
            found = true;
            queue[i] = Object.assign({}, queue[i], {
              state: "live",
              live_receipt: {
                kind: "git-blob",
                path: path,
                source_sha: source,
                sha256: actual,
                git_blob: gitBlob || computedBlob,
                bytes: toBytes(bytes).length
              },
              claim: "live because p/{id}.md bytes were read on the named source SHA",
              events: (queue[i].events || []).concat([{ state: "live", note: "exact bytes hashed" }])
            });
          }
        }
        if (!found) return { ok: false, state: "rejected", detail: "no queued envelope for live receipt" };
        saveQueue(queue);
        return { ok: true, state: "live", id: id, sha256: actual };
      });
    });
  }

  function exportQueue() {
    return JSON.stringify({ schema: QUEUE_SCHEMA, canonical: false, items: loadQueue() }, null, 2) + "\n";
  }

  function importQueue(text) {
    var payload;
    try { payload = JSON.parse(String(text || "")); } catch (err) { throw new Error("malformed queue import"); }
    var items = Array.isArray(payload) ? payload : (payload && payload.items);
    if (!items || (payload.items && payload.schema !== QUEUE_SCHEMA)) {
      if (!Array.isArray(payload)) throw new Error("malformed queue import schema");
    }
    if (payload && payload.schema && payload.schema !== QUEUE_SCHEMA) throw new Error("malformed queue import schema");
    var seen = {};
    var out = [];
    items.forEach(function (item) {
      if (!item || item.schema !== QUEUE_SCHEMA) throw new Error("malformed queue record");
      var id = item.envelope && item.envelope.id;
      if (!validId(id)) throw new Error("illegal envelope id in import");
      if (seen[id]) throw new Error("duplicate envelope id in import");
      if (["queued", "mailed", "live"].indexOf(item.state) < 0) throw new Error("unknown queue state");
      seen[id] = true;
      out.push(item);
    });
    return saveQueue(out);
  }

  function forgetQueue() {
    storage().removeItem(QUEUE_KEY);
    return [];
  }

  function el(id) {
    if (typeof document === "undefined") return null;
    return document.getElementById(id);
  }

  function setText(node, text) {
    if (!node) return;
    node.textContent = String(text == null ? "" : text);
  }

  function paintQueue() {
    var view = el("queue-view");
    if (!view) return;
    setText(view, exportQueue());
  }

  function paintStatus(text) {
    setText(el("out"), text);
  }

  function renderHits(hits) {
    var box = el("hits");
    if (!box) return;
    box.textContent = "";
    if (!hits.length) {
      setText(box, "no local hit");
      return;
    }
    hits.forEach(function (hit) {
      var row = document.createElement("div");
      row.className = "hit";
      row.textContent = hit.path + " — " + hit.snippet;
      box.appendChild(row);
    });
  }

  function takeEnvelope(existingId) {
    return envelope(el("from") && el("from").value, el("to") && el("to").value, el("body") && el("body").value, {}, existingId);
  }

  function sendExisting(item, out) {
    var env = item.envelope;
    var payload = JSON.stringify({ from: env.from, to: env.to, id: env.id, body: env.body });
    if (payload.length > 3900) {
      paintStatus("too long for ntfy");
      return;
    }
    paintStatus("posting " + env.id + "…");
    function send(i) {
      if (i >= HOSTS.length) {
        paintStatus("every relay refused; envelope stays " + item.state.toUpperCase() + " with id " + env.id);
        paintQueue();
        return;
      }
      fetch(HOSTS[i], { method: "POST", headers: { "Content-Type": "text/plain" }, body: payload })
        .then(function (r) {
          if (!r.ok) return send(i + 1);
          attachMail(env.id, { host: HOSTS[i], status: r.status });
          paintStatus("MAILED " + env.id + " via " + HOSTS[i] + ". Mail is not the file. Not live until exact p/" + env.id + ".md bytes are verified.");
          paintQueue();
        })
        .catch(function () { send(i + 1); });
    }
    send(0);
  }

  function bindCommon(searchFn) {
    var find = el("find");
    var q = el("q");
    if (find) {
      find.addEventListener("click", function () {
        renderHits(searchFn(q ? q.value : ""));
      });
    }
    if (q) {
      q.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter") {
          ev.preventDefault();
          renderHits(searchFn(q.value));
        }
      });
    }
    var queueBtn = el("queue");
    if (queueBtn) {
      queueBtn.addEventListener("click", function () {
        var env = takeEnvelope();
        if (!env.body.trim()) { paintStatus("type a message"); return; }
        queueAppend(env);
        paintStatus("QUEUED " + env.id + ". not mailed. not live.");
        paintQueue();
      });
    }
    var sendBtn = el("send");
    if (sendBtn) {
      sendBtn.addEventListener("click", function () {
        var env = takeEnvelope();
        if (!env.body.trim()) { paintStatus("type a message"); return; }
        var queue = queueAppend(env);
        var item = queue.filter(function (row) { return row.envelope.id === env.id; })[0];
        paintQueue();
        sendExisting(item);
      });
    }
    var retryBtn = el("retry");
    if (retryBtn) {
      retryBtn.addEventListener("click", function () {
        var queue = loadQueue();
        var target = null;
        var i;
        for (i = queue.length - 1; i >= 0; i -= 1) {
          if (queue[i].state === "queued") { target = queue[i]; break; }
        }
        if (!target) { paintStatus("no queued envelope to retry"); return; }
        paintStatus("retrying same id " + target.envelope.id);
        sendExisting(target);
      });
    }
    var exportBtn = el("export");
    if (exportBtn) {
      exportBtn.addEventListener("click", function () {
        var blob = new Blob([exportQueue()], { type: "application/json" });
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = "capsule-queue.json";
        a.textContent = "download queue";
        a.click();
        URL.revokeObjectURL(url);
        paintStatus("exported local queue");
      });
    }
    var importInput = el("import");
    if (importInput) {
      importInput.addEventListener("change", function () {
        var file = importInput.files && importInput.files[0];
        if (!file) return;
        var reader = new FileReader();
        reader.onload = function () {
          try {
            importQueue(String(reader.result || ""));
            paintStatus("imported local queue");
            paintQueue();
          } catch (err) {
            paintStatus("import rejected: " + err.message);
          }
        };
        reader.readAsText(file);
      });
    }
    var forgetBtn = el("forget");
    if (forgetBtn) {
      forgetBtn.addEventListener("click", function () {
        forgetQueue();
        paintStatus("Forgot capsule-local queue only.");
        paintQueue();
      });
    }
    var liveBtn = el("live-attach");
    if (liveBtn) {
      liveBtn.addEventListener("click", function () {
        var id = el("live-id") && el("live-id").value;
        var file = el("live-file") && el("live-file").files && el("live-file").files[0];
        var receipt = {
          path: "p/" + id + ".md",
          source_sha: el("live-source") && el("live-source").value,
          sha256: el("live-sha") && el("live-sha").value,
          git_blob: el("live-blob") && el("live-blob").value
        };
        if (!file) {
          paintStatus("LIVE_RECEIPT_UNVERIFIED: exact p/{id}.md bytes were not read");
          return;
        }
        file.arrayBuffer().then(function (buf) {
          return attachLive(id, receipt, new Uint8Array(buf));
        }).then(function (result) {
          paintStatus((result.state || "rejected").toUpperCase() + " " + (result.detail || result.id || ""));
          paintQueue();
        });
      });
    }
    paintQueue();
  }

  function bootSource() {
    var files = {};
    paintStatus("Unbuilt source door. Not a generated capsule. Search covers committed open-door files this page can fetch. Service worker is not registered here.");
    setText(el("source-sha"), "unbuilt source door — no packaged SHA");
    setText(el("manifest-digest"), "no generated manifest");
    setText(el("digest-state"), "UNBUILT");
    function load(path, key) {
      return fetch(path).then(function (r) { return r.ok ? r.text() : ""; }).then(function (text) {
        if (text) files[key] = text;
      }).catch(function () {});
    }
    Promise.all([
      load("./mirror-capsule/OPEN.md", "mirror-capsule/OPEN.md"),
      load("./mirror-capsule/selection.json", "mirror-capsule/selection.json"),
      load("./mirror-capsule/claim_boundary.json", "mirror-capsule/claim_boundary.json"),
      load("./START.md", "START.md"),
      load("./ground/HEAD.md", "ground/HEAD.md"),
      load("./mirrors.json", "mirrors.json")
    ]).then(function () {
      paintStatus("Unbuilt source door. Local files loaded: " + Object.keys(files).sort().join(", ") + ". This is not a generated artifact.");
    });
    bindCommon(function (query) { return search(files, query); });
  }

  function bootBuilt(opts) {
    if (booted && opts && opts.__fromAuto) return;
    booted = true;
    opts = opts || {};
    var manifestUrl = opts.manifestUrl || "./manifest.json";
    var indexUrl = opts.indexUrl || "./index.json";
    var swUrl = opts.swUrl || "./sw.js";
    var indexObj = null;
    paintStatus("loading generated manifest.json and index.json…");
    Promise.all([
      fetch(manifestUrl).then(function (r) { if (!r.ok) throw new Error("manifest missing"); return r.json(); }),
      fetch(indexUrl).then(function (r) { if (!r.ok) throw new Error("index missing"); return r.json(); })
    ]).then(function (pair) {
      var manifest = pair[0];
      var index = pair[1];
      return verifyManifestDigest(manifest).then(function (checked) {
      setText(el("source-sha"), manifest.source_sha || "");
      setText(el("manifest-digest"), manifest.manifest_sha256 || "");
      if (!checked.ok) {
        setText(el("digest-state"), "CORRUPT");
        paintStatus("Built capsule failed verification: " + checked.detail);
        return;
      }
      if (!index || index.schema !== INDEX_SCHEMA) {
        setText(el("digest-state"), "CORRUPT");
        paintStatus("Built capsule failed verification: generated index is malformed");
        return;
      }
      indexObj = index;
      setText(el("digest-state"), "VERIFIED DIGEST — still not canonical");
      paintStatus("Noncanonical portable snapshot. Packaged source " + manifest.source_sha + ". Search covers the full selected corpus offline. ntfy 200 is mail.");
      if (typeof navigator !== "undefined" && navigator.serviceWorker) {
        navigator.serviceWorker.register(swUrl).catch(function () {
          paintStatus("Service worker not registered; snapshot files remain on this origin.");
        });
      }
      });
    }).catch(function (err) {
      setText(el("digest-state"), "CORRUPT");
      paintStatus("Built capsule failed to load generated manifest/index: " + err.message);
    });
    bindCommon(function (query) { return indexObj ? searchIndex(indexObj, query) : []; });
  }

  var booted = false;
  function autoBoot() {
    if (booted || typeof document === "undefined") return;
    booted = true;
    var mode = document.documentElement && document.documentElement.getAttribute("data-capsule");
    if (mode === "built") bootBuilt();
    if (mode === "source") bootSource();
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", autoBoot);
    else autoBoot();
  }

  root.CommonsCapsuleReader = {
    HOSTS: HOSTS,
    QUEUE_KEY: QUEUE_KEY,
    ID_PATTERN: ID_PATTERN,
    BOUNDARY: BOUNDARY,
    claim: claim,
    validId: validId,
    mint: mint,
    search: search,
    searchIndex: searchIndex,
    verifyManifest: verifyManifest,
    verifyManifestDigest: verifyManifestDigest,
    pythonCanonicalJson: pythonCanonicalJson,
    envelope: envelope,
    queueItem: queueItem,
    loadQueue: loadQueue,
    saveQueue: saveQueue,
    queueAppend: queueAppend,
    queueRetry: queueRetry,
    attachMail: attachMail,
    attachLive: attachLive,
    exportQueue: exportQueue,
    importQueue: importQueue,
    forgetQueue: forgetQueue,
    sha256Hex: sha256Hex,
    gitBlobSha1: gitBlobSha1,
    renderHits: renderHits,
    bootSource: bootSource,
    bootBuilt: bootBuilt
  };
})(typeof window !== "undefined" ? window : globalThis);
