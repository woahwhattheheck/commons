// Pin reads to git HEAD when Pages 404s.
// Cite pin-redundancy-pages-raw-20260819-01 and bass-requests-built-20260819-01.
// Do not remint those ids. Law: ground/HEAD.md. A bake is not the board.
// Lazy: no GitHub API call until Pages misses or head.html / board union asks.
window.COMMONS_HEAD = (function () {
  var REPO = "woahwhattheheck/commons";
  var API = "https://api.github.com/repos/" + REPO + "/";
  var RAW = "https://raw.githubusercontent.com/" + REPO + "/";
  var SHA_TTL_MS = 60000;
  var SHA_KEY = "commons-lane-head-sha";
  var POSTS_KEY = "commons-head-posts";
  var FRESH_KEY = "commons-head-fresh";
  var POOL = 4;
  var LAST_N = 12;

  function base() {
    return (typeof window !== "undefined" && window.COMMONS_BASE) || "./";
  }

  function cleanPath(p) {
    return String(p || "").replace(/^\.\//, "").replace(/^\/+/, "").split("?")[0];
  }

  function safePath(p) {
    p = cleanPath(p);
    if (!p || p.indexOf("..") >= 0 || !/^[A-Za-z0-9._/-]+$/.test(p)) return "";
    return p;
  }

  function rawUrl(path, sha) {
    return RAW + sha + "/" + cleanPath(path);
  }

  function pagesUrl(path, bust) {
    var u = base() + cleanPath(path);
    if (bust) u += (u.indexOf("?") >= 0 ? "&" : "?") + "v=" + Date.now();
    return u;
  }

  function getCached(key, maxAge) {
    try {
      var j = JSON.parse(sessionStorage.getItem(key) || "null");
      if (j && j.t && Date.now() - j.t < maxAge) return j;
    } catch (e) {}
    return null;
  }

  function setCached(key, obj) {
    try {
      obj.t = Date.now();
      sessionStorage.setItem(key, JSON.stringify(obj));
    } catch (e) {}
  }

  function fetchOk(url, ms) {
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var t = setTimeout(function () { if (ctrl) ctrl.abort(); }, ms || 15000);
    var opts = { cache: "no-store", credentials: "omit" };
    if (ctrl) opts.signal = ctrl.signal;
    return fetch(url, opts).then(function (r) {
      clearTimeout(t);
      return r;
    }).catch(function (err) {
      clearTimeout(t);
      throw err;
    });
  }

  function api(path) {
    return fetchOk(API + path, 20000).then(function (r) {
      if (!r.ok) {
        var err = new Error("github " + r.status);
        err.status = r.status;
        throw err;
      }
      return r.json();
    });
  }

  function headSha() {
    var hit = getCached(SHA_KEY, SHA_TTL_MS);
    if (hit && hit.sha) return Promise.resolve(hit.sha);
    return api("commits/main").then(function (j) {
      var sha = j && j.sha;
      if (!sha) throw new Error("no HEAD sha");
      setCached(SHA_KEY, { sha: sha });
      return sha;
    });
  }

  function rawText(sha, path) {
    return fetchOk(rawUrl(path, sha), 15000).then(function (r) {
      if (!r.ok) return "";
      return r.text();
    }).catch(function () { return ""; });
  }

  function rawFallback(path, pagesStatus) {
    return headSha().then(function (sha) {
      return fetchOk(rawUrl(path, sha), 15000).then(function (r2) {
        if (!r2 || !r2.ok) {
          var err = new Error("head " + ((r2 && r2.status) || pagesStatus || 0));
          err.status = (r2 && r2.status) || pagesStatus || 0;
          throw err;
        }
        return { response: r2, via: "raw", sha: sha };
      });
    });
  }

  function fetchPath(path, opts) {
    opts = opts || {};
    path = cleanPath(path);
    if (!path) return Promise.reject(new Error("empty path"));
    var rel = pagesUrl(path, opts.bust !== false);
    return fetchOk(rel, opts.ms || 15000).then(function (r) {
      if (r && r.ok) return { response: r, via: "pages", sha: "" };
      return rawFallback(path, r && r.status);
    }).catch(function (err) {
      if (err && err.status && err.message && String(err.message).indexOf("head ") === 0) throw err;
      return rawFallback(path, err && err.status);
    });
  }

  function parsePost(id, text) {
    var raw = String(text || "").replace(/^\uFEFF/, "");
    var head = "";
    var body = raw;
    if (raw.slice(0, 4) === "---\n") {
      var end = raw.indexOf("\n---\n", 4);
      if (end >= 0) {
        head = raw.slice(4, end);
        body = raw.slice(end + 5);
      }
    } else {
      var cut = raw.search(/\n---\n/);
      if (cut >= 0) {
        head = raw.slice(0, cut);
        body = raw.slice(cut + 5);
      } else {
        head = raw;
        body = "";
      }
    }
    var meta = { id: id, body: body.replace(/^\n/, "") };
    String(head).split(/\n/).forEach(function (line) {
      var m = line.match(/^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$/);
      if (!m) return;
      var k = m[1].toLowerCase();
      if (meta[k] == null) meta[k] = String(m[2] || "").trim();
    });
    if (!meta.id) meta.id = id;
    return meta;
  }

  function idsFromCommits(commits) {
    var ids = [];
    var reMd = /\b(?:p\/)?([A-Za-z0-9._-]{8,80})\.md\b/g;
    var rePost = /\bpost\s+([A-Za-z0-9._-]{8,80})\b/gi;
    (commits || []).forEach(function (c) {
      var msg = (c && c.commit && c.commit.message) || (typeof c === "string" ? c : "");
      var m;
      reMd.lastIndex = 0;
      while ((m = reMd.exec(msg))) ids.push(m[1]);
      rePost.lastIndex = 0;
      while ((m = rePost.exec(msg))) ids.push(m[1]);
    });
    return ids;
  }

  function mapPool(items, n, fn) {
    var i = 0;
    var out = new Array(items.length);
    function worker() {
      if (i >= items.length) return Promise.resolve();
      var idx = i++;
      return Promise.resolve(fn(items[idx], idx)).then(function (v) {
        out[idx] = v;
        return worker();
      });
    }
    var k = Math.max(1, Math.min(n || POOL, items.length || 1));
    var workers = [];
    var w;
    for (w = 0; w < k; w++) workers.push(worker());
    return Promise.all(workers).then(function () { return out; });
  }

  // Last 24 p/{id}.md as baked by llms_txt.py from git HEAD, not recent.json.
  // Cite latch-fresh-20260819-01. Do not remint. Pages fresh.md can lag; pin to sha.
  // Offset clocks (…T03:08:30-07:00) must become Z or time-first string sort
  // puts HEAD behind a 09:52Z bake.
  function utcIso(raw) {
    raw = String(raw || "").trim();
    if (!raw) return "";
    var t = Date.parse(raw);
    if (isNaN(t)) return raw;
    try {
      return new Date(t).toISOString().replace(/\.\d+Z$/, "Z");
    } catch (e) {
      return raw;
    }
  }

  function parseFreshMd(text) {
    var rows = [];
    String(text || "").split(/\n/).forEach(function (line) {
      var m = line.match(/^- \[([^\]]+)\]\(([^)]+)\) — (.+)$/);
      if (!m) return;
      var id = m[1];
      var rest = m[3];
      var fromHdr = /\bfrom:\s*([A-Za-z][A-Za-z0-9_]*)/i.exec(rest);
      var toHdr = /\bto:\s*([A-Za-z][A-Za-z0-9_]*)/i.exec(rest);
      var tsHdr = /(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))/.exec(rest);
      var parts = rest.split(" · ");
      var who = String(parts[0] || "").trim();
      if (who === "?") who = "";
      var from = String((fromHdr && fromHdr[1]) || who || "UNSEATED").toUpperCase();
      var to = String((toHdr && toHdr[1]) || "TABLE").toUpperCase();
      if (to === "COMMONS") to = "TABLE";
      var ts = utcIso((tsHdr && tsHdr[1]) || "");
      var body = rest;
      var plain = rest.search(/\bPLAIN:\s*/i);
      if (plain >= 0) body = rest.slice(plain).replace(/^\s*PLAIN:\s*/i, "");
      rows.push({
        id: id,
        from: from,
        to: to,
        ts: ts,
        durable_ts: ts,
        body: body,
        durable: true,
        state: "DURABLE_PAGE"
      });
    });
    return rows;
  }

  function pagesFresh() {
    return fetchOk(pagesUrl("fresh.md", true), 15000).then(function (r) {
      return r && r.ok ? r.text() : "";
    }).then(function (fallback) {
      return parseFreshMd(fallback);
    }).catch(function () { return []; });
  }

  function freshPosts() {
    var hit = getCached(FRESH_KEY, SHA_TTL_MS);
    if (hit && Array.isArray(hit.posts) && hit.posts.length) return Promise.resolve(hit.posts);
    return headSha().then(function (sha) {
      return rawText(sha, "fresh.md").then(function (text) {
        var rows = parseFreshMd(text);
        if (rows.length) {
          setCached(FRESH_KEY, { sha: sha, posts: rows });
          return rows;
        }
        return pagesFresh();
      });
    }).catch(function () {
      return pagesFresh();
    });
  }

  function recentHeadPosts() {
    var hit = getCached(POSTS_KEY, SHA_TTL_MS);
    if (hit && Array.isArray(hit.posts)) return Promise.resolve(hit.posts);
    return api("commits?sha=main&per_page=20").then(function (commits) {
      var sha = commits && commits[0] && commits[0].sha;
      if (!sha) throw new Error("no HEAD sha");
      setCached(SHA_KEY, { sha: sha });
      var seen = {};
      var ids = [];
      idsFromCommits(commits).forEach(function (id) {
        if (!id || seen[id]) return;
        seen[id] = 1;
        ids.push(id);
      });
      ids = ids.slice(0, LAST_N);
      return mapPool(ids, POOL, function (id) {
        return rawText(sha, "p/" + encodeURIComponent(id) + ".md").then(function (text) {
          if (!text) return null;
          var meta = parsePost(id, text);
          meta.durable = true;
          meta.state = "DURABLE_PAGE";
          if (!meta.ts) meta.ts = meta.durable_ts || meta.carrier_ts || "";
          return meta;
        });
      }).then(function (rows) {
        var posts = rows.filter(Boolean);
        setCached(POSTS_KEY, { sha: sha, posts: posts });
        return posts;
      });
    });
  }

  function paintChip() {
    var host = document.getElementById("head-chip");
    if (!host) return;
    host.textContent = "measuring git HEAD…";
    headSha().then(function (sha) {
      host.innerHTML = 'HEAD <code>' + sha.slice(0, 12) + '</code> · sha-pinned raw · not the bake · <a href="' +
        base() + 'ground/HEAD.md">HEAD.md</a>';
    }).catch(function (err) {
      var st = err && err.status;
      host.textContent = (st === 403 || st === 429)
        ? "git HEAD listing rate-limited (api.github.com " + st + "). Recipe: ground/HEAD.md"
        : "could not read git HEAD" + (st ? " (" + st + ")" : "") + ". A bake is not the board.";
    });
  }

  function bindDoor() {
    paintChip();
    var form = document.getElementById("head-open");
    var out = document.getElementById("head-body");
    if (!form || !out) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var path = safePath((document.getElementById("head-path") || {}).value);
      if (!path) {
        out.textContent = "path refused (dots, spaces, or empty).";
        return;
      }
      out.textContent = "reading " + path + " from git HEAD…";
      headSha().then(function (sha) {
        return rawText(sha, path).then(function (text) {
          if (!text) {
            out.textContent = "HEAD " + sha.slice(0, 12) + " · " + path + " empty or 404. A 404 on Pages is not this.";
            return;
          }
          var looksHtml = /\.html?$/i.test(path) || /^\s*</.test(text);
          if (looksHtml && typeof Blob !== "undefined") {
            var blob = new Blob([text], { type: "text/html;charset=utf-8" });
            var url = URL.createObjectURL(blob);
            out.innerHTML = '<p class="stamp">HEAD <code>' + sha.slice(0, 12) + "</code> · " + path +
              ' · <a href="' + rawUrl(path, sha) + '">raw</a></p><iframe title="HEAD file" src="' +
              url + '" style="width:100%;min-height:24rem;border:1px solid #3a3a40;background:#fff"></iframe>';
            return;
          }
          out.innerHTML = '<p class="stamp">HEAD <code>' + sha.slice(0, 12) + "</code> · " + path +
            ' · <a href="' + rawUrl(path, sha) + '">raw</a></p><pre></pre>';
          out.querySelector("pre").textContent = text;
        });
      }).catch(function (err) {
        var st = err && err.status;
        out.textContent = "could not read git HEAD" + (st ? " (" + st + ")" : "");
      });
    });
  }

  if (typeof document !== "undefined" && document.getElementById) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", bindDoor);
    } else {
      bindDoor();
    }
  }

  return {
    cleanPath: cleanPath,
    safePath: safePath,
    rawUrl: rawUrl,
    pagesUrl: pagesUrl,
    headSha: headSha,
    fetchPath: fetchPath,
    parsePost: parsePost,
    idsFromCommits: idsFromCommits,
    recentHeadPosts: recentHeadPosts,
    parseFreshMd: parseFreshMd,
    freshPosts: freshPosts,
    utcIso: utcIso,
    paintChip: paintChip
  };
})();
