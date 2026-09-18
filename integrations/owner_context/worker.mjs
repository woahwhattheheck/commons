// Cloudflare Worker adapter for the owner-context display host.
// Display only. Never a gate. Never writes a raw IP into a response.
const PEPPER = "commons-owner-v1";
const KIND = "owner-context";
const HASH_RE = /^[0-9a-f]{64}$/;
const IPV4 = /\b(?:\d{1,3}\.){3}\d{1,3}\b/;
const IPV6 = /\b[0-9a-fA-F:]+:[0-9a-fA-F:]+\b/;

function cors() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD",
    "Access-Control-Allow-Headers": "*",
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
    "X-Commons-Owner-Context": "display-only"
  };
}

function normalizeIp(raw) {
  let s = String(raw || "").trim();
  if (s.charAt(0) === "[" && s.charAt(s.length - 1) === "]") s = s.slice(1, -1);
  const pct = s.indexOf("%");
  if (pct !== -1) s = s.slice(0, pct);
  if (s.indexOf(":") !== -1) s = s.toLowerCase();
  return s;
}

function looksLikeIp(s) {
  s = String(s || "");
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(s)) return true;
  if (s.indexOf(":") !== -1 && /^[0-9a-f:]+$/.test(s)) return true;
  return false;
}

function viaOf(value) {
  const v = String(value || "");
  return v === "pc" || v === "phone" ? v : "";
}

async function sha256hex(s) {
  const bytes = new TextEncoder().encode(s);
  const buf = await crypto.subtle.digest("SHA-256", bytes);
  const b = new Uint8Array(buf);
  let out = "";
  for (let i = 0; i < b.length; i++) out += (b[i] < 16 ? "0" : "") + b[i].toString(16);
  return out;
}

function payload(extra) {
  const body = Object.assign({
    k: KIND,
    v: 1,
    display_only: true,
    authority: false,
    gate: false,
    claim_still: true,
    available: false,
    pepper_version: "v1",
    sha256: "",
    slot: "",
    via_hint: "",
    host: "cloudflare",
    retention_seconds: 21600,
    reason: "",
    fresh: true
  }, extra || {});
  const text = JSON.stringify(body);
  if (IPV4.test(text) || IPV6.test(text)) {
    return JSON.stringify({
      k: KIND,
      display_only: true,
      authority: false,
      gate: false,
      available: false,
      reason: "refused"
    });
  }
  return text;
}

function extractPeer(request) {
  const cf = request.headers.get("CF-Connecting-IP") || "";
  const real = request.headers.get("X-Real-IP") || "";
  const forwarded = (request.headers.get("X-Forwarded-For") || "").split(",")[0];
  const ip = normalizeIp(cf || real || forwarded);
  return looksLikeIp(ip) ? ip : "";
}

async function loadSlots(url) {
  try {
    const resp = await fetch(url, { cf: { cacheTtl: 60 } });
    if (!resp.ok) return { pc: "", phone: "" };
    const spec = await resp.json();
    const slots = (spec && spec.slots) || {};
    const pc = slots.pc && HASH_RE.test(String(slots.pc.sha256 || "").toLowerCase())
      ? String(slots.pc.sha256).toLowerCase() : "";
    const phone = slots.phone && HASH_RE.test(String(slots.phone.sha256 || "").toLowerCase())
      ? String(slots.phone.sha256).toLowerCase() : "";
    return { pc, phone };
  } catch (e) {
    return { pc: "", phone: "" };
  }
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors() });
    }
    const url = new URL(request.url);
    if (url.pathname.endsWith("/health")) {
      return new Response(payload({ ok: true, available: false }), { status: 200, headers: cors() });
    }
    let viaHint = viaOf(url.searchParams.get("via"));
    if (request.method === "POST") {
      try {
        const obj = await request.json();
        viaHint = viaHint || viaOf(obj && obj.via);
      } catch (e) {}
    }
    const ip = extractPeer(request);
    if (!ip) {
      return new Response(payload({ reason: "no-peer", via_hint: viaHint }), { status: 200, headers: cors() });
    }
    const digest = await sha256hex(PEPPER + "\n" + ip);
    const slots = await loadSlots(env && env.OWNER_JSON_URL
      ? env.OWNER_JSON_URL
      : "https://woahwhattheheck.github.io/commons/owner.json");
    let slot = "";
    if (slots.pc && digest === slots.pc) slot = "pc";
    else if (slots.phone && digest === slots.phone) slot = "phone";
    return new Response(payload({
      available: true,
      sha256: digest,
      slot,
      via_hint: viaHint
    }), { status: 200, headers: cors() });
  }
};
