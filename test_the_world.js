// THE WORLD exact-SHA snapshot comparison tests. No network calls.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { webcrypto } = require("crypto");

function assert(condition, message) {
  if (!condition) {
    console.error("FAIL " + message);
    process.exit(1);
  }
  console.log("PASS " + message);
}

const src = fs.readFileSync(path.join(__dirname, "the-world.js"), "utf8");
const html = fs.readFileSync(path.join(__dirname, "the-world.html"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "the-world.css"), "utf8");
const sandbox = {
  URL,
  URLSearchParams,
  Uint8Array,
  ArrayBuffer,
  Promise,
  crypto: webcrypto,
  setTimeout,
  clearTimeout,
  document: undefined,
  location: undefined,
  COMMONS_EXACT_MAIN: {
    isSha(value) { return /^[0-9a-fA-F]{40}$/.test(String(value || "")); },
    resolveBrowser() { throw new Error("pure tests must not resolve main"); },
  },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.runInNewContext(src, sandbox);
const W = sandbox.COMMONS_THE_WORLD;

assert(W && W.compare && W.parseQuery, "pure THE WORLD API is exported");
assert(W.MAX_BYTES === 512 * 1024, "each exact raw response is capped at 512 KiB");

const BASE = "1111111111111111111111111111111111111111";
const TARGET = "AaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAa";
const parsed = W.parseQuery(`?base=${BASE}&target=${TARGET}&path=p%2Freceipt-20260824-01.md`);
assert(parsed.ok && parsed.base === BASE && parsed.target === TARGET.toLowerCase(), "query requires and canonicalizes two full SHAs");
assert(parsed.path === "p/receipt-20260824-01.md", "query round-trips one repo-relative path");
assert(!W.parseQuery(`?base=main&target=${TARGET}&path=DIRECTIVES.md`).ok, "moving main is not accepted as an exact SHA");
assert(!W.parseQuery(`?base=${BASE.slice(0, 12)}&target=${TARGET}&path=DIRECTIVES.md`).ok, "abbreviated SHAs fail closed");
assert(!W.parseQuery(`?base=${BASE}&base=${TARGET}&target=${TARGET}&path=DIRECTIVES.md`).ok, "duplicate SHA parameters fail closed");
assert(!W.parseQuery(`?base=%20${BASE}&target=${TARGET}&path=DIRECTIVES.md`).ok, "SHA whitespace fails closed instead of selecting a different address");
assert(!W.parseQuery(`?base=${BASE}&target=${TARGET}&path=DIRECTIVES.md%20`).ok, "path whitespace fails closed instead of selecting a different file");
assert(W.safePath("../DIRECTIVES.md") === "" && W.safePath("p/a b.md") === "", "escaping and ambiguous paths are rejected");
assert(W.safePath(" DIRECTIVES.md") === "" && W.safePath("DIRECTIVES.md ") === "", "safePath never trims into a different exact path");
assert(W.safePath("ground/HEAD.md") === "ground/HEAD.md", "ordinary nested repo paths remain open");

const raw = W.rawUrl(BASE, "ground/HEAD.md");
assert(raw === `https://raw.githubusercontent.com/woahwhattheheck/commons/${BASE}/ground/HEAD.md`, "raw evidence is pinned to the complete SHA");
assert(!raw.includes("/main/"), "raw evidence never substitutes moving main");
const permalink = W.permalink(BASE, TARGET, "ground/HEAD.md", "https://example.test/commons/the-world.html?old=1#frag");
assert(permalink === `https://example.test/commons/the-world.html?base=${BASE}&target=${TARGET.toLowerCase()}&path=ground%2FHEAD.md`, "permalink contains only exact two-SHA-plus-path state");
const evidence = W.evidence(BASE, TARGET, "ground/HEAD.md");
assert(evidence.baseCommit.endsWith(`/commit/${BASE}`) && evidence.targetCommit.endsWith(`/commit/${TARGET.toLowerCase()}`), "both exact commit evidence links are exposed");
assert(evidence.compare.endsWith(`/compare/${BASE}...${TARGET.toLowerCase()}`), "exact GitHub compare evidence link is exposed");

const equal = W.classifySides(
  { state: "PRESENT", bytes: new Uint8Array([0, 1, 2]), size: 3 },
  { state: "PRESENT", bytes: new Uint8Array([0, 1, 2]), size: 3 },
);
assert(equal.state === "IDENTICAL" && equal.first === null, "byte-equal snapshots are IDENTICAL");
const changed = W.classifySides(
  { state: "PRESENT", bytes: new Uint8Array([0, 1, 2]), size: 3 },
  { state: "PRESENT", bytes: new Uint8Array([0, 9, 2]), size: 3 },
);
assert(changed.state === "CHANGED" && changed.first.offset === 1 && changed.first.baseByte === 1 && changed.first.targetByte === 9, "CHANGED reports the first differing zero-based byte");
const lengthChanged = W.classifySides(
  { state: "PRESENT", bytes: new Uint8Array([7]), size: 1 },
  { state: "PRESENT", bytes: new Uint8Array([7, 8]), size: 2 },
);
assert(lengthChanged.state === "CHANGED" && lengthChanged.first.offset === 1 && lengthChanged.first.baseByte === null, "length-only change reports EOF at the first differing byte");
assert(W.classifySides({ state: "MISSING" }, { state: "PRESENT", bytes: new Uint8Array() }).state === "MISSING", "one exact HTTP 404 classifies as MISSING");
assert(W.classifySides({ state: "UNKNOWN" }, { state: "MISSING" }).state === "UNKNOWN", "transport uncertainty outranks a missing-side observation");

function bytesResponse(status, values, contentLength) {
  const bytes = new Uint8Array(values || []);
  return {
    ok: status === 200,
    status,
    headers: { get(name) { return String(name).toLowerCase() === "content-length" && contentLength != null ? String(contentLength) : null; } },
    arrayBuffer() { return Promise.resolve(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)); },
  };
}

