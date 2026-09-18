// DOM-free exact-main resolver contract. No network calls.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL " + msg);
    process.exit(1);
  }
  console.log("PASS " + msg);
}

function pkt(payload) {
  return (payload.length + 4).toString(16).padStart(4, "0") + payload;
}

function latin1Buffer(value) {
  const bytes = new Uint8Array(value.length);
  for (let i = 0; i < value.length; i += 1) bytes[i] = value.charCodeAt(i);
  return bytes.buffer;
}

const src = fs.readFileSync(path.join(__dirname, "exact-main.js"), "utf8");
const storage = {
  values: {},
  getItem(key) { return this.values[key] || null; },
  setItem(key, value) { this.values[key] = String(value); }
};
const sandbox = {
  globalThis: {},
  window: undefined,
  sessionStorage: storage,
  setTimeout,
  clearTimeout,
  AbortController,
  ArrayBuffer,
  Uint8Array,
  Promise,
  console
};
sandbox.globalThis = sandbox;
vm.runInNewContext(src, sandbox);
const api = sandbox.COMMONS_EXACT_MAIN;
assert(api && api.resolveBrowser && api.parseGitAdvertisement, "exact-main exports one DOM-free browser resolver and parser");
assert(api.isSha("ABCDEFABCDEFABCDEFABCDEFABCDEFABCDEFABCD"), "SHA validation accepts uppercase input as exact hexadecimal");
assert(!api.isSha("main") && !api.isSha("a".repeat(39)) && !api.isSha("g".repeat(40)), "SHA validation rejects branches, wrong lengths, and non-hex text");
assert(!api.isSha(" " + "a".repeat(40)) && !api.isSha("a".repeat(40) + " "), "SHA validation rejects surrounding whitespace instead of changing the exact address");

const shaA = "1111111111111111111111111111111111111111";
const shaB = "2222222222222222222222222222222222222222";
const advertisement = pkt("# service=git-upload-pack\n") + "0000" +
  pkt(shaB + " HEAD\0multi_ack symref=HEAD:refs/heads/main agent=git/test\n") +
  pkt(shaB + " refs/heads/main\n") + "0000";
assert(api.parseGitAdvertisement(advertisement) === shaB, "pkt parser resolves agreeing explicit main and symbolic HEAD");
assert(api.parseGitAdvertisement(latin1Buffer(advertisement)) === shaB, "pkt parser consumes browser ArrayBuffer bytes");
const headOnly = pkt(shaA + " HEAD\0symref=HEAD:refs/heads/main agent=git/test\n") + "0000";
assert(api.parseGitAdvertisement(headOnly) === shaA, "pkt parser accepts capability-bound symbolic HEAD when main row is absent");
assert(api.parseGitAdvertisement(pkt(shaA + " refs/heads/main-evil\n") + "0000") === "", "main-like ref cannot impersonate refs/heads/main");

function rejectsParse(value) {
  try { api.parseGitAdvertisement(value); } catch (_) { return true; }
  return false;
}

assert(rejectsParse("000"), "truncated pkt header is rejected");
assert(rejectsParse("0008bad"), "truncated pkt payload is rejected");
assert(rejectsParse("0003"), "reserved pkt length is rejected");
assert(rejectsParse(pkt("not-a-sha refs/heads/main\n") + "0000"), "malformed main SHA is rejected");
assert(rejectsParse(pkt(shaA + " refs/heads/main\n") + pkt(shaB + " refs/heads/main\n") + "0000"), "conflicting main refs are rejected");
assert(rejectsParse(pkt(shaA + " HEAD\0symref=HEAD:refs/heads/main\n") + pkt(shaB + " refs/heads/main\n") + "0000"), "symbolic HEAD disagreement is rejected");
const byteCounted = pkt(shaA + " refs/heads/f\xc3\xa9ature\n") + pkt(shaB + " refs/heads/main\n") + "0000";
assert(api.parseGitAdvertisement(byteCounted) === shaB, "non-ASCII bytes in an earlier ref cannot desynchronize pkt offsets");
assert(rejectsParse(new Uint8Array(2 * 1024 * 1024 + 1)), "advertisements above the fixed 2 MiB ceiling are rejected");

