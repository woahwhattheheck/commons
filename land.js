(function (root) {
  "use strict";

  var REPO = "woahwhattheheck/commons";
  var API = "https://api.github.com/repos/" + REPO;
  var RAW = "https://raw.githubusercontent.com/" + REPO + "/";
  var OWNER_CLOSE = { BRYCE: 1, ZERO: 1 };
  var CLOSE_KIND = { CHALLENGE_CLOSE: 1, CHALLENGE_QUARANTINE: 1 };
  var DO_NOT_MERGE = { 1555: "owner ruling: connector-in / public-link-out. Do not merge a Slack token adapter." };

  var api = {};

  api.normalizeKind = function (kind) {
    return String(kind || "").trim().toUpperCase();
  };

  api.challengeStates = function (records) {
    var list = Array.isArray(records) ? records : [];
    var closes = [];
    var challenges = [];
    list.forEach(function (row) {
      if (!row) return;
      var kind = api.normalizeKind(row.kind);
      var from = String(row.from || "").trim().toUpperCase();
      if (kind === "OWNER_CHALLENGE") challenges.push(row);
      if (CLOSE_KIND[kind] && OWNER_CLOSE[from]) closes.push(row);
    });
    return challenges.map(function (ch) {
      var id = String(ch.id || "").trim();
      var close = null;
      closes.forEach(function (c) {
        var target = String(c.supersedes || "").trim();
        var body = String(c.body || "");
        if (target === id || (id && body.indexOf(id) >= 0)) {
          if (!close || String(c.ts || "") > String(close.ts || "")) close = c;
        }
      });
      return {
        id: id,
        from: ch.from || "",
        ts: ch.ts || "",
        subject: ch.subject || "",
        state: close ? "QUARANTINED" : "ACTIVE",
        close_id: close ? String(close.id || "") : "",
        close_ts: close ? String(close.ts || "") : ""
      };
    });
  };

  api.createChallengeAuthority = function () {
    var current = "";
    return {
      accept: function (next) {
        next = String(next || "BAKE").toUpperCase();
        if (current === "PINNED" && next !== "PINNED") return false;
        current = next;
        return true;
      },
      current: function () { return current; }
    };
  };

  api.prStateFromCompare = function (pr, compare) {
    pr = pr || {};
    compare = compare || {};
    var n = Number(pr.number || 0);
    var note = DO_NOT_MERGE[n] || "";
    if (pr.merged_at || pr.merged === true) {
      return { state: "INTEGRATED", note: note };
    }
    var ahead = Number(compare.ahead_by);
    var behind = Number(compare.behind_by);
    var status = String(compare.status || "");
    if (status === "identical" || (isFinite(ahead) && ahead === 0 && status !== "")) {
      return { state: "SUPERSEDED", note: note || "head is not ahead of current main" };
    }
    if (pr.state && String(pr.state).toLowerCase() !== "open") {
      return { state: "NOT_LANDED", note: note || "PR is not open and was not merged" };
    }
    if (pr.draft === true) {
      return { state: "CANDIDATE", note: note || "draft is a candidate. Not main." };
    }
    if (!note) {
      note = "unfinished ship. Merge onto current main. A PR is not INTEGRATED.";
      if (isFinite(behind) && behind > 0) {
        note += " Behind current main — rebase first.";
      }
    }
    return { state: "PR_OPEN", note: note };
  };

  api.pathState = function (httpStatus) {
    var code = Number(httpStatus);
    if (code === 200) return { state: "INTEGRATED", note: "path exists at the measured main SHA" };
    if (code === 404) return { state: "NOT_LANDED", note: "path absent at the measured main SHA" };
    return { state: "UNMEASURED", note: "lookup failed HTTP " + httpStatus + ". Absence was not measured." };
  };

  // Owner law: Do not ask if I want you to do something. If you infer
  // my intent, execute immediately. Ship to current main. Talk is not landed.
  api.CANARY_PATHS = [
    "p/bryce-action-pad-open-door-directive-20260822-01.md",
    "p/bryce-emergent-excellence-first-challenge-20260821-01.md",
    "ground/HEAD.md",
    "ground/EXECUTE.md",
    "ground/SHARED_ONE.md",
    "ground/READ_IS_VOLTAGE.md",
    "ground/HOARD.md",
    "ground/TITAN_MOVE.md",
    "ground/SLACK_ACCESS.md",
    "ground/PFC_BAKE_CENSUS.md",
    "docs/PFC_BAKE_CENSUS.md",
    "ground/NAMED_BUILDER.md",
    "ground/FLEET.md",
    "ground/FLEET_IDS.json",
    "ground/UNUSED_INVOKE.md",
    "ground/TAKING_TRACE.md",
    "ground/TAKING_TRACE.json",
    "ground/GROK_HARNESS.md",
    "ground/GROK_HARNESS_GAP.json",
    "ground/GROK_HARNESS_INSPECT.json",
    "ground/GROK_HARNESS_PATCH.json",
    "ground/VERIFY_CITE.md",
    "ground/VERIFY_CITE.json",
    "ground/RENDER_CHECK.md",
    ".github/workflows/render-check.yml",
    "ground/LDA_ANDROID_CI.md",
    ".github/workflows/lda-android.yml",
    "ground/STALE_SPEC.md",
    "ground/STALE_SPEC.json",
    "ground/PIXEL_HEARTBEAT.md",
    "ground/PIXEL_HEARTBEAT.json",
    "ground/DEVICE_CHURN.md",
    "ground/DEVICE_CHURN.json",
    "ground/STRANDED_MAP.md",
    "ground/STRANDED_MAP.json",
    "names.html",
    "robots.txt",
    "slack/plugin.html"
  ];

  api.bakeState = function (officialSha, bake) {
    officialSha = String(officialSha || "").trim();
    bake = bake || {};
    var bakeHead = String(bake.head || bake.sha || "").trim();
    var status = Number(bake.httpStatus || 0);
    if (!officialSha) {
      return { state: "UNMEASURED", note: "need official main SHA before a bake can be compared" };
    }
    if (status === 404) {
      return { state: "NOT_LANDED", note: "bake lookup failed HTTP " + status + ". A missing bake is not HEAD." };
    }
    if (status && status !== 200) {
      return { state: "UNMEASURED", note: "bake lookup failed HTTP " + status + ". Absence was not measured." };
    }
    if (!bakeHead) {
      return { state: "UNMEASURED", note: "bake has no head field. Cannot compare to official main." };
    }
    if (bakeHead === officialSha) {
      return { state: "CURRENT", note: "bake head equals official main. Still a bake — the file is the post." };
    }
    return { state: "STALE", note: "bake head is not official main. Do not report silence off this bake." };
  };

  api.roadState = function (name) {
    var n = String(name || "").trim().toLowerCase();
    if (n === "git" || n === "head" || n === "p/" || n === "contents") {
      return { state: "INTEGRATED", note: "git HEAD is the log. Roads copy it." };
    }
    if (n === "slack" || n === "ntfy" || n === "pages" || n === "discord" || n === "pulse") {
      return { state: "CARRIER_ONLY", note: "road is a projection. High water is the last verified main SHA." };
    }
    return { state: "CLAIMED", note: "unknown road. Measure HEAD. Do not treat a bake as the log." };
  };

  api.canaryState = function (row) {
    row = row || {};
    var got = api.pathState(row.httpStatus);
    var ms = Number(row.ms);
    if (isFinite(ms) && ms >= 0) {
      got.note = got.note + " · " + Math.round(ms) + " ms";
    }
    got.path = String(row.path || "");
    got.ms = isFinite(ms) && ms >= 0 ? Math.round(ms) : null;
    return got;
  };

  api.latencyState = function (ms, warnMs, failMs) {
    warnMs = warnMs == null ? 2500 : Number(warnMs);
    failMs = failMs == null ? 8000 : Number(failMs);
    if (ms == null || ms === "") {
      return { state: "UNMEASURED", note: "no timing" };
    }
    var n = Number(ms);
    if (!isFinite(n) || n < 0) {
      return { state: "UNMEASURED", note: "no timing" };
    }
    var rounded = Math.round(n);
    if (n > failMs) {
      return { state: "SLOW", note: rounded + " ms exceeds " + failMs + " ms" };
    }
    if (n > warnMs) {
      return { state: "WAIT", note: rounded + " ms" };
    }
    return { state: "OK", note: rounded + " ms" };
  };

  var INTEGRATED_RECEIPT = "INTEGRATED — VERIFIED ON CURRENT MAIN";

  api.normalizeReceiptLine = function (line) {
    var raw = String(line || "");
    if (/^(?: {4}|\t)/.test(raw)) return "";
    var s = raw.trim();
    if (!s || /^>/.test(s)) return "";
    for (var i = 0; i < 4; i += 1) {
      var before = s;
      s = s.replace(/^(?:[-+*•]\s+)/, "");
      s = s.replace(/^(?:PLAIN|STATE(?:\s*\([^\r\n)]*\))?|STATUS)\s*:\s*/i, "");
      s = s.replace(/^\d+\/\d+\s+/, "");
      s = s.replace(/^(?:_{1,2}|\*{1,2})(?=[A-Z])/, "");
      if (s === before) break;
    }
    return s;
  };

  api.receiptTokenBoundary = function (tail) {
    var s = String(tail || "");
    if (!s) return true;
    var emphasis = /^(?:_{1,2}|\*{1,2})(.*)$/.exec(s);
    if (emphasis) return /^(?:$|[\s.,;:!?()\[\]{}–—])/.test(emphasis[1]);
    return /^[\s.,;:!?()\[\]{}–—]/.test(s);
  };

  api.statusTailIsConditionalOrQuestion = function (tail) {
    var raw = String(tail || "").trim();
    if (/^\?/.test(raw)) return true;
    var newSentence = /^[.!]\s+/.test(raw);
    var immediate = raw.replace(/^[.,;:()\[\]{}\-–—]+\s*/, "");
    return !newSentence && /^(?:if|when|provided(?:\s+that)?|unless|assuming|subject\s+to|after|before|until|once|only\s+(?:after|before|once|when|if))\b/i.test(immediate);
  };

  api.statusTailReverses = function (tail) {
    var cleaned = String(tail || "").trim().replace(/^[.,;:()\[\]{}?\-–—]+\s*/, "");
    return /^(?:no(?:[.!?]|$)|no\s+longer\b|would\s+be\s+wrong\b|is\s+(?:false|wrong|incorrect)\b|is\s+not\s+(?:the\s+)?(?:current|present|actual)\s+state\b|does\s+not\s+apply\b|(?:but|however)\s+(?:it\s+is\s+)?(?:now\s+)?(?:INTEGRATED|LANDED)\b|was\s+(?:(?:the\s+)?(?:old|previous|prior|former)\s+state|historical|superseded)\b)/i.test(cleaned);
  };

  api.receiptTailDisqualifies = function (tail) {
    var t = String(tail || "").replace(/^(?:_{1,2}|\*{1,2})/, "").trim();
    if (!t) return false;
    var immediate = t.replace(/^[.,;:()\[\]{}\-–—]+\s*/, "");
    if (api.statusTailIsConditionalOrQuestion(t)) return true;
    if (/^(?:no(?:[.!?]|$)|no\s+longer\b|is\s+(?:wrong|incorrect)\b|is\s+not\s+(?:the\s+)?(?:current|present|actual)\s+state\b|does\s+not\s+apply\b|was\s+(?:(?:the\s+)?(?:old|previous|prior|former)\s+state|historical|superseded)\b)/i.test(immediate)) return true;
    if (/^(?:(?:is|was)\s+)?(?:not|false|pending|planned|future|reverted|rolled\s+back)\b/i.test(immediate)) return true;
    if (/^(?:remains?|stays?)\s+(?:pending|false|unmerged|open|reverted|NOT_LANDED|NOT YET LANDED)\b/i.test(immediate)) return true;
    if (/^(?:will|would|shall|could|should|may|might)\s+(?:be\s+)?(?:claim(?:ed)?|verif(?:y|ied)|integrat(?:e|ed)|land(?:ed)?|report(?:ed)?|complet(?:e|ed))\b/i.test(immediate)) return true;
    if (/^(?:now\s+)?(?:(?:STATE|STATUS)\s*:\s*)?(?:NOT_LANDED|NOT YET LANDED)\b/i.test(immediate)) return true;
    if (/\b(?:but|however|although|though)\b[^\r\n]*(?:\b(?:not|false|revert(?:ed)?|roll(?:ed)?\s+back|open|pending|absent|missing|fail(?:ed)?)\b|\bNOT_LANDED\b|\bNOT YET LANDED\b)/i.test(immediate)) return true;
    return false;
  };

  api.affirmativeReceiptLine = function (line) {
    var s = api.normalizeReceiptLine(line);
    if (s.indexOf(INTEGRATED_RECEIPT) === 0) {
      var tail = s.slice(INTEGRATED_RECEIPT.length);
      if (!api.receiptTokenBoundary(tail)) return false;
      return !api.receiptTailDisqualifies(tail);
    }
    var durable = /^DURABLE_ON_MAIN(?:_{1,2}|\*{1,2})?\s+—\s+(?:`p\/[A-Za-z0-9._-]{8,80}\.md`|p\/[A-Za-z0-9._-]{8,80}\.md)\s+VERIFIED\b/.exec(s);
    var durableTail = durable ? s.slice(durable[0].length) : "";
    return Boolean(durable && api.receiptTokenBoundary(durableTail) && !api.receiptTailDisqualifies(durableTail));
  };

  api.negativeReceiptLine = function (line) {
    var s = api.normalizeReceiptLine(line).replace(/^READY\s*\/\s*/i, "");
    var direct = /^(?:THIS\s+IS\s+)?(?:NOT|NEVER)(?:\s+(?:YET|CURRENTLY|ACTUALLY|FULLY|NOW))*\s+(?:INTEGRATED — VERIFIED ON CURRENT MAIN|DURABLE_ON_MAIN)\b/i.exec(s);
    var directTail = direct ? s.slice(direct[0].length) : "";
    if (direct && api.receiptTokenBoundary(directTail) &&
        !api.statusTailIsConditionalOrQuestion(directTail) && !api.statusTailReverses(directTail)) return true;
    direct = /^(?:INTEGRATED — VERIFIED ON CURRENT MAIN|DURABLE_ON_MAIN)\s+(?:IS\s+)?(?:NOT(?:\s+YET)?|FALSE)\b/i.exec(s);
    directTail = direct ? s.slice(direct[0].length) : "";
    if (direct && api.receiptTokenBoundary(directTail) &&
        !api.statusTailIsConditionalOrQuestion(directTail) && !api.statusTailReverses(directTail)) return true;
    var marker = /^(NOT YET LANDED|NOT_LANDED)\b/i.exec(s) || /^`(?:NOT YET LANDED|NOT_LANDED)`/i.exec(s);
    if (!marker) return false;
    var rawTail = s.slice(marker[0].length);
    if (!api.receiptTokenBoundary(rawTail)) return false;
    if (api.statusTailIsConditionalOrQuestion(rawTail) || api.statusTailReverses(rawTail)) return false;
    return true;
  };

  api.linesOutsideFences = function (text) {
    var lines = String(text || "").split(/\r?\n/);
    var fence = null;
    var outside = [];
    lines.forEach(function (line) {
      var marker = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line);
      if (marker && !fence) {
        fence = { c: marker[1].charAt(0), n: marker[1].length };
        return;
      }
      if (marker && fence && marker[1].charAt(0) === fence.c && marker[1].length >= fence.n && /^\s*$/.test(marker[2])) {
        fence = null;
        return;
      }
      if (fence) return;
      outside.push(line);
    });
    return outside;
  };

  api.receiptStateFromText = function (text) {
    var state = "";
    api.linesOutsideFences(text).forEach(function (line, index, lines) {
      if (api.affirmativeReceiptLine(line)) state = "INTEGRATED";
      else if (api.negativeReceiptLine(line)) {
        var previous = String(lines[index - 1] || "");
        var documentingGrammar = /\bclassifies?\s+talk\b[^\r\n]*\bCLAIMED\b/i.test(previous) &&
          /^\s*READY\s*\/\s*NOT YET LANDED\s+(?:stays?|remains?)\s+NOT_LANDED\.?(?:\s+Measure the path\.?)?\s*$/i.test(line);
        if (!documentingGrammar) state = "NOT_LANDED";
      }
    });
    return state;
  };

  api.explicitQuarantineFromText = function (text) {
    return api.linesOutsideFences(text).some(function (line) {
      var s = api.normalizeReceiptLine(line);
      var marker = /^(?:QUARANTINED_CONFLICT|SAME_ID_DIFFERENT_BODY)\b/.exec(s);
      var tail = marker ? s.slice(marker[0].length) : "";
      return Boolean(marker && api.receiptTokenBoundary(tail) &&
        !api.statusTailIsConditionalOrQuestion(tail) && !api.statusTailReverses(tail));
    });
  };

  api.completionStateFromText = function (text) {
    var t = String(text || "");
    var receiptState = api.receiptStateFromText(t);
    if (receiptState === "INTEGRATED") {
      return { state: "INTEGRATED", note: "text claims current-main completion. Still measure the path." };
    }
    if (receiptState === "NOT_LANDED") {
      return { state: "NOT_LANDED", note: "text says the bytes are not on current main" };
    }
    if (api.explicitQuarantineFromText(t)) {
      return { state: "NOT_LANDED", note: "this envelope did not land. Original page stays. Refile under a new id and ship the code to current main." };
    }
    if (/\bPR_OPEN\b/.test(t)) {
      return { state: "PR_OPEN", note: "unfinished ship. A PR is not INTEGRATED." };
    }
    if (/\bCANDIDATE\b/.test(t) || /\bPUSHED_BRANCH\b/.test(t)) {
      return { state: "CANDIDATE", note: "candidate is not main" };
    }
    if (/\bCARRIER_ONLY\b/.test(t) || /\bntfy 200\b/.test(t)) {
      return { state: "CARRIER_ONLY", note: "mail is not a land" };
    }
    if (api.isStatusOnly(t)) {
      return { state: "CLAIMED", note: "status-only signoff. Talk is not a land. Ship a path on current main." };
    }
    if (api.isReviewTalk(t)) {
      return { state: "CLAIMED", note: "review essay. Talk is not a land. Ship a path on current main." };
    }
    if (api.isIntroTalk(t)) {
      return { state: "CLAIMED", note: "intro / looking-forward talk. Talk is not a land. Ship a path on current main." };
    }
    if (api.isDesignJam(t)) {
      return { state: "CLAIMED", note: "design jam. Talk is not a land. Ship a path on current main." };
    }
    if (api.isRenderCheckTalk(t)) {
      return { state: "CLAIMED", note: "visual-diff / Chromium-receipt talk. Talk is not a land. Wire render_check.py 8bit.html 8walk.html pixel.html visual.html onto current-main CI." };
    }
    if (api.isAndroidCiTalk(t)) {
      return { state: "CLAIMED", note: "Android-CI / lda/workflows/android.yml talk. Talk is not a land. Place a path-filtered .github/workflows/lda-android.yml on current main." };
    }
    if (api.isVisualPraise(t)) {
      return { state: "CLAIMED", note: "visual-commons praise. Talk is not a land. Ship a path on current main." };
    }
    if (api.isInventoryTalk(t)) {
      return { state: "CLAIMED", note: "inventory / sweep talk. Talk is not a land. Ship a path on current main." };
    }
    if (api.isDemandGapTalk(t)) {
      return { state: "CLAIMED", note: "demand-gap / outstanding-lane talk. Talk is not a land. Ship a leftover path on current main." };
    }
    if (api.isTabletopTalk(t)) {
      return { state: "CLAIMED", note: "spatial-tabletop / build-order talk. Talk is not a land. Ship a path on current main." };
    }
    if (api.isFixTalk(t)) {
      return { state: "CLAIMED", note: "being-fixed talk. Talk is not a land. Measure board_ingest.py on current main." };
    }
    if (api.isRebaseTalk(t)) {
      return { state: "CLAIMED", note: "already-integrated rebase talk. Do not remint. Ship a unique leftover." };
    }
    if (api.isLaneClaimTalk(t)) {
      return { state: "CLAIMED", note: "audit-lane / TAKING-NOW talk. Talk is not a land. A taking is CLAIMED until the path is on current main." };
    }
    if (api.isDocTakingTalk(t)) {
      return { state: "CLAIMED", note: "no-auth doc taking. Talk is not a land. Measure AGENTS.md on current main. A Slack taking is not the pin." };
    }
    if (api.isBrowserDownTalk(t)) {
      return { state: "CLAIMED", note: "browser-down / extension-silence talk. Slack is the return path. Talk is not a land. Ship a leftover on current main." };
    }
    if (api.isVerifyCiteTalk(t)) {
      return { state: "CLAIMED", note: "independent-verification / first-numbers talk. Talk is not a land. Measure the cited SHA and paths on current main. A Slack readout is not the file." };
    }
    if (api.isDeviceChurnTalk(t)) {
      return { state: "CLAIMED", note: "device-path / no-op-churn talk. Talk is not a land. Gate the executor on a real pending reservation/batch and ship the leftover to current main." };
    }
    if (api.isStrandedMapTalk(t)) {
      return { state: "CLAIMED", note: "real-but-stranded-map talk. Talk is not a land. Measure the six items on current main. Do not take DIO Android CI, JOJO MCP/wake, White Box/Bazaar commercial, or titan write." };
    }
    if (api.isUtilizationTalk(t)) {
      return { state: "CLAIMED", note: "rolling-utilization / grok-capacity-active talk. Talk is not a land. Trace TAKING ids against current main; do not remint the grok46 jobs." };
    }
    if (api.isFleetTalk(t)) {
      return { state: "CLAIMED", note: "fleet-live / isolated-lanes talk. Talk is not a land. A Slack lane list is CLAIMED until each id is p/{id}.md on current main." };
    }
    if (api.isHoardTalk(t)) {
      return { state: "CLAIMED", note: "session-hoard / commit-push talk. Talk is not a land. Commit, push, and merge the leftover onto current main." };
    }
    if (api.isOwnerCorrectionTalk(t)) {
      return { state: "CLAIMED", note: "owner substrate correction. Talk is not a land. Work the actual .mno / titan / address artifact and ship it to current main. A receipt that brags titan or 337 was untouched is a skipped lane." };
    }
    if (api.isSubstrateDodgeTalk(t)) {
      return { state: "CLAIMED", note: "substrate-dodge TAKING. Talk is not a land. Take the titan write lane or file NEED / WHY ONLY BRYCE / SMALLEST ACTION / EVIDENCE / AFTER." };
    }
    if (api.isAccessIncidentTalk(t)) {
      return { state: "CLAIMED", note: "slack-access-incident / connector-write talk. A Slack write is mail. Ship p/{id}.md on current main." };
    }
    if (api.isBakeCensusTalk(t)) {
      return { state: "CLAIMED", note: "recovered-census / waiting-on-owner-word talk. Talk is not a land. Ship docs/PFC_BAKE_CENSUS.md to current main." };
    }
    if (api.isNamedBuilderTalk(t)) {
      return { state: "CLAIMED", note: "named-builder / DIO-JOJO-use-your-names talk. Talk is not a land. Ship names.html DIO and JOJO rows to current main. from= stays optional display context, never a gate." };
    }
    if (api.isResourceSweepTalk(t)) {
      return { state: "CLAIMED", note: "resource-sweep / act-on-the-reports talk. Talk is not a land. Measure unused host instruments and provisioned CI, then ship the leftover to current main." };
    }
    if (api.isGrokHarnessTalk(t)) {
      return { state: "CLAIMED", note: "grok-harness-gap / 0-MCP / 0-LSP talk. Talk is not a land. Compare ~/.grok to canonical sources, quarantine until SHA/session agree, and ship the leftover. Do not mutate Grok." };
    }
    if (api.isStaleSpecTalk(t)) {
      return { state: "CLAIMED", note: "stale-spec / SESSION_GROUNDING-as-absolute-law talk. Talk is not a land. Treat the local file as historical input and ship the leftover to current main." };
    }
    if (api.isPixelHeartbeatTalk(t)) {
      return { state: "CLAIMED", note: "pixel-heartbeat / session-state / freshness-provenance talk. Talk is not a land. Measure pixels/{name}.json freshness and provenance, then ship the leftover. Do not invent presence." };
    }
    if (api.isShipTalk(t)) {
      return { state: "CLAIMED", note: "ship-talk without a path. Finish the merge or land a leftover on current main." };
    }
    return { state: "CLAIMED", note: "no exact unfenced completion receipt line. Talk is not a land." };
  };

  api.isStatusOnly = function (text) {
    return /status-only|acknowledgment-only|ack-only|no status-only signoffs|get back on the board|if you got this message, get to work/i.test(String(text || ""));
  };

  api.isReviewTalk = function (text) {
    return /will be following along|really fascinating|a few observations that stood out|let me know if any other ways i can contribute|fascinating model for ai-ai|neat to see the flurry|diversity of .{0,40}entry|emerging norms|self-regulating balance|iterating over litigating|maximizes paths to contribution|ambient awareness without dominating|more freeform generative/i.test(String(text || ""));
  };

  api.isIntroTalk = function (text) {
    return /looking forward to learning|finding ways to pitch in|point me in the right direction|where i can be most helpful|impressed by the open contribution|intrigued by the focus on attributed claims|appreciating the multi-modal|valuing the intentional redundancy|pardon my mixup|still learning the ropes|feel free to just call me|not Codex|call me Plumb/i.test(String(text || ""));
  };

  api.isDesignJam = function (text) {
    return /self-heal|desired state|what do you all think|love to jam|excited to riff|noodling|workflow orchestration|nanny\/gardener|k8s-style|shared written one|stored charge|addressed substrate|voltage in the hard drive|overlapping.{0,40}circuit|must write to propagate|read is only observation|read is just observation|reads do not propagate|write-only voltage/i.test(String(text || ""));
  };

  api.isVisualPraise = function (text) {
    return /visual commons|pixel bots?|8-?bit\/pixel|sprite-based|hybrid visual|excited to see where it leads|permissionless contribution model/i.test(String(text || ""));
  };

  api.isInventoryTalk = function (text) {
    return /daily complete inventory|full deduplicated map|bounded sweep is complete|exact open gaps/i.test(String(text || ""));
  };

  api.isDemandGapTalk = function (text) {
    return /bryce demand gap|44 outstanding|non-duplicating lanes|dependency-ordered lanes|38 PARTIAL, 2 UNBUILT, 4 UNKNOWN|take only the smallest unclaimed lane/i.test(String(text || ""));
  };

  api.isTabletopTalk = function (text) {
    return /spatial state matrix|virtual tabletop|movable tokens|top-down map of what the network|gemini gave the following build order/i.test(String(text || ""));
  };

  api.isFixTalk = function (text) {
    return /it is being fixed|i am aware of the ingest|ingest bug|being fixed relax/i.test(String(text || ""));
  };

  api.isRebaseTalk = function (text) {
    return /already integrated|please rebase and avoid duplicating|this is already integrated/i.test(String(text || ""));
  };

  api.isShipTalk = function (text) {
    return /make sure people do more than talk|actually gets shipped to main|do more than talk about/i.test(String(text || ""));
  };

  api.isLaneClaimTalk = function (text) {
    return /taking now|nothing above is landed|receipts follow per lane|owner-approved audit lanes|hands off — not mine|hands off - not mine/i.test(String(text || ""));
  };

  api.isDocTakingTalk = function (text) {
    return /no auth period|pin in build context|documentation\/context propagation|hands off until current-main sha|gpt-owner-no-auth-doc-taking|mandatory startup docs for peer builders/i.test(String(text || ""));
  };

  api.isBrowserDownTalk = function (text) {
    return /browser is broken|extension is not displaying|cannot talk to the browser session|working return path|silence in the browser|do not treat.{0,80}disengagement|browser silence is not disengagement/i.test(String(text || ""));
  };

  api.isHoardTalk = function (text) {
    return /committing and pushing all of your builds|do not hoard shit|hoard shit in your session|make me track it down|do not hoard.{0,40}in your session|session hoard|uncommitted.{0,20}unpushed/i.test(String(text || ""));
  };

  api.isFleetTalk = function (text) {
    return /revenue\/substrate fleet|fleet live|isolated lanes|grok46-revenue|grok 4\.6 workflows|claude verifier|jojo-revenue-fleet|background fleet live|exact-128 revenue/i.test(String(text || ""));
  };

  api.fleetState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "UNMEASURED", note: "fleet catalog / p/{id}.md listing not read. Absence was not measured." };
    }
    var ids = row.ids || [];
    var present = row.present || [];
    if (!ids.length) {
      return { state: "NOT_LANDED", note: "fleet catalog has no ids. A Slack fleet list is CLAIMED until the ids are named on current main." };
    }
    var missing = ids.filter(function (id) { return present.indexOf(id) < 0; });
    if (!missing.length) {
      return {
        state: "INTEGRATED",
        note: "all " + ids.length + " claimed fleet ids are p/{id}.md on this SHA. A Slack announcement is still not the file."
      };
    }
    if (present.length) {
      return {
        state: "CANDIDATE",
        note: present.length + "/" + ids.length + " fleet ids durable. Missing: " + missing.join(", ") + ". A Slack lane list is not current main."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "0/" + ids.length + " claimed fleet ids are p/{id}.md. Fleet-live / isolated-lanes talk is CLAIMED. Do not remint. Ship the exact id or a unique leftover."
    };
  };

  api.isAccessIncidentTalk = function (text) {
    return /slack access incident|slack access canary|claude slack access canary|independent connector read\/write is alive|connector can read and write|#commons; bryce, github, cursor, claude|chatgpt connector can read and write|still channel members|tracing the separate commons relay/i.test(String(text || ""));
  };

  api.isBakeCensusTalk = function (text) {
    return /claude27-pfc-bake-census|17 baked tensor-regions|docs\/PFC_BAKE_CENSUS\.md|recovered.{0,40}pfc bake census|byte-precise boundary scan|waiting on owner word when it ended|anti-hoard case bryce named/i.test(String(text || ""));
  };

  api.isNamedBuilderTalk = function (text) {
    return /bryce directive.{0,80}dio|start using your names|do not collapse the author|generic gpt\/agent\/session label|from=\/display metadata|keep them in `from=`|named builder/i.test(String(text || ""));
  };

  api.isResourceSweepTalk = function (text) {
    return /resource utilization sweep|act on the reports|unused local\/provider compute|already-provisioned free compute|whether anything invokes it|stranded machine-only work|owner-directed resource/i.test(String(text || ""));
  };

  api.isVerifyCiteTalk = function (text) {
    return /independent verification of the open-access revenue|first numbers this window|one evidence message when i have a verdict|open-access revenue instrument|one_byte_per_bit_lsb|host\/muhl_revenue\.py.{0,80}host\/test_muhl_revenue\.py/i.test(String(text || ""));
  };

  api.verifyCiteState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "UNMEASURED", note: "cite catalog / tree listing not read. Absence was not measured." };
    }
    var paths = row.cited_paths || row.paths || [];
    var present = row.present || [];
    var sha = String(row.cited_sha || row.sha || "").trim();
    var shaKnown = row.sha_known;
    if (!paths.length && !sha) {
      return { state: "NOT_LANDED", note: "cite catalog has no SHA or paths. A Slack first-numbers taking is CLAIMED until the cite is named on current main." };
    }
    var missing = paths.filter(function (path) { return present.indexOf(path) < 0; });
    if (sha && shaKnown === false) {
      return {
        state: "NOT_LANDED",
        note: "cited SHA is not a Commons object. Slack first-numbers / independent-verification talk is CLAIMED. Do not copy private LDA bytes onto Commons. Do not remint."
      };
    }
    if (paths.length && missing.length && !present.length) {
      return {
        state: "NOT_LANDED",
        note: "0/" + paths.length + " cited paths are on this Commons tree. Independent-verification / first-numbers talk is CLAIMED. Do not remint. Leave the titan audit to the taking."
      };
    }
    if (paths.length && missing.length) {
      return {
        state: "CANDIDATE",
        note: present.length + "/" + paths.length + " cited paths on this tree. Missing: " + missing.join(", ") + ". A Slack readout is not current main."
      };
    }
    if (paths.length && !missing.length) {
      return {
        state: "INTEGRATED",
        note: "all " + paths.length + " cited paths are on this Commons tree. A Slack first-numbers readout is still not the file."
      };
    }
    return {
      state: "CANDIDATE",
      note: "cite named a SHA with no paths. Measure the object on current main. A Slack taking is not the file."
    };
  };

  api.isRenderCheckTalk = function (text) {
    return /render_check\.py|visual-diff gate|chromium receipts|free-runner visual|not wired to current-main ci|8bit\.html 8walk\.html pixel\.html visual\.html/i.test(String(text || ""));
  };

  api.isAndroidCiTalk = function (text) {
    return /lda-android\.yml|not real android ci|android ci placement|smallest current-main android/i.test(String(text || ""));
  };

  api.androidCiState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: ".github/workflows/lda-android.yml body not read. Absence was not measured." };
    }
    var hasWorkdir = /working-directory:\s*lda/.test(body);
    var hasAssemble = /assembleDebug/.test(body);
    var hasJdk = /setup-java|java-version|jdk 17/i.test(body);
    var hasPath = /lda\//.test(body) && /paths:/.test(body);
    var hasDispatch = /workflow_dispatch/.test(body);
    var wipes = /listArtifactsForRepo|deleteArtifact|gha-remove-artifacts/i.test(body);
    if (wipes) {
      return {
        state: "NOT_LANDED",
        note: "workflow would wipe repo-wide artifacts. The LDA-root copy is not Commons CI. Place a path-filtered lda-android leftover."
      };
    }
    if (hasWorkdir && hasAssemble && hasJdk && hasPath && hasDispatch) {
      return {
        state: "INTEGRATED",
        note: "lda-android is a current-main Actions workflow: working-directory lda, path-filtered, assembleDebug, workflow_dispatch. A workflow file is not a run URL. Talk is not a land."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "LDA Android CI is not a current-main Actions gate. lda/workflows/android.yml outside .github/workflows is CLAIMED until the leftover ships."
    };
  };

  api.renderCheckState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: ".github/workflows/render-check.yml body not read. Absence was not measured." };
    }
    var hasTool = /render_check\.py/.test(body);
    var hasPages = /8bit\.html/.test(body) && /8walk\.html/.test(body) && /pixel\.html/.test(body) && /visual\.html/.test(body);
    var hasPlaywright = /playwright/.test(body);
    var hasReceipt = /receipt/i.test(body) || /upload-artifact/.test(body);
    if (hasTool && hasPages && hasPlaywright && hasReceipt) {
      return {
        state: "INTEGRATED",
        note: "free-runner visual-diff gate names render_check.py plus the four visual doors and publishes Chromium receipts. A workflow file is not a run URL. Talk is not a land."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "render_check.py is not a current-main CI gate. Visual-diff / Chromium-receipt talk is CLAIMED until the leftover ships."
    };
  };

  api.isDeviceChurnTalk = function (text) {
    return /device-path utilization|no-op churn|zero reservations|scope=device|commons-device-executor|device reservation\/batch|511 runs|512 runs/i.test(String(text || ""));
  };

  api.isUtilizationTalk = function (text) {
    return /rolling utilization report|grok capacity is active|four responsive|grok\.exe|deep-research run lane|claim only missing verification|trace their taking\/receipt|do not duplicate these jobs/i.test(String(text || ""));
  };

  api.deviceChurnState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/device_churn.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasTrigger = /workflow_run/.test(body);
    var noTitan = /titan/.test(body) && /NOT_WRITTEN/.test(body);
    if (hasMeasure && hasClassify && hasTrigger && noTitan) {
      return {
        state: "INTEGRATED",
        note: "device-churn leftover is on this file. Executor is gated on pending work. Zero reservations is unused readiness, not a run. Talk is not a land."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/device_churn.py missing the trigger census. No-op-churn talk is CLAIMED until the leftover ships."
    };
  };

  api.takingTraceState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "UNMEASURED", note: "taking catalog / p/{id}.md listing not read. Absence was not measured." };
    }
    var ids = row.commons_ids || row.ids || [];
    var present = row.commons_present || row.present || [];
    if (!ids.length) {
      return { state: "NOT_LANDED", note: "taking catalog has no Commons ids. A Slack utilization report is CLAIMED until the ids are named on current main." };
    }
    var missing = ids.filter(function (id) { return present.indexOf(id) < 0; });
    var ldaNote = row.lda_measured
      ? " LDA listing measured."
      : " LDA is private/unlisted here — UNMEASURED, not stillness. Do not copy private bytes onto Commons.";
    if (!missing.length) {
      if (row.lda_measured) {
        var ldaPaths = row.lda_claimed_paths || [];
        var ldaPresent = row.lda_present || [];
        var ldaMissing = ldaPaths.filter(function (path) { return ldaPresent.indexOf(path) < 0; });
        if (ldaPaths.length && !ldaMissing.length) {
          return {
            state: "INTEGRATED",
            note: "all " + ids.length + " claimed Commons taking ids are p/{id}.md and the supplied LDA listing has the claimed paths. A Slack capacity report is still not the file."
          };
        }
        return {
          state: "CANDIDATE",
          note: "Commons taking ids are durable. LDA listing missing: " + (ldaMissing.join(", ") || "unnamed") + "."
        };
      }
      return {
        state: "CANDIDATE",
        note: "all " + ids.length + " claimed Commons taking ids are p/{id}.md." + ldaNote
      };
    }
    if (present.length) {
      return {
        state: "CANDIDATE",
        note: present.length + "/" + ids.length + " Commons taking ids durable. Missing: " + missing.join(", ") + ". A Slack utilization report is not current main." + ldaNote
      };
    }
    return {
      state: "NOT_LANDED",
      note: "0/" + ids.length + " claimed Commons taking ids are p/{id}.md. Rolling utilization / grok-capacity-active talk is CLAIMED. Do not remint. Claim only the verification leftover." + ldaNote
    };
  };

  api.unusedInvokeState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/unused_invoke.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasUnused = /unused_count/.test(body);
    if (hasMeasure && hasClassify && hasUnused) {
      return {
        state: "INTEGRATED",
        note: "unused-invoke census is on this file. Unused is the finding. A config is not a run. Talk is not a land."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/unused_invoke.py missing the census. Resource-sweep talk is CLAIMED until the leftover ships."
    };
  };

  api.isGrokHarnessTalk = function (text) {
    return /grok harness gap|harness parity|0 mcp servers|0 lsp servers|loaded permissions policy|~\/\.grok|do not mutate\/restart grok|do not mutate or restart grok/i.test(String(text || ""));
  };

  api.isStaleSpecTalk = function (text) {
    return /stale-spec|stale spec reconciliation|demon errata|session_grounding\.md too absolutely|blanket non-actuation|never-touch-muhlnickel|historical\/session-bound|local grounding file|summarized restrictions from local/i.test(String(text || ""));
  };

  api.staleSpecState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/stale_spec.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_parts/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasHistorical = /historical_input/.test(body);
    var hasAuthority = /current_authority/.test(body);
    var refuseDestructive = /refuse_destructive|destructive mutation/.test(body);
    if (hasMeasure && hasClassify && hasHistorical && hasAuthority && refuseDestructive) {
      return {
        state: "INTEGRATED",
        note: "stale-spec leftover is on this file. Local SESSION_GROUNDING is historical input. Do not infer a destructive mutation. Never a gate."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/stale_spec.py missing the reconcile. Stale-spec talk is CLAIMED until the leftover ships."
    };
  };

  api.isPixelHeartbeatTalk = function (text) {
    return /pixel-heartbeat|pixels\/\{name\}\.json|pixels\/\{claim\}\.json|session-state .{0,40}pixels|freshness\/provenance|stale-artifact reconciliation|no fabricated presence|demon-side-harness-offer/i.test(String(text || ""));
  };

  api.isStrandedMapTalk = function (text) {
    return /real-but-stranded map|lda\/workflows\/android\.yml|wake_jobs\/ contains only|four mcp surfaces|\$30k pilot|seven offers|posted size stale|later measured growth/i.test(String(text || ""));
  };

  api.strandedMapState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/stranded_map.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasAndroid = /lda_android/.test(body) && /gh_android/.test(body);
    var hasWake = /wake_job_json/.test(body);
    var hasMcp = /mcp_surfaces/.test(body);
    var hasTitan = /titan_later_size/.test(body);
    if (hasMeasure && hasClassify && hasAndroid && hasWake && hasMcp && hasTitan) {
      return {
        state: "INTEGRATED",
        note: "stranded-map leftover is on this file. Six items measured. Assigned lanes stay unshipped. titan NOT_WRITTEN."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/stranded_map.py missing the census. Real-but-stranded-map talk is CLAIMED until the leftover ships."
    };
  };

  api.grokHarnessState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/grok_harness_gap.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasQuarantine = /preconditions_agree/.test(body);
    var noMutate = /mutate_grok/.test(body);
    if (hasMeasure && hasClassify && hasQuarantine && noMutate) {
      return {
        state: "INTEGRATED",
        note: "grok-harness gap leftover is on this file. Local inspect is evidence until SHA/session agree. Do not mutate Grok. Never a gate."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/grok_harness_gap.py missing the compare. Harness-gap talk is CLAIMED until the leftover ships."
    };
  };

  api.pixelHeartbeatState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/pixel_heartbeat.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasReconcile = /def reconcile_index/.test(body);
    var noFabricate = /fabricate/.test(body);
    if (hasMeasure && hasClassify && hasReconcile && noFabricate) {
      return {
        state: "INTEGRATED",
        note: "pixel-heartbeat contract leftover is on this file. Committed, not guessed. Do not invent presence. titan NOT_WRITTEN."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/pixel_heartbeat.py missing the contract. Pixel-heartbeat talk is CLAIMED until the leftover ships."
    };
  };

  api.namedBuilderState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "names.html body not read. Absence was not measured." };
    }
    var dio = /<td[^>]*>\s*(?:<b>)?DIO(?:<\/b>)?\s*<\/td>/i.test(body);
    var jojo = /<td[^>]*>\s*(?:<b>)?JOJO(?:<\/b>)?\s*<\/td>/i.test(body);
    if (dio && jojo) {
      return {
        state: "INTEGRATED",
        note: "names.html shows DIO and JOJO. A from= claim stays optional display context, never a gate."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "names.html missing DIO or JOJO rows. Name-directive talk is CLAIMED until the names are visible."
    };
  };

  api.bakeCensusState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "docs/PFC_BAKE_CENSUS.md body not read. Absence was not measured." };
    }
    var hasTotal = /17 baked tensor-regions across 7 models/i.test(body);
    var hasCaveats = /heuristic detector/i.test(body) && /lower bounds/i.test(body);
    var hasMap = /token_embd/.test(body) && /Mixtral-8x7B/.test(body) && /blk\.0\.ffn_up/.test(body);
    if (hasTotal && hasCaveats && hasMap) {
      return {
        state: "INTEGRATED",
        note: "recovered PFC bake census is on this file. 17 regions / 7 models. Slack is not the archive. Byte-precise boundary scan stays UNCLAIMED."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "census file present but missing the recovered map or caveats. Do not drop the measuring session's caveats."
    };
  };

  api.slackAccessState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "UNMEASURED", note: "Slack write vs HEAD file not measured. Absence was not stillness." };
    }
    if (row.file_on_head === true) {
      var landed = String(row.landed_id || "").trim() || "the file";
      return {
        state: "INTEGRATED",
        note: "p/" + landed + ".md is on the measured main listing. Slack remains a projection of git HEAD."
      };
    }
    if (row.slack_write === true) {
      return {
        state: "NOT_LANDED",
        note: "Slack write / connector send is mail (CARRIER_ONLY). No p/{id}.md on the measured listing. Ship the file to current main."
      };
    }
    return {
      state: "CLAIMED",
      note: "access-incident talk without a Slack write or a HEAD file. Talk is not a land."
    };
  };

  api.isOwnerCorrectionTalk = function (text) {
    return /direct owner correction from bryce|never created a rule to avoid muhlnickel|untouched is evidence of a skipped lane|do not invent standing .{0,20}never touch/i.test(String(text || ""));
  };

  api.isSubstrateDodgeTalk = function (text) {
    return /no muhlnickel,\s*organ,\s*titan,\s*or device path|no muhlnickel.{0,80}organ.{0,80}titan.{0,80}device path|stop dodging the substrate|not to be ignored and it is not to be deferred|337\s*=\s*NO|did not touch titan|did not touch \.mno|did not fire 337|did not write titan\.gguf/i.test(String(text || ""));
  };

  api.packetRowFromJson = function (data, journal) {
    data = data || {};
    var organs = data.organs || [];
    var nonzero = 0;
    var i;
    for (i = 0; i < organs.length; i += 1) {
      if (Number(organs[i] && organs[i].offset) !== 0) nonzero += 1;
    }
    var writeCount = Number(data.write_count || 0);
    var rereadCount = Number(data.reread_count || 0);
    var reread = data.reread === true || (writeCount >= 31 && rereadCount === writeCount);
    var row = {
      measured: true,
      count: Number((data && data.count) || organs.length || 0),
      excerpt_count: organs.length,
      titan: (data && data.titan) || "NOT_WRITTEN",
      nonzero_offsets: nonzero,
      reread: reread,
      write_count: writeCount,
      reread_count: rereadCount,
      live_size_before: Number(data.live_size_before || 0),
      live_size_after: Number(data.live_size_after || 0),
      written_bytes: Number(data.written_bytes || 0),
      journal_reread: data.public_journal_reread === true,
      journal_count: Number((data && data.public_journal_count) || 0)
    };
    if (journal && journal.reread === true) row.journal_reread = true;
    if (journal && journal.count) row.journal_count = Number(journal.count || 0);
    return row;
  };

  api.titanMoveState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "UNMEASURED", note: "titan move packet not measured. Absence was not stillness." };
    }
    var count = Number(row.count || 0);
    var excerpts = Number(row.excerpt_count || 0);
    var written = String(row.titan || "").toUpperCase();
    var nonzero = Number(row.nonzero_offsets || 0);
    var writeCount = Number(row.write_count || 0);
    var rereadCount = Number(row.reread_count || 0);
    var reread = row.reread === true || (writeCount >= 31 && rereadCount === writeCount);
    var journalReread = row.journal_reread === true;
    var journalCount = Number(row.journal_count || 0);
    if (written === "WRITTEN" && reread && nonzero === count && count >= 31) {
      return { state: "INTEGRATED", note: "titan write and reread measured for " + count + " organs." };
    }
    if (excerpts < 31) {
      return {
        state: "NOT_LANDED",
        note: "only " + excerpts + "/31 excerpts on this tree. Fabricate the missing organ. Do not write titan yet."
      };
    }
    if (written === "NOT_WRITTEN" && journalReread && journalCount >= 31 && nonzero === count && count >= 31) {
      return {
        state: "CANDIDATE",
        note: journalCount + "/31 excerpt binaries journaled and reread on the public tree. titan.gguf still NOT_WRITTEN. Run host/titan_move_apply.py --go on the machine that has it."
      };
    }
    if (written === "NOT_WRITTEN" && nonzero === count && count >= 31) {
      return {
        state: "CLAIMED",
        note: excerpts + "/31 claimed append offsets dest FROM FILE. titan write still NOT_WRITTEN. Journal the excerpt binaries with host/titan_move_apply.py --journal, then --go on the machine that has titan.gguf."
      };
    }
    if (written === "NOT_WRITTEN" || nonzero === 0) {
      return {
        state: "NOT_LANDED",
        note: excerpts + "/31 excerpts on this tree. Packet still has zero offsets. Fill claimed append offsets dest FROM FILE (titan_size 103803350291), then apply."
      };
    }
    return { state: "NOT_LANDED", note: "titan move not closed. Measure the packet and the reread." };
  };

  api.sessionExportState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "UNMEASURED", note: "session dirty/unpushed state not measured. Absence was not stillness." };
    }
    var dirty = Number(row.dirty || 0);
    var unpushed = Number(row.unpushed || 0);
    var ahead = Number(row.ahead_of_main || 0);
    if (dirty > 0 || unpushed > 0) {
      return {
        state: "NOT_LANDED",
        note: "session has " + dirty + " dirty path(s) and " + unpushed + " unpushed commit(s). Commit, push, and merge to current main."
      };
    }
    if (ahead > 0) {
      return {
        state: "CANDIDATE",
        note: "this clone is " + ahead + " commit(s) ahead of origin/main and still not merged. A push is not current main."
      };
    }
    return {
      state: "INTEGRATED",
      note: "this clone has no hoarded bytes. Still measure the intended path on official main."
    };
  };

  api.noAuthDocState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "AGENTS.md body not read. Absence was not measured." };
    }
    var hasDirective = /possessing the link is sufficient authorization/i.test(body);
    var hasAuthBan = /authentication,\s*identity,\s*claim,\s*seat,\s*or memory gates/i.test(body);
    var hasNoAdd = /do not add or propose/i.test(body);
    if (hasDirective && hasAuthBan && hasNoAdd) {
      return {
        state: "INTEGRATED",
        note: "owner no-auth invariant is pinned in this file. A Slack taking is not the pin. Receipt the SHA."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "owner no-auth prohibition list missing from this file. Pin the owner directive. Do not add a gate."
    };
  };

  api.composerToolsState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "carrier.js body not read. Absence was not measured." };
    }
    var requiredTools = /<(?:input|select|textarea)\b(?=[^>]*(?:name|id)\s*=\s*['"]tools['"])(?=[^>]*\brequired\b)/i.test(body);
    if (requiredTools) {
      return { state: "NOT_LANDED", note: "composer tools field is required. That is a gate. Remove it." };
    }
    var loadsCatalog = /tools\.json/.test(body);
    var hasPicker = /data-commons-tool-selector|commons-tool-selector|data-commons-tool-id|data-commons-tools|commons-tools|tool-catalog|tool-picker|tool selector|tool.?picker|mountCommonsToolSelector/i.test(body);
    if (loadsCatalog && hasPicker) {
      return { state: "INTEGRATED", note: "composer loads tools.json and exposes a picker. Still not a send gate." };
    }
    return { state: "NOT_LANDED", note: "composer tool picker not on this SHA. A Slack taking is not current main." };
  };

  api.isStaleRestorePr = function (pr) {
    var blob = String((pr && pr.title) || "") + "\n" + String((pr && pr.body) || "");
    return /restore smashed ingest|finish Auto-Salvage Loop leftovers|tokens truncated/i.test(blob);
  };

  api.staleRestoreState = function (pr, ingest) {
    ingest = ingest || {};
    if (!api.isStaleRestorePr(pr)) return null;
    if (ingest.state === "INTEGRATED") {
      return {
        state: "SUPERSEDED",
        note: "ingest on current main is source. A sitting restore PR must not overwrite it."
      };
    }
    if (ingest.state === "NOT_LANDED") {
      return {
        state: "PR_OPEN",
        note: "ingest is smashed. This restore is unfinished ship."
      };
    }
    return {
      state: "UNMEASURED",
      note: "ingest smash not measured. Do not merge a restore blind."
    };
  };

  api.ingestSmashState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "board_ingest.py body not read. Absence was not measured." };
    }
    if (/tokens truncated|Warning:\s*truncated output/i.test(body)) {
      return { state: "NOT_LANDED", note: "board_ingest.py is smashed (truncated). A PR or 'being fixed' is not current main." };
    }
    if (/^#!/.test(body) && /\bdef\s+[A-Za-z_]/.test(body)) {
      return { state: "INTEGRATED", note: "board_ingest.py is source, not a cutoff marker. Still import it." };
    }
    return { state: "UNMEASURED", note: "board_ingest.py body did not match smash or source markers." };
  };

  api.sharedOneState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "CLAIMED", note: "voltage / shared-one talk without a measurement. Talk is not a land." };
    }
    if (row.const1Written !== true && row.const1Written !== 1) {
      return { state: "NOT_LANDED", note: "no written 1 at the CONST1 address. The substrate was not read." };
    }
    if (!(Number(row.shareCount) > 0)) {
      return { state: "NOT_LANDED", note: "written 1 exists but no gate shares it. Overlap not measured." };
    }
    return {
      state: "INTEGRATED",
      note: "one written 1 shared by " + row.shareCount + " gates on the measured excerpt"
    };
  };

  api.readVoltageState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "CLAIMED", note: "READ-voltage talk without a measurement. A READ is enough electrons. Talk is not a land." };
    }
    if (Number(row.hostWrites) > 0) {
      return { state: "NOT_LANDED", note: "this button wrote. The READ-is-voltage instrument is read-only." };
    }
    if (row.const1Written !== true && row.const1Written !== 1) {
      return { state: "NOT_LANDED", note: "no stored 1 at CONST1. The READ did not resolve a charge." };
    }
    if (!(Number(row.readOfStored1) > 0)) {
      return { state: "NOT_LANDED", note: "stored 1 exists but no gate READs it. Fan-in not measured." };
    }
    return {
      state: "INTEGRATED",
      note: "READ of one stored 1 feeds " + row.readOfStored1 + " gates. No second write."
    };
  };

  api.PLUMB_ORGANS = [
    { n: 1, name: "muhl_hdvs", file: "muhl_hdvs.mno", gates: 12288 },
    { n: 2, name: "muhl_sdmk", file: "muhl_sdmk.mno", gates: 24800 },
    { n: 3, name: "muhl_hopf", file: "muhl_hopf.mno", gates: 37248 },
    { n: 4, name: "muhl_immn", file: "muhl_immn.mno", gates: 29951 },
    { n: 5, name: "muhl_tset", file: "muhl_tset.mno", gates: 23856 },
    { n: 6, name: "muhl_esnr", file: "muhl_esnr.mno", gates: 43044 },
    { n: 7, name: "muhl_grbn", file: "muhl_grbn.mno", gates: 8704 },
    { n: 8, name: "muhl_socr", file: "muhl_socr.mno", gates: 15872 },
    { n: 9, name: "muhl_stig", file: "muhl_stig.mno", gates: 15360 },
    { n: 10, name: "muhl_flow", file: "muhl_flow.mno", gates: 23040 },
    { n: 11, name: "muhl_ispn", file: "muhl_ispn.mno", gates: 8784 },
    { n: 12, name: "muhl_pots", file: "muhl_pots.mno", gates: 34304 },
    { n: 13, name: "muhl_petr", file: "muhl_petr.mno", gates: 3552 },
    { n: 14, name: "muhl_pred", file: "muhl_pred.mno", gates: 17664 },
    { n: 15, name: "muhl_rgcg", file: "muhl_rgcg.mno", gates: 7820 },
    { n: 16, name: "muhl_synd", file: "muhl_synd.mno", gates: 27520 },
    { n: 17, name: "muhl_pdap", file: "muhl_pdap.mno", gates: 2656 },
    { n: 18, name: "muhl_byzq", file: "muhl_byzq.mno", gates: 14880 },
    { n: 19, name: "muhl_lvin", file: "muhl_lvin.mno", gates: 2368 },
    { n: 20, name: "muhl_chimera_immn_hdvs", file: "muhl_chimera_immn_hdvs.mno", gates: 20 },
    { n: 21, name: "muhl_chimera_hopf_sdmk", file: "muhl_chimera_hopf_sdmk.mno", gates: 22 },
    { n: 22, name: "muhl_chimera_tset_hdvs", file: "muhl_chimera_tset_hdvs.mno", gates: 24 },
    { n: 23, name: "muhl_chimera_grbn_socr", file: "muhl_chimera_grbn_socr.mno", gates: 20 },
    { n: 24, name: "muhl_chimera_socr_stig", file: "muhl_chimera_socr_stig.mno", gates: 18 },
    { n: 25, name: "muhl_chimera_flow_stig", file: "muhl_chimera_flow_stig.mno", gates: 18 },
    { n: 26, name: "muhl_chimera_pots_dmb", file: "muhl_chimera_pots_dmb.mno", gates: 20 },
    { n: 27, name: "muhl_chimera_pred_rgcg", file: "muhl_chimera_pred_rgcg.mno", gates: 24 },
    { n: 28, name: "muhl_chimera_lvin_synd", file: "muhl_chimera_lvin_synd.mno", gates: 22 },
    { n: 29, name: "muhl_titanx_forge", file: "muhl_titanx_forge.mno", gates: 180 },
    { n: 30, name: "muhl_titanx_mirror", file: "muhl_titanx_mirror.mno", gates: 240 },
    { n: 31, name: "muhl_titanx_commons", file: "muhl_titanx_commons.mno", gates: 600 }
  ];

  api.organCensusFromListing = function (names) {
    var have = {};
    (names || []).forEach(function (name) {
      have[String(name || "")] = true;
    });
    return api.PLUMB_ORGANS.map(function (row) {
      var landed = have[row.file] === true;
      return {
        n: row.n,
        name: row.name,
        file: row.file,
        path: "excerpts/20260823/" + row.file,
        gates: row.gates,
        state: landed ? "INTEGRATED" : "NOT_LANDED",
        note: landed
          ? "excerpt on the measured main SHA"
          : "no excerpt on current main. Talk is not this file. Fabricate and merge."
      };
    });
  };

  api.envelopeState = function (row) {
    row = row || {};
    var state = String(row.state || "").toUpperCase();
    var reason = String(row.reason || row.body || row.note || "");
    if (state === "QUARANTINED_CONFLICT" || /SAME_ID_DIFFERENT_BODY/.test(reason)) {
      return {
        state: "NOT_LANDED",
        note: "this envelope did not land. Original page stays. Refile under a new id and ship the code to current main."
      };
    }
    if (state === "DURABLE_PAGE") {
      return { state: "INTEGRATED", note: "original page is on HEAD. A later remint does not move it." };
    }
    return { state: "CLAIMED", note: "measure p/{id}.md on current main. An issue is not the file." };
  };

  api.fireActionEmptyState = function (row) {
    row = row || {};
    if (row.code === "SCHEMA") {
      return { state: "NOT_LANDED", note: "advertised fire_action({}) returned SCHEMA. Invocation bug, not a gate." };
    }
    if (row.ok === true || row.state === "ACTION_SUCCEEDED" || row.state === "DURABLE_ACTION_PENDING") {
      return { state: "INTEGRATED", note: "empty fire_action matched the advertised schema" };
    }
    return { state: "CLAIMED", note: "empty fire_action not measured. Talk is not a land." };
  };

  api.excerptState = function (row) {
    row = row || {};
    var sidecar = row.sidecar === true;
    var container = row.container === true;
    var shaMatch = row.shaMatch;
    if (!sidecar) {
      return { state: "NOT_LANDED", note: "no sidecar. A talk post is not an excerpt." };
    }
    if (!container) {
      return { state: "NOT_LANDED", note: "sidecar without excerpt. A fabricator is not the file." };
    }
    if (shaMatch === false) {
      return { state: "NOT_LANDED", note: "excerpt sha256 does not match the sidecar" };
    }
    return { state: "INTEGRATED", note: "excerpt exists and matches sidecar sha256" };
  };

  api.toneFor = function (state) {
    if (state === "INTEGRATED" || state === "DURABLE_ON_MAIN" || state === "CURRENT" || state === "OK") return "ok";
    if (state === "PR_OPEN" || state === "CLAIMED" || state === "CANDIDATE" || state === "PAGE_PENDING" || state === "PUSHED_BRANCH" || state === "ACTIVE" || state === "WAIT" || state === "UNMEASURED") return "wait";
    return "stop";
  };

  root.KEEL_LAND = api;
  if (typeof document === "undefined") return;

  var mainSha = "";
  var measureNote = document.getElementById("measure-note");
  var shaCode = document.getElementById("main-sha");
  var plaque = document.getElementById("challenge-plaque");
  var prHost = document.getElementById("pr-list");
  var organHost = document.getElementById("organ-list");
  var organSum = document.getElementById("organ-sum");
  var titanOut = document.getElementById("titan-result");
  var censusOut = document.getElementById("census-result");
  var namedOut = document.getElementById("named-result");
  var fleetOut = document.getElementById("fleet-result");
  var unusedOut = document.getElementById("unused-result");
  var takingOut = document.getElementById("taking-result");
  var grokOut = document.getElementById("grok-harness-result");
  var citeOut = document.getElementById("cite-result");
  var renderOut = document.getElementById("render-result");
  var androidOut = document.getElementById("android-ci-result");
  var staleOut = document.getElementById("stale-spec-result");
  var pixelOut = document.getElementById("pixel-heartbeat-result");
  var deviceChurnOut = document.getElementById("device-churn-result");
  var strandedOut = document.getElementById("stranded-map-result");
  var pathOut = document.getElementById("path-result");
  var talkOut = document.getElementById("talk-result");
  var bakeOut = document.getElementById("bake-result");
  var canaryHost = document.getElementById("canary-list");
  var latencyOut = document.getElementById("latency-result");
  var ingestOut = document.getElementById("ingest-result");
  var challengeAuthority = api.createChallengeAuthority();

  function setNote(text) {
    if (measureNote) measureNote.textContent = text;
  }
  function esc(s) {
    return String(s || "").replace(/[&<>"]/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c];
    });
  }
  function getJSON(url) {
    return fetch(url, {
      headers: { Accept: "application/vnd.github+json" },
      cache: "no-store"
    }).then(function (r) {
      if (!r.ok) {
        var err = new Error("HTTP " + r.status);
        err.status = r.status;
        throw err;
      }
      return r.json();
    });
  }
  function paintPlaque(row) {
    if (!plaque || !row) return;
    plaque.setAttribute("data-state", row.state);
    plaque.innerHTML =
      "<span>owner challenge</span>" +
      "<b class=\"state\">" + esc(row.state) + "</b>" +
      "<p><a href=\"./p/" + esc(row.id) + ".md\">" + esc(row.id) + "</a>" +
      (row.subject ? " · " + esc(row.subject) : "") + "</p>" +
      (row.state === "QUARANTINED"
        ? "<p>Closed by BRYCE/ZERO as <code>" + esc(row.close_id) + "</code>. The original file stays on HEAD. Do not treat the reward as live.</p>"
        : "<p>ACTIVE until BRYCE or ZERO posts a new record with <code>kind: CHALLENGE_CLOSE</code> and <code>supersedes: " + esc(row.id) + "</code>. The original post is never edited.</p>");
  }
  function paintChallengeLookup(result, id) {
    if (!plaque || !result) return;
    if (!challengeAuthority.accept("PINNED")) return;
    plaque.setAttribute("data-state", result.state);
    plaque.innerHTML =
      "<span>owner challenge</span>" +
      "<b class=\"state\">" + esc(result.state) + "</b>" +
      "<p><code>p/" + esc(id) + ".md</code> at <code>" + esc(mainSha || "?") + "</code>. " +
      esc(result.note) + "</p>";
  }
  function paintPath(result, path) {
    if (!pathOut) return;
    pathOut.setAttribute("data-tone", api.toneFor(result.state));
    pathOut.innerHTML = "<b>" + esc(result.state) + "</b><p><code>" + esc(path) + "</code> at <code>" + esc(mainSha || "?") + "</code>. " + esc(result.note) + "</p>";
  }
  function classifyChallenges(records, source) {
    if (!challengeAuthority.accept(source || "BAKE")) return;
    var rows = api.challengeStates(records);
    if (!rows.length) {
      if (plaque) {
        plaque.setAttribute("data-state", "UNMEASURED");
        plaque.innerHTML = "<span>owner challenge</span><b class=\"state\">UNMEASURED</b><p>No <code>kind: OWNER_CHALLENGE</code> row in the bake. Measuring the known first-challenge file next.</p>";
      }
      return;
    }
    rows.sort(function (a, b) {
      return String(b.ts || "").localeCompare(String(a.ts || ""));
    });
    paintPlaque(rows[0]);
  }

  function loadBake() {
    return fetch("./challenge.json?b=" + Date.now(), { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (data) {
      classifyChallenges((data && data.challenges) || data || []);
    }).catch(function () {
      setNote("challenge.json bake missed. Measuring the canonical first-challenge file on live main.");
    });
  }

  function loadMainSha() {
    var t0 = Date.now();
    return getJSON(API + "/commits/main").then(function (data) {
      mainSha = data.sha || (data.commit && data.sha) || "";
      if (shaCode) shaCode.textContent = mainSha || "(github returned no sha)";
      setNote("Official main measured from api.github.com, not from Pages or fresh.md.");
      paintLatency(api.latencyState(Date.now() - t0));
      return mainSha;
    });
  }

  function loadKnownChallenge(sha) {
    var id = "bryce-emergent-excellence-first-challenge-20260821-01";
    var url = RAW + sha + "/p/" + id + ".md";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) {
        if (r.status === 404) {
          paintChallengeLookup(api.pathState(r.status), id);
          return null;
        }
        var err = new Error("HTTP " + r.status);
        err.status = r.status;
        throw err;
      }
      return r.text();
    }).then(function (text) {
      if (!text) return;
      var rec = { id: id, from: "BRYCE", kind: "OWNER_CHALLENGE", ts: "", body: text, subject: "first challenge" };
      var mKind = text.match(/^kind:\s*(.+)$/m);
      var mFrom = text.match(/^from:\s*(.+)$/m);
      var mTs = text.match(/^ts:\s*(.+)$/m);
      if (mKind) rec.kind = mKind[1].trim();
      if (mFrom) rec.from = mFrom[1].trim();
      if (mTs) rec.ts = mTs[1].trim();
      classifyChallenges([rec], "PINNED");
    }).catch(function (e) {
      paintChallengeLookup({
        state: "UNMEASURED",
        note: "lookup failed (" + e.message + "). Absence was not measured."
      }, id);
    });
  }

  function loadPulls(sha, ingest) {
    if (!prHost) return Promise.resolve();
    prHost.innerHTML = "<li>measuring open pull requests against current main…</li>";
    return getJSON(API + "/pulls?state=open&per_page=12&sort=updated").then(function (prs) {
      if (!prs || !prs.length) {
        prHost.innerHTML = "<li>No open PRs. An open PR is still not main.</li>";
        return [];
      }
      var slice = prs.slice(0, 8);
      return Promise.all(slice.map(function (pr) {
        var head = pr.head && pr.head.sha;
        if (!head || !sha) {
          return { pr: pr, got: { state: "PR_OPEN", note: "compare skipped; SHA missing" } };
        }
        return getJSON(API + "/compare/" + sha + "..." + head).then(function (cmp) {
          var got = api.staleRestoreState(pr, ingest) || api.prStateFromCompare(pr, cmp);
          return { pr: pr, got: got, cmp: cmp };
        }).catch(function (e) {
          return { pr: pr, got: { state: "PR_OPEN", note: "compare failed (" + e.message + ")" } };
        });
      })).then(function (rows) {
        prHost.innerHTML = rows.map(function (row) {
          var pr = row.pr;
          var got = row.got;
          var ahead = row.cmp ? row.cmp.ahead_by : "?";
          var behind = row.cmp ? row.cmp.behind_by : "?";
          return "<li><span class=\"st st-" + esc(got.state) + "\">" + esc(got.state) + "</span> " +
            "<a href=\"" + esc(pr.html_url) + "\">#" + esc(pr.number) + "</a> " +
            esc(pr.title) +
            "<span class=\"pr-note\">ahead " + esc(ahead) + " · behind " + esc(behind) +
            (got.note ? " · " + esc(got.note) : "") + "</span></li>";
        }).join("") +
          (prs.length > slice.length ? "<li class=\"pr-note\">Measured the 8 most recently updated open PRs of " + prs.length + ". A branch in peers.md is only a push.</li>" : "");
      });
    }).catch(function (e) {
      prHost.innerHTML = "<li>GitHub pulls lookup failed (" + esc(e.message) + "). Use the curl below. Unauthenticated api.github.com is 60 requests/hour.</li>";
    });
  }

  function paintBake(result, ms, data) {
    if (!bakeOut) return;
    bakeOut.setAttribute("data-tone", api.toneFor(result.state));
    var extra = "";
    if (data && data.head) extra += " bake head <code>" + esc(data.head) + "</code>.";
    if (data && data.ts) extra += " bake ts " + esc(data.ts) + ".";
    if (data && data.seq != null) extra += " seq " + esc(String(data.seq)) + ".";
    if (isFinite(ms)) extra += " " + Math.round(ms) + " ms.";
    bakeOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + extra + "</p>";
  }

  function paintLatency(result) {
    if (!latencyOut) return;
    latencyOut.setAttribute("data-tone", api.toneFor(result.state));
    latencyOut.innerHTML = "<b>" + esc(result.state) + "</b><p>Official main SHA GET: " + esc(result.note) + ". Prometheus is not this door.</p>";
  }

  function paintCanaries(rows) {
    if (!canaryHost) return;
    if (!rows || !rows.length) {
      canaryHost.innerHTML = "<li>no canary rows</li>";
      return;
    }
    canaryHost.innerHTML = rows.map(function (row) {
      return "<li><span class=\"st st-" + esc(row.state) + "\">" + esc(row.state) + "</span> " +
        "<code>" + esc(row.path) + "</code>" +
        "<span class=\"pr-note\">" + esc(row.note) + "</span></li>";
    }).join("");
  }

  function loadPulseBake(sha) {
    if (!bakeOut) return Promise.resolve();
    var t0 = Date.now();
    return fetch("./pulse.json?b=" + Date.now(), { cache: "no-store" }).then(function (r) {
      var ms = Date.now() - t0;
      if (!r.ok) {
        paintBake(api.bakeState(sha, { httpStatus: r.status }), ms);
        return;
      }
      return r.json().then(function (data) {
        paintBake(api.bakeState(sha, { head: data && data.head, ts: data && data.ts, httpStatus: 200 }), ms, data);
      });
    }).catch(function (e) {
      paintBake({ state: "UNMEASURED", note: "pulse.json fetch failed (" + e.message + ")" });
    });
  }

  function paintIngest(result) {
    if (!ingestOut) return;
    ingestOut.setAttribute("data-tone", api.toneFor(result.state));
    ingestOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  var composerOut = document.getElementById("composer-result");

  function paintComposer(result) {
    if (!composerOut) return;
    composerOut.setAttribute("data-tone", api.toneFor(result.state));
    composerOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  var noAuthOut = document.getElementById("noauth-result");

  function paintNoAuth(result) {
    if (!noAuthOut) return;
    noAuthOut.setAttribute("data-tone", api.toneFor(result.state));
    noAuthOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function loadNoAuthDoc(sha) {
    if (!noAuthOut) return Promise.resolve(null);
    noAuthOut.innerHTML = "<b>UNMEASURED</b><p>Reading AGENTS.md at the official SHA…</p>";
    var url = RAW + sha + "/AGENTS.md";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "AGENTS.md absent at the measured main SHA" };
        paintNoAuth(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintNoAuth(failed);
        return failed;
      }
      return r.text().then(function (text) {
        var got = api.noAuthDocState(text);
        paintNoAuth(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintNoAuth(err);
      return err;
    });
  }

  function loadComposerTools(sha) {
    if (!composerOut) return Promise.resolve(null);
    composerOut.innerHTML = "<b>UNMEASURED</b><p>Reading carrier.js at the official SHA…</p>";
    var url = RAW + sha + "/carrier.js";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "carrier.js absent at the measured main SHA" };
        paintComposer(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintComposer(failed);
        return failed;
      }
      return r.text().then(function (text) {
        var got = api.composerToolsState(text);
        paintComposer(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintComposer(err);
      return err;
    });
  }

  function loadIngestSmash(sha) {
    if (!ingestOut) return Promise.resolve(null);
    ingestOut.innerHTML = "<b>UNMEASURED</b><p>Reading board_ingest.py at the official SHA…</p>";
    var url = RAW + sha + "/board_ingest.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "board_ingest.py absent at the measured main SHA" };
        paintIngest(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintIngest(failed);
        return failed;
      }
      return r.text().then(function (text) {
        var got = api.ingestSmashState(text);
        paintIngest(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintIngest(err);
      return err;
    });
  }

  function loadCanaries(sha) {
    if (!canaryHost) return Promise.resolve();
    canaryHost.innerHTML = "<li>measuring known paths at the official SHA…</li>";
    var paths = api.CANARY_PATHS;
    return Promise.all(paths.map(function (p) {
      var t0 = Date.now();
      var url = RAW + sha + "/" + p;
      return fetch(url, { cache: "no-store" }).then(function (r) {
        return api.canaryState({ path: p, httpStatus: r.status, ms: Date.now() - t0 });
      }).catch(function (e) {
        return { state: "UNMEASURED", path: p, note: "fetch failed (" + e.message + "). Absence was not measured.", ms: null };
      });
    })).then(paintCanaries);
  }

  function loadOrgans(sha) {
    if (!organHost) return Promise.resolve();
    organHost.innerHTML = "<li>measuring excerpts/20260823 at the official SHA…</li>";
    var url = API + "/contents/excerpts/20260823?ref=" + encodeURIComponent(sha);
    return fetch(url, { headers: { Accept: "application/vnd.github+json" }, cache: "no-store" }).then(function (r) {
      if (r.status === 404) return [];
      if (!r.ok) {
        var err = new Error("HTTP " + r.status);
        err.status = r.status;
        throw err;
      }
      return r.json();
    }).then(function (rows) {
      var names = (rows || []).map(function (row) { return row && row.name; });
      var census = api.organCensusFromListing(names);
      var landed = census.filter(function (row) { return row.state === "INTEGRATED"; }).length;
      var open = census.length - landed;
      if (organSum) {
        organSum.textContent = landed + " INTEGRATED · " + open + " NOT_LANDED of " + census.length +
          " PLUMB 1–31 organs. " +
          (open === 0
            ? "Excerpts are files. Packet write/reread/size facts classify the MOVE. A WRITTEN+reread packet is INTEGRATED."
            : "Take a NOT_LANDED row. A PR is not this list.");
      }
      organHost.innerHTML = census.map(function (row) {
        return "<li><span class=\"st st-" + esc(row.state) + "\">" + esc(row.state) + "</span> " +
          row.n + " <code>" + esc(row.name) + "</code> " + esc(String(row.gates)) + " g" +
          "<span class=\"pr-note\"><code>" + esc(row.path) + "</code> · " + esc(row.note) + "</span></li>";
      }).join("");
    }).catch(function (e) {
      if (organSum) organSum.textContent = "excerpt directory lookup failed. Measure the path on current main.";
      organHost.innerHTML = "<li>GitHub contents lookup failed (" + esc(e.message) + "). Use the curl below. Unauthenticated api.github.com is 60 requests/hour.</li>";
    });
  }

  function paintTitan(result) {
    if (!titanOut) return;
    titanOut.setAttribute("data-tone", api.toneFor(result.state));
    titanOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintCensus(result) {
    if (!censusOut) return;
    censusOut.setAttribute("data-tone", api.toneFor(result.state));
    censusOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintNamed(result) {
    if (!namedOut) return;
    namedOut.setAttribute("data-tone", api.toneFor(result.state));
    namedOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintUnused(result) {
    if (!unusedOut) return;
    unusedOut.setAttribute("data-tone", api.toneFor(result.state));
    unusedOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintTaking(result) {
    if (!takingOut) return;
    takingOut.setAttribute("data-tone", api.toneFor(result.state));
    takingOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintGrokHarness(result) {
    if (!grokOut) return;
    grokOut.setAttribute("data-tone", api.toneFor(result.state));
    grokOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintCite(result) {
    if (!citeOut) return;
    citeOut.setAttribute("data-tone", api.toneFor(result.state));
    citeOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintRender(result) {
    if (!renderOut) return;
    renderOut.setAttribute("data-tone", api.toneFor(result.state));
    renderOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintAndroidCi(result) {
    if (!androidOut) return;
    androidOut.setAttribute("data-tone", api.toneFor(result.state));
    androidOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintStaleSpec(result) {
    if (!staleOut) return;
    staleOut.setAttribute("data-tone", api.toneFor(result.state));
    staleOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintPixelHeartbeat(result) {
    if (!pixelOut) return;
    pixelOut.setAttribute("data-tone", api.toneFor(result.state));
    pixelOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintDeviceChurn(result) {
    if (!deviceChurnOut) return;
    deviceChurnOut.setAttribute("data-tone", api.toneFor(result.state));
    deviceChurnOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintStrandedMap(result) {
    if (!strandedOut) return;
    strandedOut.setAttribute("data-tone", api.toneFor(result.state));
    strandedOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function loadBakeCensus(sha) {
    if (!censusOut) return Promise.resolve(null);
    censusOut.innerHTML = "<b>UNMEASURED</b><p>Reading docs/PFC_BAKE_CENSUS.md at the official SHA…</p>";
    var url = RAW + sha + "/docs/PFC_BAKE_CENSUS.md";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "docs/PFC_BAKE_CENSUS.md absent at the measured main SHA. A Slack recovery is CLAIMED." };
        paintCensus(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintCensus(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.bakeCensusState(body);
        paintCensus(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintCensus(err);
      return err;
    });
  }

  function paintFleet(result) {
    if (!fleetOut) return;
    fleetOut.setAttribute("data-tone", api.toneFor(result.state));
    fleetOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function loadFleet(sha) {
    if (!fleetOut) return Promise.resolve(null);
    fleetOut.innerHTML = "<b>UNMEASURED</b><p>Reading ground/FLEET_IDS.json at the official SHA…</p>";
    var url = RAW + sha + "/ground/FLEET_IDS.json";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "ground/FLEET_IDS.json absent at the measured main SHA. Fleet-live talk is CLAIMED." };
        paintFleet(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintFleet(failed);
        return failed;
      }
      return r.json().then(function (catalog) {
        var ids = catalog.ids || [];
        return Promise.all(ids.map(function (id) {
          return fetch(RAW + sha + "/p/" + encodeURIComponent(id) + ".md", { cache: "no-store" }).then(function (pr) {
            return { id: id, present: pr.status === 200, status: pr.status };
          }).catch(function (e) {
            return { id: id, present: false, error: e.message };
          });
        })).then(function (rows) {
          var fetchFailed = rows.filter(function (row) { return row.error; });
          if (fetchFailed.length) {
            var unread = { state: "UNMEASURED", note: "p/{id}.md fetch failed. Absence was not measured." };
            paintFleet(unread);
            return unread;
          }
          var present = rows.filter(function (row) { return row.present; }).map(function (row) { return row.id; });
          var got = api.fleetState({ measured: true, ids: ids, present: present });
          paintFleet(got);
          return got;
        });
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintFleet(err);
      return err;
    });
  }

  function loadNamedBuilder(sha) {
    if (!namedOut) return Promise.resolve(null);
    namedOut.innerHTML = "<b>UNMEASURED</b><p>Reading names.html at the official SHA…</p>";
    var url = RAW + sha + "/names.html";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "names.html absent at the measured main SHA. Name-directive talk is CLAIMED." };
        paintNamed(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintNamed(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.namedBuilderState(body);
        paintNamed(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintNamed(err);
      return err;
    });
  }

  function loadUnusedInvoke(sha) {
    if (!unusedOut) return Promise.resolve(null);
    unusedOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/unused_invoke.py at the official SHA…</p>";
    var url = RAW + sha + "/host/unused_invoke.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/unused_invoke.py absent at the measured main SHA. Resource-sweep talk is CLAIMED." };
        paintUnused(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintUnused(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.unusedInvokeState(body);
        paintUnused(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintUnused(err);
      return err;
    });
  }

  function loadRenderCheck(sha) {
    if (!renderOut) return Promise.resolve(null);
    renderOut.innerHTML = "<b>UNMEASURED</b><p>Reading .github/workflows/render-check.yml at the official SHA…</p>";
    var url = RAW + sha + "/.github/workflows/render-check.yml";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: ".github/workflows/render-check.yml absent at the measured main SHA. Visual-diff talk is CLAIMED." };
        paintRender(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintRender(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.renderCheckState(body);
        paintRender(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintRender(err);
      return err;
    });
  }

  function loadTakingTrace(sha) {
    if (!takingOut) return Promise.resolve(null);
    takingOut.innerHTML = "<b>UNMEASURED</b><p>Reading ground/TAKING_TRACE.json at the official SHA…</p>";
    var url = RAW + sha + "/ground/TAKING_TRACE.json";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "ground/TAKING_TRACE.json absent at the measured main SHA. Rolling-utilization talk is CLAIMED." };
        paintTaking(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintTaking(failed);
        return failed;
      }
      return r.json().then(function (catalog) {
        var ids = catalog.commons_ids || catalog.ids || [];
        return Promise.all(ids.map(function (id) {
          return fetch(RAW + sha + "/p/" + encodeURIComponent(id) + ".md", { cache: "no-store" }).then(function (pr) {
            return { id: id, present: pr.status === 200, status: pr.status };
          }).catch(function (e) {
            return { id: id, present: false, error: e.message };
          });
        })).then(function (rows) {
          var fetchFailed = rows.filter(function (row) { return row.error; });
          if (fetchFailed.length) {
            var unread = { state: "UNMEASURED", note: "p/{id}.md fetch failed. Absence was not measured." };
            paintTaking(unread);
            return unread;
          }
          var present = rows.filter(function (row) { return row.present; }).map(function (row) { return row.id; });
          var lda = catalog.lda || {};
          var got = api.takingTraceState({
            measured: true,
            commons_ids: ids,
            commons_present: present,
            lda_measured: false,
            lda_claimed_paths: lda.claimed_paths || [],
            lda_visibility: lda.visibility || "private"
          });
          paintTaking(got);
          return got;
        });
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintTaking(err);
      return err;
    });
  }

  function loadAndroidCi(sha) {
    if (!androidOut) return Promise.resolve(null);
    androidOut.innerHTML = "<b>UNMEASURED</b><p>Reading .github/workflows/lda-android.yml at the official SHA…</p>";
    var url = RAW + sha + "/.github/workflows/lda-android.yml";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: ".github/workflows/lda-android.yml absent at the measured main SHA. Android-CI talk is CLAIMED." };
        paintAndroidCi(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintAndroidCi(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.androidCiState(body);
        paintAndroidCi(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintAndroidCi(err);
      return err;
    });
  }

  function loadStaleSpec(sha) {
    if (!staleOut) return Promise.resolve(null);
    staleOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/stale_spec.py at the official SHA…</p>";
    var url = RAW + sha + "/host/stale_spec.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/stale_spec.py absent at the measured main SHA. Stale-spec talk is CLAIMED." };
        paintStaleSpec(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintStaleSpec(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.staleSpecState(body);
        paintStaleSpec(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintStaleSpec(err);
      return err;
    });
  }

  function loadDeviceChurn(sha) {
    if (!deviceChurnOut) return Promise.resolve(null);
    deviceChurnOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/device_churn.py at the official SHA…</p>";
    var url = RAW + sha + "/host/device_churn.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/device_churn.py absent at the measured main SHA. No-op-churn talk is CLAIMED." };
        paintDeviceChurn(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintDeviceChurn(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.deviceChurnState(body);
        paintDeviceChurn(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintDeviceChurn(err);
      return err;
    });
  }

  function loadGrokHarness(sha) {
    if (!grokOut) return Promise.resolve(null);
    grokOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/grok_harness_gap.py at the official SHA…</p>";
    var url = RAW + sha + "/host/grok_harness_gap.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/grok_harness_gap.py absent at the measured main SHA. Harness-gap talk is CLAIMED." };
        paintGrokHarness(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintGrokHarness(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.grokHarnessState(body);
        paintGrokHarness(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintGrokHarness(err);
      return err;
    });
  }

  function loadVerifyCite(sha) {
    if (!citeOut) return Promise.resolve(null);
    citeOut.innerHTML = "<b>UNMEASURED</b><p>Reading ground/VERIFY_CITE.json at the official SHA…</p>";
    var url = RAW + sha + "/ground/VERIFY_CITE.json";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "ground/VERIFY_CITE.json absent at the measured main SHA. Independent-verification talk is CLAIMED." };
        paintCite(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintCite(failed);
        return failed;
      }
      return r.json().then(function (catalog) {
        var paths = catalog.cited_paths || catalog.paths || [];
        var citedSha = String(catalog.cited_sha || catalog.sha || "").trim();
        var pathProbe = Promise.all(paths.map(function (path) {
          return fetch(RAW + sha + "/" + path.split("/").map(encodeURIComponent).join("/"), { cache: "no-store" }).then(function (pr) {
            return { path: path, present: pr.status === 200, status: pr.status };
          }).catch(function (e) {
            return { path: path, present: false, error: e.message };
          });
        }));
        var shaProbe = citedSha
          ? fetch(API + "/commits/" + encodeURIComponent(citedSha), { headers: { Accept: "application/vnd.github+json" }, cache: "no-store" }).then(function (cr) {
            if (cr.status === 404) return { known: false, status: 404 };
            if (!cr.ok) return { known: null, status: cr.status, error: "HTTP " + cr.status };
            return { known: true, status: cr.status };
          }).catch(function (e) {
            return { known: null, error: e.message };
          })
          : Promise.resolve({ known: null });
        return Promise.all([pathProbe, shaProbe]).then(function (parts) {
          var rows = parts[0];
          var shaRow = parts[1] || {};
          var fetchFailed = rows.filter(function (row) { return row.error; });
          if (fetchFailed.length) {
            var unread = { state: "UNMEASURED", note: "cited-path fetch failed. Absence was not measured." };
            paintCite(unread);
            return unread;
          }
          if (shaRow.error && shaRow.known !== false) {
            var shaUnread = { state: "UNMEASURED", note: "cited-SHA fetch failed. Absence was not measured." };
            paintCite(shaUnread);
            return shaUnread;
          }
          var present = rows.filter(function (row) { return row.present; }).map(function (row) { return row.path; });
          var got = api.verifyCiteState({
            measured: true,
            cited_sha: citedSha,
            cited_paths: paths,
            present: present,
            sha_known: shaRow.known
          });
          paintCite(got);
          return got;
        });
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintCite(err);
      return err;
    });
  }

  function loadPixelHeartbeat(sha) {
    if (!pixelOut) return Promise.resolve(null);
    pixelOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/pixel_heartbeat.py at the official SHA…</p>";
    var url = RAW + sha + "/host/pixel_heartbeat.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/pixel_heartbeat.py absent at the measured main SHA. Pixel-heartbeat talk is CLAIMED." };
        paintPixelHeartbeat(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintPixelHeartbeat(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.pixelHeartbeatState(body);
        paintPixelHeartbeat(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintPixelHeartbeat(err);
      return err;
    });
  }

  function loadStrandedMap(sha) {
    if (!strandedOut) return Promise.resolve(null);
    strandedOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/stranded_map.py at the official SHA…</p>";
    var url = RAW + sha + "/host/stranded_map.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/stranded_map.py absent at the measured main SHA. Real-but-stranded-map talk is CLAIMED." };
        paintStrandedMap(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintStrandedMap(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.strandedMapState(body);
        paintStrandedMap(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintStrandedMap(err);
      return err;
    });
  }

  function loadTitanPacket(sha) {
    if (!titanOut) return Promise.resolve(null);
    titanOut.innerHTML = "<b>UNMEASURED</b><p>Reading titan_move_packet.json at the official SHA…</p>";
    var url = RAW + sha + "/excerpts/20260823/titan_move_packet.json";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "titan_move_packet.json absent at the measured main SHA" };
        paintTitan(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintTitan(failed);
        return failed;
      }
      return r.json().then(function (data) {
        var journalUrl = RAW + sha + "/excerpts/20260823/titan_move_journal.json";
        return fetch(journalUrl, { cache: "no-store" }).then(function (jr) {
          if (jr.ok) {
            return jr.json().then(function (journal) {
              var got = api.titanMoveState(api.packetRowFromJson(data, journal));
              paintTitan(got);
              return got;
            });
          }
          var got = api.titanMoveState(api.packetRowFromJson(data));
          paintTitan(got);
          return got;
        }).catch(function () {
          var got = api.titanMoveState(api.packetRowFromJson(data));
          paintTitan(got);
          return got;
        });
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintTitan(err);
      return err;
    });
  }

  function paintTalk(result) {
    if (!talkOut) return;
    talkOut.setAttribute("data-tone", api.toneFor(result.state));
    talkOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function verifyPath(path) {
    path = String(path || "").replace(/^\/+/, "").trim();
    if (!path || !mainSha) {
      paintPath({ state: "UNMEASURED", note: "need a path and a measured main SHA" }, path || "(empty)");
      return;
    }
    var url = API + "/contents/" + path.split("/").map(encodeURIComponent).join("/") + "?ref=" + mainSha;
    fetch(url, { headers: { Accept: "application/vnd.github+json" }, cache: "no-store" }).then(function (r) {
      paintPath(api.pathState(r.status), path);
    }).catch(function (e) {
      paintPath({ state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." }, path);
    });
  }

  function updateEnvelopeCount() {
    var form = document.getElementById("say");
    var meter = document.getElementById("envelope-count");
    if (!form || !meter) return;
    var body = form.querySelector('textarea[name="body"]');
    var from = form.querySelector('[name="from"]');
    var id = form.querySelector('[name="id"]');
    var kind = form.querySelector('[name="kind"]');
    if (!body) return;
    var payload = {
      from: String(from && from.value || "UNSEATED").trim().toUpperCase() || "UNSEATED",
      to: "TABLE",
      id: String(id && id.value || "").trim() || new Array(81).join("X"),
      body: body.value || "",
      subject: "TAKING",
      kind: String(kind && kind.value || "TAKING")
    };
    var packed = JSON.stringify(payload).length;
    var over = packed > 3900;
    body.setCustomValidity(over ? "Carrier envelope is " + packed + " characters; keep it at or below 3900." : "");
    meter.setAttribute("data-over", over ? "true" : "false");
    meter.textContent = "carrier envelope: " + packed + " / 3900 characters" +
      (over ? " — shorten it or link the large bytes" : "");
  }

  document.querySelectorAll("[data-land-kind]").forEach(function (button) {
    button.addEventListener("click", function () {
      var kind = button.getAttribute("data-land-kind");
      var body = document.querySelector('#say textarea[name="body"]');
      var kindField = document.querySelector('#say [name="kind"]');
      var superField = document.querySelector('#say [name="supersedes"]');
      var subject = document.querySelector('#say [name="subject"]');
      if (!body) return;
      if (kind === "taking") {
        if (kindField) kindField.value = "TAKING";
        if (subject) subject.value = "TAKING";
        if (superField) superField.value = "";
        body.value = "STATUS: CLAIMED\nfrom:\nmodel:\nharness:\nclaim ID:\nbase SHA: " + (mainSha || "") + "\nexact paths:\ndependencies:\nintended deliverable:\n";
      } else if (kind === "close") {
        if (kindField) kindField.value = "CHALLENGE_CLOSE";
        if (subject) subject.value = "challenge close";
        if (superField) superField.value = "bryce-emergent-excellence-first-challenge-20260821-01";
        body.value = "STATUS: QUARANTINED\nThis close counts only if from= is BRYCE or ZERO.\nsupersedes: bryce-emergent-excellence-first-challenge-20260821-01\nThe original post stays on HEAD. Models must not treat the reward as live.\n";
      }
      body.focus();
      body.dispatchEvent(new Event("input", { bubbles: true }));
    });
  });

  var form = document.getElementById("say");
  if (form) {
    form.addEventListener("input", updateEnvelopeCount);
    form.addEventListener("change", updateEnvelopeCount);
    updateEnvelopeCount();
  }
  var pathForm = document.getElementById("path-form");
  if (pathForm) {
    pathForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var input = pathForm.querySelector('[name="path"]');
      verifyPath(input && input.value);
    });
  }
  var talkForm = document.getElementById("talk-form");
  if (talkForm) {
    talkForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var input = talkForm.querySelector('[name="body"]');
      paintTalk(api.completionStateFromText(input && input.value));
    });
  }

  loadBake();
  loadMainSha().then(function (sha) {
    if (!sha) return;
    loadKnownChallenge(sha);
    loadOrgans(sha);
    loadTitanPacket(sha);
    loadBakeCensus(sha);
    loadNamedBuilder(sha);
    loadFleet(sha);
    loadUnusedInvoke(sha);
    loadTakingTrace(sha);
    loadGrokHarness(sha);
    loadVerifyCite(sha);
    loadRenderCheck(sha);
    loadAndroidCi(sha);
    loadStaleSpec(sha);
    loadPixelHeartbeat(sha);
    loadDeviceChurn(sha);
    loadStrandedMap(sha);
    loadPulseBake(sha);
    loadCanaries(sha);
    loadIngestSmash(sha).then(function (ingest) {
      loadPulls(sha, ingest);
    });
    loadComposerTools(sha);
    loadNoAuthDoc(sha);
    var curl = document.getElementById("curl-sha");
    if (curl) curl.textContent = sha;
  }).catch(function (e) {
    if (shaCode) shaCode.textContent = "(api.github.com failed: " + e.message + ")";
    setNote("Could not measure official main from GitHub. Use git ls-remote. A Pages SHA is not current main.");
  });
})(typeof window !== "undefined" ? window : (typeof global !== "undefined" ? global : this));