(async function run() {
  const emptyDigest = await W.digestHex(new Uint8Array(), webcrypto);
  assert(emptyDigest === "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "SHA-256 digest covers an exact empty byte stream");

  let request = null;
  const present = await W.fetchSnapshot(BASE, "DIRECTIVES.md", {
    crypto: webcrypto,
    fetch(url, options) {
      request = { url, options };
      return Promise.resolve(bytesResponse(200, [65, 0, 66], 3));
    },
  });
  assert(present.state === "PRESENT" && present.size === 3 && present.digest.length === 64, "HTTP 200 returns measured size and SHA-256");
  assert(request.url.includes(`/${BASE}/DIRECTIVES.md`), "fetch uses the requested exact SHA");
  assert(request.options.cache === "no-store" && request.options.credentials === "omit", "raw fetch is fresh and anonymous");
  assert(request.options.redirect === "error", "raw fetch refuses redirects instead of following a different object");
  assert(!Object.keys(request.options.headers).some((name) => /authorization/i.test(name)), "raw fetch carries no authorization header");

  const redirected = await W.fetchSnapshot(BASE, "DIRECTIVES.md", {
    crypto: webcrypto,
    fetch(url) {
      const response = bytesResponse(200, [1]);
      response.url = url + "?different=1";
      return Promise.resolve(response);
    },
  });
  assert(redirected.state === "UNKNOWN" && /response URL changed/.test(redirected.reason), "changed final response URL fails closed before PRESENT classification");

  const redirected404 = await W.fetchSnapshot(BASE, "absent.txt", {
    crypto: webcrypto,
    fetch(url) {
      const response = bytesResponse(404);
      response.url = url.replace(`/${BASE}/`, `/${TARGET.toLowerCase()}/`);
      return Promise.resolve(response);
    },
  });
  assert(redirected404.state === "UNKNOWN", "changed final response URL also cannot become MISSING");

  const missing = await W.fetchSnapshot(BASE, "absent.txt", {
    crypto: webcrypto,
    fetch: () => Promise.resolve(bytesResponse(404)),
  });
  assert(missing.state === "MISSING" && missing.httpStatus === 404, "only exact HTTP 404 produces the MISSING side state");

  const serverFailure = await W.fetchSnapshot(BASE, "DIRECTIVES.md", {
    crypto: webcrypto,
    fetch: () => Promise.resolve(bytesResponse(503)),
  });
  assert(serverFailure.state === "UNKNOWN" && serverFailure.httpStatus === 503, "non-404 HTTP failure remains UNKNOWN");

  const networkFailure = await W.fetchSnapshot(BASE, "DIRECTIVES.md", {
    crypto: webcrypto,
    fetch: () => Promise.reject(new Error("offline")),
  });
  assert(networkFailure.state === "UNKNOWN" && /offline/.test(networkFailure.reason), "network failure remains UNKNOWN");

  let oversizedBodyRead = false;
  const oversized = await W.fetchSnapshot(BASE, "board.md", {
    crypto: webcrypto,
    fetch: () => Promise.resolve({
      ok: true,
      status: 200,
      headers: { get: () => String(W.MAX_BYTES + 1) },
      arrayBuffer() { oversizedBodyRead = true; return Promise.resolve(new ArrayBuffer(0)); },
    }),
  });
  assert(oversized.state === "UNKNOWN" && /512 KiB/.test(oversized.reason), "response over the byte ceiling fails closed as UNKNOWN");
  assert(!oversizedBodyRead, "declared oversized body is not buffered");

  let invalidFetches = 0;
  const invalid = await W.fetchSnapshot("main", "DIRECTIVES.md", {
    crypto: webcrypto,
    fetch: () => { invalidFetches += 1; return Promise.resolve(bytesResponse(200)); },
  });
  assert(invalid.state === "UNKNOWN" && invalidFetches === 0, "invalid SHA makes no network request");

  const compared = await W.compare(BASE, TARGET, "DIRECTIVES.md", {
    crypto: webcrypto,
    now: () => "2026-08-25T02:34:56.000Z",
    fetch(url) {
      if (url.includes(`/${BASE}/`)) return Promise.resolve(bytesResponse(200, [1, 2, 3]));
      if (url.includes(`/${TARGET.toLowerCase()}/`)) return Promise.resolve(bytesResponse(200, [1, 2, 4]));
      throw new Error("unexpected URL " + url);
    },
  });
  assert(compared.state === "CHANGED" && compared.first.offset === 2, "two exact fetches classify a real byte change");
  assert(compared.measuredAt === "2026-08-25T02:34:56.000Z", "comparison completion supplies the receipt measurement timestamp");
  const exactUrl = W.permalink(BASE, TARGET, "DIRECTIVES.md", "https://example.test/commons/the-world.html");
  const receipt = W.receipt({ base: BASE, target: TARGET.toLowerCase(), path: "DIRECTIVES.md" }, compared, exactUrl);
  assert(receipt.includes(`base: ${BASE}`) && receipt.includes(`target: ${TARGET.toLowerCase()}`), "portable receipt names both complete SHAs");
  assert(receipt.includes("measured_at: 2026-08-25T02:34:56.000Z"), "portable receipt includes the comparison completion timestamp");
  assert(receipt.includes("base_reason: exact raw bytes measured") && receipt.includes("target_reason: exact raw bytes measured"), "portable receipt preserves each side's bounded measurement reason");
  assert(/first_differing_byte: 2 \(0x2\)/.test(receipt) && receipt.includes("scope: exact raw observations only"), "portable receipt carries byte offset and bounded epistemic scope");
  const identicalReceipt = W.receipt({ base: BASE, target: BASE, path: "DIRECTIVES.md" }, equal, exactUrl);
  assert(identicalReceipt.includes("first_differing_byte: NONE"), "NONE is reserved for a fully measured IDENTICAL byte comparison");
  const missingReceipt = W.receipt({ base: BASE, target: TARGET.toLowerCase(), path: "absent.txt" }, {
    state: "MISSING",
    measuredAt: "2026-08-25T02:34:57.000Z",
    base: missing,
    target: present,
    first: null,
  }, exactUrl);
  assert(missingReceipt.includes("first_differing_byte: UNMEASURED"), "MISSING never claims that no differing byte exists");
  const unknownReceipt = W.receipt({ base: BASE, target: TARGET.toLowerCase(), path: "DIRECTIVES.md" }, {
    state: "UNKNOWN",
    measuredAt: "2026-08-25T02:34:58.000Z",
    base: serverFailure,
    target: present,
    first: null,
  }, exactUrl);
  assert(unknownReceipt.includes("first_differing_byte: UNMEASURED"), "UNKNOWN never claims that no differing byte exists");

  const streamChunks = [new Uint8Array(W.MAX_BYTES), new Uint8Array([1])];
  let cancelled = false;
  const streaming = await W.readCapped({
    headers: { get: () => null },
    body: {
      getReader() {
        let i = 0;
        return {
          read() { return Promise.resolve(i < streamChunks.length ? { done: false, value: streamChunks[i++] } : { done: true }); },
          cancel() { cancelled = true; return Promise.resolve(); },
        };
      },
    },
  }, W.MAX_BYTES);
  assert(streaming.tooLarge && cancelled, "streaming body is cancelled as soon as it crosses 512 KiB");

  assert(html.indexOf("exact-main.js") < html.indexOf("the-world.js"), "shared exact-main resolver loads before THE WORLD");
  assert(/name="base"/.test(html) && /name="target"/.test(html) && /name="path"/.test(html), "HTML form exposes shareable base, target, and path fields");
  assert(/role="status"[^>]*aria-live="polite"/.test(html), "resolver and comparison results use an accessible live status");
  assert(/Possessing the link is sufficient authorization[\s\S]*No login or token/i.test(html), "open no-auth law is explicit");
  assert(/does not by itself validate that arbitrary SHA/i.test(html), "MISSING semantics do not overclaim arbitrary commit validity");
  assert(/min-height:\s*44px/.test(css) && /@media \(max-width:\s*48rem\)/.test(css), "mobile controls meet 44px target and stack at a bounded breakpoint");
  assert(!/\.innerHTML\s*=/.test(src), "all measured content is rendered without innerHTML injection");
  assert(/credentials:\s*"omit"/.test(src) && !/Authorization/.test(src), "source contract is anonymous and contains no authorization path");
  assert(!/localStorage|sessionStorage/.test(src), "exact comparison state lives in its URL, not hidden browser storage");
  console.log("THE_WORLD_OK");
})().catch((error) => {
  console.error(error && error.stack || error);
  process.exit(1);
});