async function run() {
  let gitCalls = 0;
  const primary = await api.resolve(
    () => Promise.resolve({ sha: shaA }),
    () => { gitCalls += 1; return Promise.resolve(advertisement); }
  );
  assert(primary.sha === shaA && primary.via === "GitHub commits API", "valid API response resolves exact main through the primary road");
  assert(gitCalls === 0, "valid API response never calls the fallback");

  let whitespaceGitCalls = 0;
  const whitespacePrimary = await api.resolve(
    () => Promise.resolve({ sha: " " + shaA }),
    () => { whitespaceGitCalls += 1; return Promise.resolve(advertisement); }
  );
  assert(whitespaceGitCalls === 1 && whitespacePrimary.sha === shaB && whitespacePrimary.via === "anonymous git smart-HTTP fallback", "whitespace-wrapped API SHA fails over instead of selecting a different address");

  const fallback = await api.resolve(
    () => Promise.reject(new Error("commits/main HTTP 403")),
    () => { gitCalls += 1; return Promise.resolve(advertisement); }
  );
  assert(gitCalls === 1 && fallback.sha === shaB, "API 403 calls the git fallback exactly once and returns its exact main SHA");
  assert(fallback.via === "anonymous git smart-HTTP fallback" && /HTTP 403/.test(fallback.primaryError), "fallback labels its road and retains primary failure evidence");

  let bothFailed = false;
  try {
    await api.resolve(
      () => Promise.reject(new Error("commits/main HTTP 403")),
      () => Promise.resolve("0008bad")
    );
  } catch (error) {
    bothFailed = /GitHub API:.*HTTP 403.*git smart-HTTP:.*truncated/.test(String(error && error.message));
  }
  assert(bothFailed, "two failed roads reject together instead of returning stale or invented state");

  const calls = [];
  sandbox.fetch = function (url, options) {
    calls.push({ url: String(url), options });
    if (String(url) === api.mainApi) {
      return Promise.resolve({
        ok: false,
        status: 403,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve({})
      });
    }
    if (String(url) === api.mainGitAdvertisement) {
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: { get: (name) => String(name).toLowerCase() === "content-type" ? "application/x-git-upload-pack-advertisement" : "" },
        arrayBuffer: () => Promise.resolve(latin1Buffer(advertisement))
      });
    }
    return Promise.reject(new Error("unexpected URL " + url));
  };
  const live = await api.resolveBrowser({ force: true });
  assert(live.sha === shaB && live.via === "anonymous git smart-HTTP fallback", "browser resolver exercises the real 403-to-ArrayBuffer fallback contract");
  assert(calls.length === 2 && calls[0].url === api.mainApi && calls[1].url === api.mainGitAdvertisement, "browser resolver calls only the fixed API and fixed proxy endpoints in order");
  assert(calls.every((call) => call.options.credentials === "omit"), "every resolver request omits credentials");
  assert(calls.every((call) => call.options.redirect === "error"), "resolver refuses redirects away from either fixed endpoint");
  assert(calls[1].options.headers.Accept === "application/x-git-upload-pack-advertisement", "git fallback requests the exact advertisement MIME");

  const beforeCache = calls.length;
  const cached = await api.resolveBrowser();
  assert(cached.sha === shaB && cached.cached === true && calls.length === beforeCache, "fresh session cache reuses the exact observed SHA without another request");

  storage.setItem("commons-exact-main-v1", JSON.stringify({
    sha: " " + shaA,
    via: "poisoned cache",
    observedAt: new Date().toISOString(),
    savedAt: Date.now()
  }));
  const beforePoisonedCache = calls.length;
  const afterPoisonedCache = await api.resolveBrowser();
  assert(afterPoisonedCache.sha === shaB && !afterPoisonedCache.cached && calls.length === beforePoisonedCache + 2, "whitespace-wrapped cached SHA is discarded and remeasured");

  let aborts = 0;
  class CountingAbortController {
    constructor() { this.signal = {}; }
    abort() { aborts += 1; }
  }
  sandbox.AbortController = CountingAbortController;
  sandbox.fetch = function (url) {
    if (String(url) === api.mainApi) {
      return Promise.resolve({ ok: true, status: 200, json: () => new Promise(() => {}) });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      headers: { get: () => "application/x-git-upload-pack-advertisement" },
      arrayBuffer: () => new Promise(() => {})
    });
  };
  let bodyDeadline = false;
  try {
    await api.resolveBrowser({ force: true, timeoutMs: 10 });
  } catch (error) {
    bodyDeadline = /GitHub API:.*timed out.*git smart-HTTP:.*timed out/.test(String(error && error.message));
  }
  assert(bodyDeadline && aborts === 2, "API and git body decoders remain inside aborting deadlines after response headers arrive");

  assert(src.includes("timed out after") && src.includes("controller.abort()"), "both network roads are bounded by an aborting deadline");
  assert(!/Authorization/.test(src) && !/credentials\s*:\s*["']include/.test(src), "shared resolver contains no auth header or credentialed read");
  assert(api.mainGitAdvertisement === "https://cors.isomorphic-git.org/github.com/woahwhattheheck/commons.git/info/refs?service=git-upload-pack", "proxy target is fixed to the verified anonymous git path");
  console.log("EXACT_MAIN_OK");
}

run().catch((error) => {
  console.error(error && error.stack || error);
  process.exit(1);
});
