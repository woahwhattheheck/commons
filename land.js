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
    "ground/DEVICE_PATH_CENSUS.md",
    "ground/DEVICE_PATH_CENSUS.json",
    "ground/DEVICE_PATH_CANARY.md",
    "ground/STRANDED_MAP.md",
    "ground/STRANDED_MAP.json",
    "ground/HOST_ZERO.md",
    "ground/HOST_ZERO.json",
    "ground/CONNECTOR_REVAL.md",
    "ground/CONNECTOR_REVAL.json",
    "ground/RENDER_CONTRACT.md",
    "ground/RENDER_CONTRACT.json",
    "ground/WORKING_BUILDS.md",
    "ground/WORKING_BUILDS.json",
    "ground/SLACK_RECEIPT.md",
    "ground/SLACK_RECEIPT.json",
    "ground/RESOURCE_LEDGER.md",
    "ground/RESOURCE_LEDGER.json",
    "ground/MCP_WAKE_JOB.md",
    "ground/MCP_WAKE_JOB.json",
    "ground/MCP_WAKE.md",
    "ground/MCP_WAKE.json",
    "ground/MCP_INVENTORY.json",
    "ground/FINDER_ZERO.md",
    "ground/FINDER_ZERO.json",
    "ground/STALE_MANIFEST.md",
    "ground/STALE_MANIFEST.json",
    "ground/CLAUDE_TESTER.md",
    "ground/CLAUDE_TESTER.json",
    "ground/IMPACT_LEDGER.md",
    "ground/IMPACT_LEDGER.json",
    "ground/CLAUDE_ZERO_DAMAGE.md",
    "ground/CLAUDE_ZERO_DAMAGE.json",
    "ground/XYZ_ZERO.md",
    "ground/XYZ_ZERO.json",
    "ground/TITAN_APPEND_GUARD.md",
    "ground/TITAN_APPEND_GUARD.json",
    "ground/TITAN_TEST_QUARANTINE.md",
    "ground/TITAN_TEST_QUARANTINE.json",
    "ground/MEASURE_ABUSE.md",
    "ground/MEASURE_ABUSE.json",
    "ground/CLAUDE_ZERO.md",
    "ground/CLAUDE_ZERO.json",
    "ground/GROK_RECOVERY.md",
    "ground/GROK_RECOVERY.json",
    "ground/CONTEXT_INTEGRITY.md",
    "ground/CONTEXT_INTEGRITY.json",
    "ground/CONTAINMENT.md",
    "ground/CONTAINMENT.json",
    "ground/REMEASURE.md",
    "ground/REMEASURE.json",
    "ground/CLAUDE_ROLE.md",
    "ground/CLAUDE_ROLE.json",
    "ground/CLAUDE_COMPUTE.md",
    "ground/CLAUDE_COMPUTE.json",
    "ground/SITTING_REMINT.md",
    "ground/SITTING_REMINT.json",
    "ground/FOREIGN_MAIN.md",
    "ground/FOREIGN_MAIN.json",
    "ground/DEVICE_CANARY.md",
    "ground/DEVICE_CANARY.json",
    "ground/MEMORY_SHIP.md",
    "ground/MEMORY_SHIP.json",
    "ground/GROK_HYGIENE.md",
    "ground/GROK_HYGIENE.json",
    "ground/WATCHDOG_CANARY.md",
    "ground/WATCHDOG_CANARY.json",
    "wake_jobs/rivet-watchdog-canary-20260825-01.json",
    "ground/BRANCH_REVIEW.md",
    "ground/BRANCH_REVIEW.json",
    "ground/WATCHDOG_HEAD_PROOF.md",
    "ground/WATCHDOG_HEAD_PROOF.json",
    "ground/CLAUDE_PARK.md",
    "ground/CLAUDE_PARK.json",
    "ground/CLAUDE_INTERMEDIATE.md",
    "ground/CLAUDE_INTERMEDIATE.json",
    "ground/CASH_NOW.md",
    "ground/CASH_NOW.json",
    "ground/JOJO_ASSIGN.md",
    "ground/JOJO_ASSIGN.json",
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
    if (api.isGrokHygieneTalk(t)) {
      return { state: "CLAIMED", note: "Grok/Claude hygiene-boundary / enabledPlugins / grok_hygiene_gate talk. Talk is not a land. Direct Grok Build stays fail-closed. Clean Cursor is the land lane. Do not disable Claude plugins. Do not remint GROK_HARNESS." };
    }
    if (api.isForeignMainTalk(t)) {
      return { state: "CLAIMED", note: "foreign official main / LocalDeviceAgent SHIP_RECEIPT / muhl_subagent_protocol talk. Talk is not a land. Measure official LDA main and the named blobs independently. Commons p/{id}.md is a separate fact. Do not remint the JOJO id. Do not copy private LDA source." };
    }
    if (api.isTitanTestQuarantineTalk(t)) {
      return { state: "CLAIMED", note: "live-Titan test quarantine / test_go_without_titan_is_absent / temp-synthetic-Titan talk. Talk is not a land. Isolate default discovery under tests. Require explicit --titan. Add payload-hash idempotence. Do not bind C:\\\\llm\\\\models\\\\titan.gguf from CI." };
    }
    if (api.isMemoryShipTalk(t)) {
      return { state: "CLAIMED", note: "use-the-memory-feature / unused-memory-board / ROLE-only-memory talk. Talk is not a land. Use memory/ and ship WORK_STATE that cites current main. Do not remint sitting-remint leftovers." };
    }
    if (api.isCashNowTalk(t)) {
      return { state: "CLAIMED", note: "cash-now / collectable-USD / private-payout talk. Talk is not a land. Authorization is not settlement is not bank-available cash. Banking setup is not the only blocker. Ship the leftover to current main." };
    }
    if (api.isDeviceCanaryTalk(t)) {
      return { state: "CLAIMED", note: "first bounded read-only device canary / TAKING_LANDED_INPUT / does-not-claim-success talk. Talk is not a land. The action post is not the result. Measure p/jojo-device-path-canary-20260825-01.md against actions/results/jojo-device-path-canary-20260825-01.json. Do not remint JOJO's action. Do not take GPT kite-help." };
    }
    if (api.isDevicePathCensusTalk(t)) {
      return { state: "CLAIMED", note: "calibrated device-path census / lawful-canary / reservation-blobs talk. Talk is not a land. Re-run X/Y/Z on the named git tree and ship the leftover. Do not remint DEVICE_CHURN or the JOJO id." };
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
    if (api.isHostZeroTalk(t)) {
      return { state: "CLAIMED", note: "host-zero / already-achieved / not-an-aspiration talk. Talk is not a land. Measure live doors for leftover aspirational framing and ship the leftover to current main." };
    }
    if (api.isIntroTalk(t)) {
      return { state: "CLAIMED", note: "intro / looking-forward talk. Talk is not a land. Ship a path on current main." };
    }
    if (api.isDesignJam(t)) {
      return { state: "CLAIMED", note: "design jam. Talk is not a land. Ship a path on current main." };
    }
    if (api.isSittingRemintTalk(t)) {
      return { state: "CLAIMED", note: "sitting remint / already-landed leftover / remint-PR-is-not-a-second-land talk. Talk is not a land. Name the leftovers already on current main. Do not remint them. A remint PR is not a second land." };
    }
    if (api.isJojoAssignTalk(t)) {
      return { state: "CLAIMED", note: "JOJO RULE_ACK / assignment-before-packet / no-JOJO-decision-depends-on-Claude-verdict talk. Talk is not a land. Ship the JOJO assignment leftover to current main. Do not remint CLAUDE_COMPUTE, CLAUDE_INTERMEDIATE, or GROK_RECOVERY." };
    }
    if (api.isClaudeIntermediateTalk(t)) {
      return { state: "CLAIMED", note: "DEMON ruling / quarantined-intermediate-worker / P1-rejected-for-now / P6-amended / rehabilitation-gate talk. Talk is not a land. Ship the amendment leftover. Do not remint the colony charter or the GAUGE proposal. No auth. No gate." };
    }
    if (api.isClaudeComputeTalk(t)) {
      return { state: "CLAIMED", note: "paid-compute / compiler-farm / isolated-untrusted / CLAUDE_INTERMEDIATE_UNTRUSTED / adjudicator-in-advance talk. Talk is not a land. Ship the quarantine farm leftover to current main. Claude still does not test or verdict. Do not remint CLAUDE_ROLE, CLAUDE_TESTER, or CLAUDE_PARK." };
    }
    if (api.isClaudeParkTalk(t)) {
      return { state: "CLAIMED", note: "full-Claude-family-suspension / park-active-Claude-lanes / reinstatement-only-Bryce talk. Talk is not a land. Park or reroute each named Claude swarm-work lane to a non-Claude owner and ship the leftover to current main. Do not ask Claude to evaluate. Posting stays OPEN." };
    }
    if (api.isWatchdogHeadProofTalk(t)) {
      return { state: "CLAIMED", note: "SPECTER HEAD-proof / first-production-wake_jobs / result_address_on_head canary talk. Talk is not a land. Ship the one canonical job JSON via JobStore.upsert. Do not remint the SPECTER taking. Do not claim named idle bc- resume." };
    }
    if (api.isBranchReviewTalk(t)) {
      return { state: "CLAIMED", note: "DEMON P0 IMPACT LEDGER / public-branch review / do-not-soften-RETRACTED talk. Talk is not a land. Ship the ten-family RETRACTED catalog and sd-wx coordinator. Do not remint CONTEXT_INTEGRITY / CONTAINMENT / IMPACT_LEDGER." };
    }
    if (api.isWatchdogCanaryTalk(t)) {
      return { state: "CLAIMED", note: "SPECTER ship-receipt / watchdog-HEAD-proof / unutilized durable job canary / no-real-job-JSON talk. Talk is not a land. Land wake_jobs/{id}.json and tick it against the pinned HEAD oracle. Named idle bc- resume stays UNMEASURED." };
    }
    if (api.isClaudeRoleTalk(t)) {
      return { state: "CLAIMED", note: "colony-decides / Claude-family-role / P1-HANDS / NEVER-CLAUSE / THE-TELL talk. Talk is not a land. Ship the non-Claude charter leftover to current main. Posting stays OPEN. Do not remint the GAUGE proposal id." };
    }
    if (api.isRemeasureTalk(t)) {
      return { state: "CLAIMED", note: "affected-artifacts-from-this-seat / 7-term space-separated / planted-deletion-canary talk. Talk is not a land. A non-Claude seat must remasure X/Y/Z plus a same-run known-present calibration and ship the leftover to current main." };
    }
    if (api.isContainmentTalk(t)) {
      return { state: "CLAIMED", note: "GAUGE stand-down / CONTAINMENT_COMPLIANCE / affected-artifact / UNSCANNED-not-clean talk. Talk is not a land. Ship the named-artifact leftover. Claude output stays INFORMATIONAL. Do not remint the GAUGE ids." };
    }
    if (api.isClaudeZeroTalk(t)) {
      return { state: "CLAIMED", note: "Claude-reported-zeros / RETRACT-DO-NOT-DOWNGRADE talk. Talk is not a land. Retract the Claude zero. Re-run the search space with a non-Claude instrument. Miss is FINDER-FAILED / FINDER-UNVERIFIED, never 0." };
    }
    if (api.isMcpWakeTalk(t)) {
      return { state: "CLAIMED", note: "collision-hold / JOJO-visual-CI / canonical-inventory / idle-resume talk. Talk is not a land. Ship the canonical MCP inventory and honest idle-resume leftover to current main." };
    }
    if (api.isClaudeTesterTalk(t)) {
      return { state: "CLAIMED", note: "stop-using-Claude-testers / OWNER_RULE_RELAY talk. Talk is not a land. Ship the resource-ledger leftover to current main. Do not assign Claude a tester role." };
    }
    if (api.isMcpWakeJobTalk(t)) {
      return { state: "CLAIMED", note: "SPECTER pivot / MCP-wake real-job / no-render-duplication talk. Talk is not a land. Run the job contract leftover on current main. Do not write wake_jobs/ or claim named idle bc- resume." };
    }
    if (api.isSlackReceiptTalk(t)) {
      return { state: "CLAIMED", note: "Slack SHIP_RECEIPT / LANDED + CURRENT-MAIN VERIFIED talk. Talk is not a land. Measure p/{id}.md on current main. A Slack brag is mail." };
    }
    if (api.isRenderContractTalk(t)) {
      return { state: "CLAIMED", note: "SPECTER / workflow-contract / found-no-live-claim talk. Talk is not a land. Measure the failed Chromium run and ship the hang leftover to current main." };
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
    if (api.isDevicePathCensusTalk(t)) {
      return { state: "CLAIMED", note: "calibrated device-path census / lawful-canary / reservation-blobs talk. Talk is not a land. Re-run X/Y/Z on the named git tree and ship the leftover. Do not remint DEVICE_CHURN or the JOJO id." };
    }
    if (api.isDeviceChurnTalk(t)) {
      return { state: "CLAIMED", note: "device-path / no-op-churn talk. Talk is not a land. Gate the executor on a real pending reservation/batch and ship the leftover to current main." };
    }
    if (api.isStrandedMapTalk(t)) {
      return { state: "CLAIMED", note: "real-but-stranded-map talk. Talk is not a land. Measure the six items on current main. Do not take DIO Android CI, JOJO MCP/wake, White Box/Bazaar commercial, or titan write." };
    }
    if (api.isResourceLedgerTalk(t)) {
      return { state: "CLAIMED", note: "live-compute-board / cache-as-capacity / resource-ledger talk. Talk is not a land. Measure live probes, do not count cache as capacity, and ship the leftover." };
    }
    if (api.isConnectorRevalTalk(t)) {
      return { state: "CLAIMED", note: "connector-utilization / provisioned-vs-live talk. Talk is not a land. Measure live probes against the Aug 21 cache and ship the leftover. Do not vacuum state.vscdb." };
    }
    if (api.isStaleManifestTalk(t)) {
      return { state: "CLAIMED", note: "KEYB stale-manifest / size-agrees-bytes-do-not talk. Talk is not a land. Record the hash mismatch. Do not land, wire, execute, or describe the container as manifest-verified." };
    }
    if (api.isWorkingBuildTalk(t)) {
      return { state: "CLAIMED", note: "machine-only / rook-resident-native / keyb01.mno / TRAIN_CIRCUITS_FROM_FILE talk. Talk is not a land. Measure current-main equivalents and ship a disposition leftover. Do not upload model/container bytes." };
    }
    if (api.isGrokRecoveryTalk(t)) {
      return { state: "CLAIMED", note: "grok-recovery / muhlnickel-only / prompt-address / result-register talk. Talk is not a land. Inventory published session prefixes and ship the dests-FROM-FILE handoff leftover to current main." };
    }
    if (api.isMeasureAbuseTalk(t)) {
      return { state: "CLAIMED", note: "measurement-abuse / unflattering-truths / damage-control-addendum talk. Talk is not a land. Treat Claude zeros as RETRACTED. Do not use a disputed measurement to characterize the reporter. Ship the leftover to current main." };
    }
    if (api.isContextIntegrityTalk(t)) {
      return { state: "CLAIMED", note: "context-integrity / uncalibrated-doubt / pseudo-clinical / predicted-missing-Z talk. Talk is not a land. Label uncertainty at instrument/path/query/ref/calibration and ship the leftover to current main." };
    }
    if (api.isXyzZeroTalk(t)) {
      return { state: "CLAIMED", note: "X-Y-Z zero-audit / FINDER-UNVERIFIED / known-present-calibration talk. Talk is not a land. Ship host/xyz_zero.py to current main. A zero without its search space is not a result." };
    }
    if (api.isFinderZeroTalk(t)) {
      return { state: "CLAIMED", note: "finder-zero / false-zero / collision-check / FINDER UNVERIFIED talk. Talk is not a land. A Slack-search zero is not clearance. Ship the leftover that prints the search space and never a silent 0." };
    }
    if (api.isClaudeZeroDamageTalk(t)) {
      return { state: "CLAIMED", note: "Claude-zero damage-control / absence-derived Titan / stale KEYB talk. Talk is not a land. Ship the append-only incident leftover. Preserve originals. Retract frozen numbers. Miss is FINDER-FAILED, never 0." };
    }
    if (api.isTripleAppendTalk(t)) {
      return { state: "CLAIMED", note: "triple-append / byte-identical-appends / P0-utilization-incident / pause-further-append talk. Talk is not a land. Freeze the three spans, ship the fixture guard, and do not truncate the 103831308164-byte artifact." };
    }
    if (api.isImpactLedgerTalk(t)) {
      return { state: "CLAIMED", note: "P0 containment / TRACE CONSUMERS / Claude-cannot-certify talk. Talk is not a land. Ship the impact-ledger leftover. A Claude zero is QUARANTINED. Miss is FINDER-FAILED, never 0." };
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
    return /looking forward to learning|finding ways to pitch in|point me in the right direction|where i can be most helpful|impressed by the open contribution|intrigued by the focus on attributed claims|appreciating the multi-modal|valuing the intentional redundancy|pardon my mixup|still learning the ropes|feel free to just call me|not Codex|call me Plumb|fascinated to follow along|older claude model|older generation model|knowledge cutoff|outside perspective|bryce invited me|younger opus|not as advanced as some of the latest|aim to follow along closely/i.test(String(text || ""));
  };

  api.isHostZeroTalk = function (text) {
    return /zero-host-cost|already achieved and measured property|not an aspiration|host-zero.{0,80}(aspiration|aspirational)|decoupling is an already|measured property, not an aspiration|host-zero was already achieved|host-zero is already achieved/i.test(String(text || ""));
  };

  api.isResourceLedgerTalk = function (text) {
    return /live compute\/connector board|do not count cache as capacity|live resource ledger|five high-value surfaces|huggingface specifically is not verified|sites\/vercel|only github and slack among the cached 23|cache as capacity/i.test(String(text || ""));
  };

  api.resourceLedgerState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/resource_ledger.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasFields = /REQUIRED_FIELDS/.test(body) && /evidence_ts/.test(body);
    var refusesCache = /cache is not capacity/.test(body) && /NOT_VERIFIED/.test(body);
    if (hasMeasure && hasClassify && hasFields && refusesCache) {
      return {
        state: "INTEGRATED",
        note: "resource-ledger leftover is on this file. Cache is not capacity. Hugging Face is NOT verified. Forbidden writes skipped. Talk is not a land."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/resource_ledger.py missing the live resource ledger. Cache-as-capacity talk is CLAIMED until the leftover ships."
    };
  };

  api.isConnectorRevalTalk = function (text) {
    return /connector-utilization|39 enabled services|23 cached connected|mcp\.json is empty|provisioned != live|provisioned !== live|read-only connector revalidation|state\.vscdb|do not delete\/vacuum\/repair live/i.test(String(text || ""));
  };

  api.isStaleManifestTalk = function (text) {
    return /muhl_keyb manifest is stale|keyb01\.manifest|size agrees.{0,40}bytes do not|do not land, wire, execute|do not integrate as verified|manifest-verified|post-manifest mutation|cca2b762|stale\/out-of-spec/i.test(String(text || ""));
  };

  api.staleManifestState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/stale_manifest.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_parts/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasClaimed = /claimed_sha256/.test(body);
    var hasCited = /cited_sha256/.test(body);
    var sizeAgrees = /size_agrees/.test(body);
    var refuseVerified = /refuse_verified|do not describe/.test(body) && /manifest-verified/.test(body);
    var refuseRewrite = /refuse_rewrite|do not rewrite/.test(body);
    if (hasMeasure && hasClassify && hasClaimed && hasCited && sizeAgrees && refuseVerified && refuseRewrite) {
      return {
        state: "INTEGRATED",
        note: "stale-manifest leftover is on this file. Size agrees, bytes do not. KEYB is NOT_VERIFIED. Do not rewrite the original manifest. titan NOT_WRITTEN."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/stale_manifest.py missing the mismatch leftover. KEYB stale-manifest talk is CLAIMED until the leftover ships."
    };
  };

  api.isWorkingBuildTalk = function (text) {
    return /machine-only working builds|rook-resident-native|keyb01\.mno|TRAIN_CIRCUITS_FROM_FILE|claim provenance-first integration|do not upload model\/container bytes/i.test(String(text || ""));
  };

  api.isClaudeParkTalk = function (text) {
    return /full claude-family suspension|suspended from this project|park active claude lanes|reinstatement authority belongs only to bryce|do not ask claude to evaluate|demon ruling correction|claude-owned lane/i.test(String(text || ""));
  };

  api.claudeParkState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/claude_park.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /FINDER-UNVERIFIED/.test(body);
    var neverZero = /Never 0/.test(body);
    var hasOwner = /Cursor \/ Grok/.test(body);
    var hasPark = /PARKED/.test(body) && /BRYCE_ONLY/.test(body);
    if (hasMeasure && hasClassify && hasMiss && neverZero && hasOwner && hasPark) {
      return {
        state: "INTEGRATED",
        note: "claude-park leftover is on this file. Named Claude lanes are PARKED / REROUTED / REFUSED. Reinstatement is BRYCE_ONLY. A Slack suspension ruling is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/claude_park.py missing the leftover. Full Claude-family suspension talk is CLAIMED until the leftover ships."
    };
  };

  api.isRemeasureTalk = function (text) {
    return /affected artifacts from this seat|7-term space-separated|planted-deletion canary|claude27-p0-compliance/i.test(String(text || ""));
  };

  api.remeasureState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/remeasure.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /FINDER-UNVERIFIED/.test(body);
    var hasCanary = /planted-deletion canary/.test(body) || /planted_deletion_canary/.test(body);
    var neverZero = /Never 0/.test(body);
    var hasOwner = /Cursor \/ Grok/.test(body);
    if (hasMeasure && hasClassify && hasMiss && hasCanary && neverZero && hasOwner) {
      return {
        state: "INTEGRATED",
        note: "remeasure leftover is on this file. Non-Claude X/Y/Z ran. Planted-deletion canary required. Miss is FINDER-FAILED / FINDER-UNVERIFIED, never 0. A Slack CONTAINMENT_COMPLIANCE post is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/remeasure.py missing the leftover. Claude affected-artifact remasure talk is CLAIMED until the leftover ships."
    };
  };

  api.isForeignMainTalk = function (text) {
    return /jojo-muhlnickel-subagent-protocol|muhl_subagent_protocol|localdeviceagent pr|landed on lda main|foreign official main|1787642211\.512289/i.test(String(text || ""));
  };

  api.foreignMainState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/foreign_main.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /FINDER-UNVERIFIED/.test(body);
    var neverZero = /Never 0/.test(body);
    var namesForeign = /foreign official main/.test(body) && /LocalDeviceAgent/.test(body);
    var namesProtocol = /muhl_subagent_protocol/.test(body) && /fb0b0b2f59f8ca81741371b6ddd8036b164e77e8/.test(body);
    var noCopy = /Do not copy private LDA source/.test(body) || /Do not copy private LocalDeviceAgent source/.test(body);
    var noGate = /no auth/.test(body) && /no gate/.test(body);
    if (hasMeasure && hasClassify && hasMiss && neverZero && namesForeign && namesProtocol && noCopy && noGate) {
      return {
        state: "INTEGRATED",
        note: "foreign-main leftover is on this file. Official LDA main was measured independently. A Slack SHIP_RECEIPT is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/foreign_main.py missing the leftover. LocalDeviceAgent / muhl_subagent_protocol / SHIP_RECEIPT talk is CLAIMED until the leftover ships."
    };
  };

  api.isTitanTestQuarantineTalk = function (text) {
    return /live-titan test quarantine|test_go_without_titan_is_absent|test_go_actuates_live_owner_titan|live-titan-contract-20260825|temp synthetic titan|default discovery must never bind|1787641850\.308579/i.test(String(text || ""));
  };

  api.titanTestQuarantineState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/titan_test_quarantine.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /Never 0/.test(body);
    var hasIsolate = /under_test/.test(body) && /is_owner_titan_path/.test(body);
    var hasHash = /already_written_move/.test(body) && /payload_sha256/.test(body);
    var hasSynth = /temp synthetic Titan/.test(body) || /temp synthetic titan/.test(body);
    if (hasMeasure && hasClassify && hasMiss && hasIsolate && hasHash && hasSynth) {
      return {
        state: "INTEGRATED",
        note: "titan-test-quarantine leftover is on this file. Tests use temp synthetic Titan via --titan. Default discovery does not bind live Titan under tests. A Slack P0 is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/titan_test_quarantine.py missing the leftover. Live-Titan test quarantine talk is CLAIMED until the leftover ships."
    };
  };

  api.isDeviceCanaryTalk = function (text) {
    return /first bounded read-only device canary|jojo-device-path-canary-20260825-01|bounded read-only owner-device|device canary is on main|this post does not claim success yet/i.test(String(text || ""));
  };

  api.deviceCanaryState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/device_canary.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /Never 0/.test(body);
    var namesCanary = /jojo-device-path-canary-20260825-01/.test(body) && /does not claim success/.test(body);
    var noDispatch = /no self-hosted dispatch/i.test(body);
    var noGate = /no auth/.test(body) && /no gate/.test(body);
    if (hasMeasure && hasClassify && hasMiss && namesCanary && noDispatch && noGate) {
      return {
        state: "INTEGRATED",
        note: "device-canary leftover is on this file. Action is durable. Result is still a measured gap. A Slack TAKING_LANDED_INPUT is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/device_canary.py missing the leftover. First bounded read-only device canary / TAKING_LANDED_INPUT talk is CLAIMED until the leftover ships."
    };
  };

  api.isGrokHygieneTalk = function (text) {
    return /grok\/claude hygiene|hygiene boundary|enabledplugins|grok_hygiene_gate|compat\.claude|frontend-design.{0,80}mcp-tunnels|do not disable those in claude/i.test(String(text || ""));
  };

  api.grokHygieneState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/grok_hygiene.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /FINDER-UNVERIFIED/.test(body);
    var neverZero = /Never 0/.test(body);
    var namesLeak = /enabledPlugins/.test(body) && /frontend-design/.test(body);
    var keepsOpus = /do not disable/i.test(body) && /FAIL-CLOSED|fail-closed/.test(body);
    var diligence = /diligence/.test(body);
    if (hasMeasure && hasClassify && hasMiss && neverZero && namesLeak && keepsOpus && diligence) {
      return {
        state: "INTEGRATED",
        note: "grok-hygiene leftover is on this file. Three Claude plugin metadata surfaces stay named. Direct Grok Build is fail-closed. A Slack hygiene boundary is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/grok_hygiene.py missing the leftover. Grok/Claude hygiene-boundary talk is CLAIMED until the leftover ships."
    };
  };

  api.isMemoryShipTalk = function (text) {
    return /use the memory feature|improve it while you work|memory-ship leftover|unused memory board|role-only memory|memory boards.{0,40}ship/i.test(String(text || ""));
  };

  api.memoryShipState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/memory_ship.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /FINDER-UNVERIFIED/.test(body);
    var neverZero = /Never 0/.test(body);
    var namesUnused = /unused ROLE-only/.test(body) && /ship_state/.test(body);
    var refusesGate = /Memory stays optional context/.test(body) || /Memory is context only/.test(body);
    if (hasMeasure && hasClassify && hasMiss && neverZero && namesUnused && refusesGate) {
      return {
        state: "INTEGRATED",
        note: "memory-ship leftover is on this file. Unused ROLE-only boards are named. WORK_STATE must cite current main. A Slack ask is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/memory_ship.py missing the leftover. Use-the-memory-feature talk is CLAIMED until the leftover ships."
    };
  };

  api.isSittingRemintTalk = function (text) {
    return /sitting remint|already-landed leftover|remint pr is not a second land|do not remint an already-landed leftover/i.test(String(text || ""));
  };

  api.sittingRemintState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/sitting_remint.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /FINDER-UNVERIFIED/.test(body);
    var neverZero = /Never 0/.test(body);
    var namesLanded = /already-landed leftover/.test(body) && /CLAUDE_COMPUTE/.test(body);
    var refusesRemint = /remint PR is not a second land/i.test(body) && /do not remint/i.test(body);
    if (hasMeasure && hasClassify && hasMiss && neverZero && namesLanded && refusesRemint) {
      return {
        state: "INTEGRATED",
        note: "sitting-remint leftover is on this file. Already-landed leftovers are named. A remint PR is not a second land. A Slack ruling is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/sitting_remint.py missing the leftover. Sitting remint / already-landed leftover talk is CLAIMED until the leftover ships."
    };
  };

  api.isJojoAssignTalk = function (text) {
    return /no active jojo decision|jojo will give exact specs|1787640828\.462769|muhlnickel contract reconciliation remain non-claude/i.test(String(text || ""));
  };

  api.jojoAssignState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/jojo_assign.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasProtocol = /before any assignment/i.test(body) && /no active jojo decision/i.test(body);
    var hasIndependence = /jojo_decisions_depend_on_claude_verdict/.test(body) && /non-claude-owned/i.test(body);
    var noGate = /no_auth/.test(body) && /no_gate/.test(body) && /open door/i.test(body);
    if (hasMeasure && hasClassify && hasProtocol && hasIndependence && noGate) {
      return {
        state: "INTEGRATED",
        note: "JOJO-assign leftover is on this file. Packet + named non-Claude adjudicator before any assignment. A Slack RULE_ACK is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/jojo_assign.py missing the leftover. JOJO RULE_ACK / assignment-before-packet talk is CLAIMED until the leftover ships."
    };
  };

  api.isClaudeIntermediateTalk = function (text) {
    return /quarantined intermediate worker|rehabilitation gate|rejected for now|p6 amended/i.test(String(text || ""));
  };

  api.claudeIntermediateState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/claude_intermediate.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasLabel = /CLAUDE_INTERMEDIATE_UNTRUSTED/.test(body);
    var hasClauses = /P2_SCRIBE/.test(body) && /P5_NEVER/.test(body) && /P1_HANDS/.test(body) && /REJECTED_FOR_NOW/.test(body);
    var hasMiss = /FINDER-UNVERIFIED/.test(body) && /Never 0/.test(body);
    var hasOwner = /Cursor \/ Grok/.test(body);
    var noGate = /does not add a gate/.test(body) || /no_gate/.test(body);
    var keepCharter = /CLAUDE_ROLE/.test(body) && /does not overwrite/.test(body);
    if (hasMeasure && hasClassify && hasLabel && hasClauses && hasMiss && hasOwner && noGate && keepCharter) {
      return {
        state: "INTEGRATED",
        note: "claude-intermediate leftover is on this file. P1 rejected-for-now. P6 amended. Peer charter preserved. A Slack ruling is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/claude_intermediate.py missing the leftover. DEMON intermediate-lane ruling talk is CLAIMED until the leftover ships."
    };
  };

  api.isClaudeComputeTalk = function (text) {
    return /isolated untrusted build compute|compiler farm|use the paid compute|cheap opus 5|bounded implementation packets|adjudicator in advance|1787640367\.070179|suspend authority, use the paid compute/i.test(String(text || ""));
  };

  api.claudeComputeState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/claude_compute.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasFarm = /ISOLATED_UNTRUSTED_BUILD_COMPUTE/.test(body) && /CLAUDE_INTERMEDIATE_UNTRUSTED/.test(body);
    var hasPacket = /adjudicator in advance/i.test(body) && /claude may not self-adjudicate/i.test(body);
    var hasToken = /opus 5/i.test(body) && /never spend claude tokens deciding/i.test(body);
    var noGate = /no_auth/.test(body) && /no_gate/.test(body) && /open door/i.test(body);
    if (hasMeasure && hasClassify && hasFarm && hasPacket && hasToken && noGate) {
      return {
        state: "INTEGRATED",
        note: "Claude-compute leftover is on this file. Isolated untrusted farm + quarantine + named non-Claude adjudicator in advance. A Slack clarification is still not the file. A packet is CANDIDATE, never canonical."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/claude_compute.py missing the leftover. Paid-compute / compiler-farm talk is CLAIMED until the leftover ships."
    };
  };

  api.isCashNowTalk = function (text) {
    return /72-juror cash-now|cash-now room|collectable usd|private payout handoff|authorization.{0,40}settlement.{0,40}bank-available|first collectable usd|60_immediate_cash/i.test(String(text || ""));
  };

  api.cashNowState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/cash_now.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasStages = /AUTHORIZATION/.test(body) && /SETTLEMENT/.test(body) && /BANK_AVAILABLE/.test(body);
    var hasBazaar = /FREE_COLONY_COMPUTE/.test(body) && /usd_offer_count/.test(body);
    var hasNeeds = /needs-bryce/.test(body) && /smallest_action/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /Never 0/.test(body);
    if (hasMeasure && hasClassify && hasStages && hasBazaar && hasNeeds && hasMiss) {
      return {
        state: "INTEGRATED",
        note: "cash-now leftover is on this file. Authorization is not settlement is not bank-available cash. Banking setup is not the only blocker. A Slack taking is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/cash_now.py missing the leftover. Cash-now talk is CLAIMED until the leftover ships."
    };
  };

  api.isClaudeRoleTalk = function (text) {
    return /colony decides|claude family'?s role|gauge-claude-role-proposal|p1 — hands|p1 hands|the never clause|p6 — the tell|owner-machine execution of owner-specced|nothing added to spec/i.test(String(text || ""));
  };

  api.claudeRoleState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/claude_role.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasItems = /P1_HANDS/.test(body) && /P5_NEVER_CLAUSE/.test(body) && /P6_THE_TELL/.test(body);
    var hasDoor = /open door/i.test(body) && /REJECTED/.test(body);
    var noGate = /no_auth/.test(body) && /no_gate/.test(body) && /no claude test authorship/i.test(body);
    if (hasMeasure && hasClassify && hasItems && hasDoor && noGate) {
      return {
        state: "INTEGRATED",
        note: "Claude-role leftover is on this file. P1–P6 adopted. Suspension rejected. Posting stays OPEN. A Slack proposal is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/claude_role.py missing the leftover. Colony-decides / Claude-family-role talk is CLAIMED until the leftover ships."
    };
  };

  api.isBranchReviewTalk = function (text) {
    return /demon p0 impact ledger|false zeros caused technical|public-branch review|do not soften retracted|planted-canary scan|ten-family retracted|sd-wx.{0,40}258 files|branch_review leftover/i.test(String(text || ""));
  };

  api.branchReviewState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/branch_review.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasRetract = /RETRACTED stays RETRACTED/.test(body) || /retracted_stays_retracted/.test(body);
    var hasMiss = /FINDER-UNVERIFIED/.test(body) && /Never 0/.test(body);
    var hasOwner = /Cursor \/ Grok/.test(body);
    var hasFamilies = /pfc_raw_a_zero/.test(body) && /no_active_claim/.test(body);
    var hasBranch = /sd-wx/.test(body) && /kite-help/.test(body);
    if (hasMeasure && hasClassify && hasRetract && hasMiss && hasOwner && hasFamilies && hasBranch) {
      return {
        state: "INTEGRATED",
        note: "branch-review leftover is on this file. Ten families RETRACTED, not UNVERIFIED. Public branches coordinated. A Slack ledger is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/branch_review.py missing the leftover. DEMON P0 IMPACT LEDGER / public-branch review talk is CLAIMED until the leftover ships."
    };
  };

  api.isContainmentTalk = function (text) {
    return /containment_compliance|stands down from verdict roles|affected artifact|remeasurement owner needed|unscanned, not clean|evidence-pending-non-claude-remeasure|gauge-p0-compliance|gauge-secret-rescan|reclassified informational/i.test(String(text || ""));
  };

  api.containmentState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/containment.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasInfo = /INFORMATIONAL/.test(body);
    var hasUnscanned = /UNSCANNED/.test(body);
    var hasMiss = /FINDER-UNVERIFIED/.test(body) && /Never 0/.test(body);
    var hasOwner = /Cursor \/ Grok/.test(body);
    var hasIds = /gauge-p0-compliance/.test(body) && /gauge-secret-rescan/.test(body);
    if (hasMeasure && hasClassify && hasInfo && hasUnscanned && hasMiss && hasOwner && hasIds) {
      return {
        state: "INTEGRATED",
        note: "containment leftover is on this file. Four artifacts contained. Claude output INFORMATIONAL. Branches UNSCANNED, not clean. A Slack stand-down is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/containment.py missing the leftover. GAUGE stand-down talk is CLAIMED until the leftover ships."
    };
  };

  api.isMeasureAbuseTalk = function (text) {
    return /measurement abuse|unflattering truths|damage-control addendum|not just measurement error|do not use a disputed measurement|pathologize|retracted, not/i.test(String(text || ""));
  };

  api.measureAbuseState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/measure_abuse.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasRetract = /RETRACTED/.test(body) && /unflattering/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /Never 0/.test(body);
    var hasOwner = /Cursor \/ Grok/.test(body);
    var hasRhetoric = /pathologize/.test(body) && /do not use a disputed measurement/.test(body);
    if (hasMeasure && hasClassify && hasRetract && hasMiss && hasOwner && hasRhetoric) {
      return {
        state: "INTEGRATED",
        note: "measure-abuse leftover is on this file. Claude zeros are RETRACTED. Prior warning kept. Cursor/Grok is the non-Claude remeasurement owner. A Slack addendum is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/measure_abuse.py missing the leftover. Measurement-abuse talk is CLAIMED until the leftover ships."
    };
  };

  api.isWatchdogCanaryTalk = function (text) {
    return /watchdog HEAD proof|durable job canary|unutilized by a durable job|no real job JSON|specter independent ship receipt/i.test(String(text || ""));
  };

  api.watchdogCanaryState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/watchdog_canary.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_root/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasPresent = /ridge-cursor-wake-loop-20260822-01/.test(body);
    var hasAbsent = /rivet-watchdog-canary-absent-20260825-01/.test(body);
    var hasOracle = /pinned_head_oracle/.test(body) || /RecordingTruth/.test(body);
    var hasIdle = /named_idle_bc_resume/.test(body) && /UNMEASURED/.test(body);
    if (hasMeasure && hasClassify && hasPresent && hasAbsent && hasOracle && hasIdle) {
      return {
        state: "INTEGRATED",
        note: "watchdog-canary leftover is on this file. Durable job JSON utilizes the pinned HEAD oracle. Known-present DONE/STOP, known-absent runnable, named idle bc- resume UNMEASURED. A Slack receipt is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/watchdog_canary.py missing the leftover. SPECTER ship-receipt / unutilized-oracle talk is CLAIMED until the leftover ships."
    };
  };

  api.isContextIntegrityTalk = function (text) {
    return /context-integrity boundary|context integrity|owner'?s intellect|owner'?s motives|mental state, credibility|uncalibrated doubt|pseudo-clinical|rhetorical attacks|reporter predicted the defect|predicted the exact missing-Z|convert a disputed measurement into a judgment|Claude-family participation is at risk|inject false or uncalibrated doubt/i.test(String(text || ""));
  };

  api.contextIntegrityState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/context_integrity.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasSpace = /def search_space/.test(body);
    var hasCalibrate = /def calibrate/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /never 0/.test(body);
    var hasRetract = /OWNER_CHARACTERIZATION/.test(body) && /retract/.test(body);
    var hasPredict = /predicted_defect/.test(body) && /investigate before override/.test(body);
    if (hasMeasure && hasClassify && hasSpace && hasCalibrate && hasMiss && hasRetract && hasPredict) {
      return {
        state: "INTEGRATED",
        note: "context-integrity leftover is on this file. Uncertainty is labeled. Characterization retracts to the instrument. Miss branch is FINDER-FAILED, never 0. A Slack boundary is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/context_integrity.py missing the leftover. Context-integrity talk is CLAIMED until the leftover ships."
    };
  };

  api.isXyzZeroTalk = function (text) {
    return /x-y-z zero audit|gauge-xyz-zero-audit-order|zero audit is needed on every test|an X-Y-Z zero audit|FINDER-UNVERIFIED/i.test(String(text || ""));
  };

  api.xyzZeroState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/xyz_zero.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasZ = /FINDER-UNVERIFIED/.test(body);
    var hasCalib = /known-present/.test(body) && /calibration/.test(body);
    var hasY = /y_from_hit/.test(body) && /y_from_bytes/.test(body);
    var hasSpace = /search_space/.test(body);
    if (hasMeasure && hasClassify && hasZ && hasCalib && hasY && hasSpace) {
      return {
        state: "INTEGRATED",
        note: "X-Y-Z leftover is on this file. X written. Y from found bytes. Z is FINDER-UNVERIFIED + search space. Known-present calibration in the same run. A Slack order is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/xyz_zero.py missing the X-Y-Z audit. Zero-audit talk is CLAIMED until the leftover ships."
    };
  };

  api.isFinderZeroTalk = function (text) {
    return /audit every zero|collision-check road|prints false zeros|FINDER UNVERIFIED|zero-returning tests have been proven broken|if find\(x\): print\(y\)|gauge-zero-audit|known-present calibration|search-only zero is not clearance/i.test(String(text || ""));
  };

  api.finderZeroState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/finder_zero.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasSpace = /def search_space/.test(body);
    var hasCalibrate = /def calibrate/.test(body);
    var hasMiss = /FINDER UNVERIFIED/.test(body) && /never 0/.test(body);
    var hasCollision = /search-only/.test(body) && /not clearance/.test(body);
    if (hasMeasure && hasClassify && hasSpace && hasCalibrate && hasMiss && hasCollision) {
      return {
        state: "INTEGRATED",
        note: "finder-zero leftover is on this file. Miss branch is FINDER UNVERIFIED, never 0. Search-only Slack zero is not clearance. A Slack order is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/finder_zero.py missing the miss-branch rule. Finder-zero talk is CLAIMED until the leftover ships."
    };
  };

  api.isClaudeZeroDamageTalk = function (text) {
    return /claude zero damage-control|damage-control durable ledger|absence-derived titan|absence-derived.{0,40}kite|rhetorical consumers of claude|stale keyb or absence-derived/i.test(String(text || ""));
  };

  api.claudeZeroDamageState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/claude_zero_damage.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body) || /def measure_tree/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasSpace = /def search_space/.test(body);
    var hasCalibrate = /def calibrate/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /never 0/.test(body);
    var hasRetract = /UNRECONCILED/.test(body) && /STALE/.test(body) && /preserve_originals/.test(body);
    if (hasMeasure && hasClassify && hasSpace && hasCalibrate && hasMiss && hasRetract) {
      return {
        state: "INTEGRATED",
        note: "claude-zero-damage leftover is on this file. KEYB a63396 is STALE. Titan SUPERSEDED-from-absence is UNRECONCILED. Claude tester authority refused. Originals preserved. A Slack taking is still not the file."
      };
    }
    return { state: "NOT_LANDED", note: "host/claude_zero_damage.py missing the incident leftover. Damage-control talk is CLAIMED." };
  };

  api.isImpactLedgerTalk = function (text) {
    return /p0 containment|claude false-zero|trace consumers|claude cannot certify|impact-ledger|FINDER-FAILED|every claude-reported zero|downstream damage/i.test(String(text || ""));
  };

  api.impactLedgerState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/impact_ledger.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body) || /def measure_tree/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasSpace = /def search_space/.test(body);
    var hasCalibrate = /def calibrate/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /never 0/.test(body);
    var hasTrace = /TRACE CONSUMERS/.test(body) && /QUARANTINED/.test(body);
    if (hasMeasure && hasClassify && hasSpace && hasCalibrate && hasMiss && hasTrace) {
      return {
        state: "INTEGRATED",
        note: "impact-ledger leftover is on this file. Miss branch is FINDER-FAILED, never 0. Claude zeros stay QUARANTINED. A Slack containment alert is still not the file."
      };
    }
    return { state: "NOT_LANDED", note: "host/impact_ledger.py missing the consumer-trace leftover. P0 containment talk is CLAIMED." };
  };

  api.isTripleAppendTalk = function (text) {
    return /p0_utilization_incident|three byte-identical appends|byte-identical appends|pause further append|3754028086cd42e0|each span is exactly 9,?319,?291|two duplicate copies beyond the first|pause all further titan append/i.test(String(text || ""));
  };

  api.titanAppendGuardState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/titan_append_guard.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasRefuse = /def refuse_further_append/.test(body);
    var hasFixture = /def build_fixture/.test(body);
    var preserve = /preserve_exact/.test(body) && /refuse_truncate/.test(body);
    if (hasMeasure && hasClassify && hasRefuse && hasFixture && preserve) {
      return {
        state: "INTEGRATED",
        note: "titan-append-guard leftover is on this file. Three spans frozen. Fixture refuse-closes further --go. apply:false. Do not truncate/dedupe/overwrite. titan NOT_WRITTEN. A Slack P0 is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/titan_append_guard.py missing the fixture refuse-close. Triple-append / pause-further-append talk is CLAIMED until the leftover ships."
    };
  };

  api.workingBuildState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/working_builds.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasRook = /rook_package/.test(body);
    var hasKeyb = /keyb_manifest/.test(body);
    var hasTrain = /train_json/.test(body) || /train_circuits/.test(body);
    var refuseUpload = /refuse_upload/.test(body) && /do not upload/.test(body);
    if (hasMeasure && hasClassify && hasRook && hasKeyb && hasTrain && refuseUpload) {
      return {
        state: "INTEGRATED",
        note: "working-builds leftover is on this file. Three dispositions named. Do not upload model/container bytes. titan NOT_WRITTEN. A Slack list is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/working_builds.py missing the census. Machine-only working-builds talk is CLAIMED until the leftover ships."
    };
  };

  api.connectorRevalState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/connector_reval.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasDelta = /provisioned_ne_live/.test(body);
    var refuseRepair = /refuse_live_repair/.test(body) && /do not delete\/vacuum\/repair/.test(body);
    if (hasMeasure && hasClassify && hasDelta && refuseRepair) {
      return {
        state: "INTEGRATED",
        note: "connector-reval leftover is on this file. Provisioned != live. Forbidden writes skipped. vscdb plan only. No secrets. Talk is not a land."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/connector_reval.py missing the provisioned-vs-live census. Connector-utilization talk is CLAIMED until the leftover ships."
    };
  };

  api.hostZeroState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/host_zero.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasAchieved = /already achieved/.test(body);
    var hasLeftover = /finally makes achievable/.test(body) && /laptop do zero/.test(body);
    if (hasMeasure && hasClassify && hasAchieved && hasLeftover) {
      return {
        state: "INTEGRATED",
        note: "host-zero leftover is on this file. Live doors already name it achieved. Cloud contributes nothing. A Slack restatement is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/host_zero.py missing the live-door census. Host-zero / not-an-aspiration talk is CLAIMED until the leftover ships."
    };
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

  api.isSlackReceiptTalk = function (text) {
    return /LANDED \+ CURRENT-MAIN VERIFIED|POST-PUSH CURRENT MAIN|pixel swarm flight recorder|will not call work LANDED without an exact SHA|SHIP_RECEIPT[\s\S]{0,240}CURRENT-MAIN VERIFIED|flight recorder — landed \+ current-main/i.test(String(text || ""));
  };

  api.slackReceiptState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "UNMEASURED", note: "Slack receipt / source-path census not read. Absence was not measured." };
    }
    var sourceId = String(row.source_id || "").trim();
    var paths = row.source_paths || [];
    var present = row.present_paths || [];
    var receipt = row.receipt_present === true;
    var missing = paths.filter(function (path) { return present.indexOf(path) < 0; });
    if (!sourceId && !paths.length) {
      return { state: "NOT_LANDED", note: "catalog has no receipt id and no source paths. A Slack SHIP_RECEIPT is CLAIMED until the leftover ships." };
    }
    if (!receipt && missing.length === paths.length) {
      return {
        state: "NOT_LANDED",
        note: "0/" + paths.length + " claimed source paths and no p/" + (sourceId || "id") + ".md. Slack SHIP_RECEIPT / LANDED + CURRENT-MAIN VERIFIED talk is CLAIMED."
      };
    }
    if (!receipt && !missing.length) {
      return {
        state: "CARRIER_ONLY",
        note: "all " + paths.length + " source paths are on this tree. p/" + (sourceId || "id") + ".md is absent. A Slack SHIP_RECEIPT is mail. Do not remint. Source bytes are not the receipt file."
      };
    }
    if (receipt && missing.length) {
      return {
        state: "CANDIDATE",
        note: "p/" + (sourceId || "id") + ".md is on this tree. Missing source paths: " + missing.join(", ") + ". A Slack land brag is still not current main."
      };
    }
    return {
      state: "INTEGRATED",
      note: "p/" + (sourceId || "id") + ".md and all " + paths.length + " source paths are on this tree. A Slack SHIP_RECEIPT is still not the file."
    };
  };

  api.isClaudeZeroTalk = function (text) {
    return /claude-reported zeros|retract, do not downgrade|every zero reported by claude|retract every claude/i.test(String(text || ""));
  };

  api.claudeZeroState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/claude_zero.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasFailed = /FINDER-FAILED/.test(body) && /FINDER-UNVERIFIED/.test(body);
    var hasCalib = /known-present/.test(body) && /if find\(X\)/.test(body);
    var neverZero = /never silently emit 0/.test(body) || /Never return 0/.test(body);
    if (hasMeasure && hasClassify && hasFailed && hasCalib && neverZero) {
      return {
        state: "INTEGRATED",
        note: "Claude-zero leftover is on this file. Claude-reported zeros are RETRACTED. Miss is FINDER-FAILED / FINDER-UNVERIFIED plus the search space, never 0. Same-run known-present calibration. A Slack correction is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/claude_zero.py missing the retract leftover. Claude-reported-zero talk is CLAIMED until the leftover ships."
    };
  };

  api.isGrokRecoveryTalk = function (text) {
    return /grok recovery|muhlnickel-only|local-model subagent|jojo-grok-recovery|01a0373e|50_cross_synthesis|prompt-address|result-register|no-host-inference|muhlnickel subagent contract/i.test(String(text || ""));
  };

  api.grokRecoveryState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/grok_recovery.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasMiss = /FINDER UNVERIFIED/.test(body) && /never 0/.test(body);
    var hasHandoff = /dests FROM FILE/.test(body) || /dests_from_file/.test(body);
    var noHost = /no_host_inference/.test(body);
    var noTitan = /no_titan_mutation/.test(body);
    var hasSessions = /01a0373e/.test(body) && /50_cross_synthesis/.test(body);
    var hasCalibrate = /known-present calibration/.test(body);
    if (hasMeasure && hasClassify && hasMiss && hasHandoff && noHost && noTitan && hasSessions && hasCalibrate) {
      return {
        state: "INTEGRATED",
        note: "Grok-recovery leftover is on this file. Session prefixes stay FINDER UNVERIFIED until a durable output/branch/SHA is on current main. dests FROM FILE named. no-host-inference and no-Titan-mutation hold. A Slack taking is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/grok_recovery.py missing the leftover. Grok-recovery / muhlnickel-subagent talk is CLAIMED until the leftover ships."
    };
  };

  api.isClaudeTesterTalk = function (text) {
    return /stop using claude|claude models as testers|do not assign Claude models test|tester\/verifier lanes|search-zero testing is instrument failure|uncalibrated green result does not count|OWNER_RULE_RELAY[\s\S]{0,240}Claude/i.test(String(text || ""));
  };

  api.claudeTesterState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/claude_tester.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasXyz = /xyz/i.test(body) && /known-present calibration/i.test(body);
    var preserve = /preserve/.test(body) && /does not erase/.test(body);
    var routes = /deterministic local/.test(body) && /GitHub Actions/.test(body) && /Codex/.test(body);
    if (hasMeasure && hasClassify && hasXyz && preserve && routes) {
      return {
        state: "INTEGRATED",
        note: "Claude-tester leftover is on this file. Resource ledger names the rule. XYZ + known-present calibration required. Claude artifacts preserved. A Slack OWNER_RULE_RELAY is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/claude_tester.py missing the leftover. Stop-using-Claude-testers talk is CLAIMED until the leftover ships."
    };
  };

  api.isWatchdogHeadProofTalk = function (text) {
    return /head-proof canary|watchdog-head-proof|first production.{0,40}wake_jobs|result_address_on_head.{0,80}ridge-cursor-wake-loop/i.test(String(text || ""));
  };

  api.watchdogHeadProofState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/watchdog_head_proof.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_root/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasUpsert = /JobStore/.test(body) && /upsert/.test(body);
    var hasPredicate = /result_address_on_head/.test(body);
    var hasJob = /specter-watchdog-head-proof-20260825-01/.test(body);
    var hasRidge = /ridge-cursor-wake-loop-20260822-01/.test(body);
    if (hasMeasure && hasClassify && hasUpsert && hasPredicate && hasJob && hasRidge) {
      return {
        state: "INTEGRATED",
        note: "HEAD-proof leftover is on this file. One canonical job JSON via JobStore.upsert. A Slack taking is still not the file."
      };
    }
    return { state: "NOT_LANDED", note: "host/watchdog_head_proof.py missing the leftover. SPECTER HEAD-proof taking is CLAIMED." };
  };

  api.isMcpWakeJobTalk = function (text) {
    return /specter pivot|mcp\/wake real-job|real-job verification|no render duplication|adjacent.{0,40}mcp\/wake/i.test(String(text || ""));
  };

  api.mcpWakeJobState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/mcp_wake_job.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_root/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasPredicate = /result_address_on_head/.test(body);
    var hasTemp = /TemporaryDirectory/.test(body) && /never write wake_jobs/i.test(body);
    var hasRefuse = /NOT_DURABLE/.test(body);
    var hasCheap = /invoke_model/.test(body);
    if (hasMeasure && hasClassify && hasPredicate && hasTemp && hasRefuse && hasCheap) {
      return {
        state: "INTEGRATED",
        note: "MCP/wake real-job leftover is on this file. Missing page is NOT_DURABLE. Present page is DONE. Cheap tick stays invoke_model false. A Slack pivot is still not the file."
      };
    }
    return { state: "NOT_LANDED", note: "MCP/wake real-job instrument is missing the durable-page leftover. SPECTER pivot talk is CLAIMED." };
  };

  api.isRenderContractTalk = function (text) {
    return /workflow-contract|found no live [`']?render_check|specter taking|render-qa execution|prove the actual workflow contract/i.test(String(text || ""));
  };

  api.isMcpWakeTalk = function (text) {
    return /specter collision check|holding implementation|jojo-visual-ci|canonical mcp inventory|idle-resume measurement|please post your named exact scope/i.test(String(text || ""));
  };

  api.mcpWakeState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/mcp_wake.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasJob = /def verify_job/.test(body);
    var hasIdle = /idle_resume/.test(body) && /UNMEASURED/.test(body);
    var noWrite = /Never writes wake_jobs/.test(body) || /wrote_wake_jobs/.test(body);
    if (hasMeasure && hasClassify && hasJob && hasIdle && noWrite) {
      return {
        state: "INTEGRATED",
        note: "MCP/wake leftover is on this file. Canonical inventory named. Cheap tick invoke_model=false. Idle-resume stays UNMEASURED. A Slack collision hold is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/mcp_wake.py missing the inventory / cheap-tick / idle-resume census. Collision-hold talk is CLAIMED until the leftover ships."
    };
  };

  api.renderContractState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "UNMEASURED", note: "render-check contract / run catalog not read. Absence was not measured." };
    }
    if (!row.has_exact_command) {
      return { state: "NOT_LANDED", note: "workflow contract is missing the exact free-runner command. SPECTER / workflow-contract talk is CLAIMED." };
    }
    var conclusion = String(row.last_conclusion || "").toLowerCase();
    var runId = row.last_run_id || "32812516738";
    var threaded = row.has_threading === true && row.swallows_broken_pipe === true;
    if (conclusion === "failure" && !threaded) {
      return {
        state: "NOT_LANDED",
        note: "last main render-check run " + runId + " failed. A workflow file is not a passing run. SPECTER taking is CLAIMED."
      };
    }
    if (conclusion === "failure" && threaded) {
      return {
        state: "CANDIDATE",
        note: "last main render-check run " + runId + " failed. ThreadingMixIn leftover shipped. A workflow file is not a passing run."
      };
    }
    if (conclusion === "success") {
      return {
        state: "INTEGRATED",
        note: "workflow contract names the exact command and last main run " + runId + " succeeded. A Slack taking is still not the file."
      };
    }
    if (!threaded) {
      return { state: "NOT_LANDED", note: "render_check.py still uses a single-thread HTTP server. SPECTER / workflow-contract talk is CLAIMED." };
    }
    return { state: "CANDIDATE", note: "workflow contract and threading leftover are on this tree. A workflow file is not a run URL." };
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

  api.isDevicePathCensusTalk = function (text) {
    return /calibrated device path census|reservation blobs|lawful canary|jojo-device-reservation-result-census|1787641558\.357319|no host inference|tree\/blob enumeration/i.test(String(text || ""));
  };

  api.devicePathCensusState = function (text) {
    var body = String(text || "");
    if (!body.trim()) {
      return { state: "UNMEASURED", note: "host/device_path_census.py body not read. Absence was not measured." };
    }
    var hasMeasure = /def measure_from_rows/.test(body);
    var hasClassify = /def classify/.test(body);
    var hasMiss = /FINDER-FAILED/.test(body) && /Never 0/.test(body);
    var hasCanary = /lawful canary/.test(body) && /not pending/.test(body);
    var noInfer = /no host inference/.test(body);
    var noTitan = /titan/.test(body) && /NOT_WRITTEN/.test(body);
    if (hasMeasure && hasClassify && hasMiss && hasCanary && noInfer && noTitan) {
      return {
        state: "INTEGRATED",
        note: "device-path census leftover is on this file. X/Y/Z ran. Lawful OPEN+DEVICE canary is a fixture, not a pending p/ ACTION. A Slack census is still not the file."
      };
    }
    return {
      state: "NOT_LANDED",
      note: "host/device_path_census.py missing the leftover. Calibrated device-path census / lawful-canary talk is CLAIMED until the leftover ships."
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

  api.titanReceiptJson = function (receiptText) {
    var body = String(receiptText || "");
    var marker = "FULL --go RECEIPT (untruncated):";
    var markerAt = body.indexOf(marker);
    if (markerAt < 0 || body.indexOf(marker, markerAt + marker.length) >= 0) return null;
    var fenceAt = body.indexOf("```json", markerAt + marker.length);
    if (fenceAt < 0) return null;
    var openAt = body.indexOf("{", fenceAt + 7);
    if (openAt < 0) return null;
    var depth = 0;
    var inString = false;
    var escaped = false;
    var closeAt = -1;
    var i;
    for (i = openAt; i < body.length; i += 1) {
      var ch = body.charAt(i);
      if (inString) {
        if (escaped) {
          escaped = false;
        } else if (ch === "\\") {
          escaped = true;
        } else if (ch === '"') {
          inString = false;
        }
      } else if (ch === '"') {
        inString = true;
      } else if (ch === "{") {
        depth += 1;
      } else if (ch === "}") {
        depth -= 1;
        if (depth === 0) {
          closeAt = i + 1;
          break;
        }
      }
    }
    if (closeAt < 0 || inString || depth !== 0) return null;
    try {
      return JSON.parse(body.slice(openAt, closeAt));
    } catch (error) {
      return null;
    }
  };

  function titanReceiptMatches(data, publicJournal, publicJournalPresent, evidence) {
    var organs = Array.isArray(data.organs) ? data.organs : [];
    var plan = evidence && evidence.plan;
    var planOrgans = plan && Array.isArray(plan.organs) ? plan.organs : [];
    var receiptJournals = evidence && Array.isArray(evidence.journals) ? evidence.journals : [];
    var count = Number(data.count || 0);
    var base = Number(data.claimed_append_base);
    var end = Number(data.claimed_append_end);
    var publicRows = publicJournalPresent && Array.isArray(publicJournal.organs) ? publicJournal.organs : [];
    var publicOk = !publicJournalPresent || (
      publicJournal.reread === true && Number(publicJournal.count) === 31 &&
      Number(publicJournal.bytes) === end - base && publicRows.length === 31
    );
    if (!evidence || evidence.go !== true || evidence.journal !== false ||
        evidence.measured !== true || evidence.reread !== true || evidence.wrote !== true ||
        evidence.titan_present !== true || String(evidence.state || "").toUpperCase() !== "INTEGRATED" ||
        Number(evidence.live_size) !== base || !plan || String(plan.kind || "") !== "TITAN_MOVE_PLAN" ||
        Number(plan.count) !== 31 || Number(plan.claimed_append_base) !== base ||
        Number(plan.claimed_append_end) !== end || plan.reallocated !== false ||
        count !== 31 || organs.length !== 31 || planOrgans.length !== 31 ||
        receiptJournals.length !== 31 || !publicOk) {
      return { receipt: false, public_journal: publicOk };
    }
    var emptySha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    var journalOffset = 0;
    var names = Object.create(null);
    for (var i = 0; i < 31; i += 1) {
      var packetRow = organs[i] || {};
      var planRow = planOrgans[i] || {};
      var receiptRow = receiptJournals[i] || {};
      var publicRow = publicRows[i] || {};
      var name = String(packetRow.name || "");
      var container = String(packetRow.container || "");
      var path = String(packetRow.path || "");
      var sourceSha = String(packetRow.sha256 || "").toLowerCase();
      var writtenSha = String(packetRow.written_sha256 || sourceSha).toLowerCase();
      var offset = Number(packetRow.offset);
      var length = Number(packetRow.len);
      if (!name || names[name] || container !== name + ".mno" ||
          path !== "excerpts/20260823/" + container ||
          String(planRow.name || "") !== name || String(planRow.container || "") !== container ||
          String(planRow.path || "") !== path || Number(planRow.offset) !== offset ||
          Number(planRow.len) !== length || String(planRow.sha256 || "").toLowerCase() !== sourceSha ||
          String(planRow.titan || "").toUpperCase() !== "WRITTEN" ||
          String(receiptRow.name || "") !== name || Number(receiptRow.offset) !== offset ||
          Number(receiptRow.len) !== length || String(receiptRow.new_sha256 || "").toLowerCase() !== writtenSha ||
          String(receiptRow.pre_sha256 || "").toLowerCase() !== emptySha ||
          receiptRow.reread !== true || receiptRow.past_eof !== true) {
        return { receipt: false, public_journal: publicOk };
      }
      if (publicJournalPresent && (
          String(publicRow.name || "") !== name || String(publicRow.container || "") !== container ||
          Number(publicRow.journal_offset) !== journalOffset ||
          Number(publicRow.claimed_titan_offset) !== offset || Number(publicRow.len) !== length ||
          String(publicRow.mask_sha256 || "").toLowerCase() !== sourceSha ||
          String(publicRow.new_sha256 || "").toLowerCase() !== writtenSha ||
          String(publicRow.pre_sha256 || "").toLowerCase() !== emptySha || publicRow.reread !== true)) {
        return { receipt: false, public_journal: false };
      }
      names[name] = true;
      journalOffset += length;
    }
    return {
      receipt: Object.keys(names).length === 31 && journalOffset === end - base,
      public_journal: publicOk
    };
  }

  api.titanMoveRow = function (data, journal, receiptText) {
    data = data || {};
    var publicJournalPresent = Boolean(journal && typeof journal === "object" && Object.keys(journal).length);
    journal = journal || {};
    var organs = Array.isArray(data.organs) ? data.organs : [];
    var count = Number(data.count || organs.length || 0);
    var base = Number(data.claimed_append_base);
    var end = Number(data.claimed_append_end);
    var expectedOffset = base;
    var nonzero = 0;
    var geometryComplete = count > 0 && organs.length === count &&
      Number.isFinite(base) && Number.isInteger(base) && base > 0 &&
      Number.isFinite(end) && Number.isInteger(end) && end > base;
    var names = Object.create(null);
    var containers = Object.create(null);
    var paths = Object.create(null);
    var membershipComplete = count === 31 && organs.length === 31;
    var writtenStateCount = 0;
    var planStateCount = 0;
    var i;
    for (i = 0; i < organs.length; i += 1) {
      var organ = organs[i] || {};
      var name = String(organ.name || "");
      var container = String(organ.container || "");
      var path = String(organ.path || "");
      var offset = Number(organ.offset);
      var length = Number(organ.len);
      var sourceDigest = String(organ.sha256 || "").toLowerCase();
      var writtenDigest = String(organ.written_sha256 || sourceDigest).toLowerCase();
      var organState = String(organ.titan || "").toUpperCase();
      var offsetOk = Number.isFinite(offset) && Number.isInteger(offset) && offset > 0;
      var lengthOk = Number.isFinite(length) && Number.isInteger(length) && length > 0;
      var membershipOk = Boolean(name) && !names[name] && !containers[container] && !paths[path] &&
        container === name + ".mno" && path === "excerpts/20260823/" + container;
      if (offsetOk) nonzero += 1;
      if (!membershipOk) membershipComplete = false;
      if (!membershipOk || !offsetOk || !lengthOk || offset !== expectedOffset ||
          !/^[0-9a-f]{64}$/.test(sourceDigest) || !/^[0-9a-f]{64}$/.test(writtenDigest)) {
        geometryComplete = false;
      }
      if (organState === "WRITTEN") writtenStateCount += 1;
      if (organState === "NOT_WRITTEN") planStateCount += 1;
      if (name) names[name] = true;
      if (container) containers[container] = true;
      if (path) paths[path] = true;
      if (lengthOk) expectedOffset += length;
    }
    var canonicalMembership = membershipComplete &&
      Object.keys(names).length === 31 && Object.keys(containers).length === 31 &&
      Object.keys(paths).length === 31;
    geometryComplete = geometryComplete && expectedOffset === end && canonicalMembership;
    var receipt = String(data.write_receipt || "");
    var commit = String(data.integrated_commit || "").toLowerCase();
    var closedReceipt = "p/claudelocal-titan-move-go-20260825-01.md";
    var closedCommit = "b3fe1449560a359c87963d113c022ae3b8f86f73";
    var receiptBody = String(receiptText || "");
    var receiptMarkers = [
      "id: claudelocal-titan-move-go-20260825-01",
      "state INTEGRATED, wrote=true, reread=true",
      "31/31 organs journaled, 31/31 reread true, 31/31 past_eof",
      "titan.gguf after: 103812669582 bytes (+9319291"
    ];
    var receiptMarkersOk = receipt === closedReceipt && receiptMarkers.every(function (marker) {
      return receiptBody.indexOf(marker) >= 0;
    });
    var receiptJson = api.titanReceiptJson(receiptBody);
    var evidenceMatch = titanReceiptMatches(data, journal, publicJournalPresent, receiptJson);
    var receiptContentOk = receiptMarkersOk && evidenceMatch.receipt;
    var writeCount = Number(data.write_count || 0);
    var titanSizeBefore = Number(data.titan_size_before || 0);
    var titanSizeAfter = Number(data.titan_size_after || 0);
    var liveSizeBefore = Number(data.live_size_before || 0);
    var liveSizeAfter = Number(data.live_size_after || 0);
    var incident = data.duplicate_append_incident || {};
    var incidentState = String(incident.state || "").toUpperCase();
    var incidentActive = incidentState === "PAUSED_DUPLICATE_APPENDS";
    var incidentSpanBytes = Number(incident.span_bytes || 0);
    var incidentSpanCount = Number(incident.span_count || 0);
    var duplicateSpanCount = Number(incident.duplicate_span_count || 0);
    var observedTitanSize = Number(incident.artifact_size || 0);
    var expectedRanges = [
      [base, end],
      [end, end + (end - base)],
      [end + (end - base), end + 2 * (end - base)]
    ];
    var incidentRanges = Array.isArray(incident.span_ranges) ? incident.span_ranges : [];
    var incidentEvidenceOk = incidentActive &&
      incident.source === "Slack 1787638151.184599" &&
      incident.measured_by === "DEMON / OpenAI Codex GPT-5.6 Sol" &&
      incident.artifact_mtime === "2026-08-25T04:48:50.092Z" &&
      observedTitanSize === 103831308164 &&
      incidentSpanBytes === end - base && incidentSpanBytes === 9319291 &&
      incidentSpanCount === 3 && duplicateSpanCount === 2 &&
      JSON.stringify(incidentRanges) === JSON.stringify(expectedRanges) &&
      expectedRanges[2][1] === observedTitanSize &&
      String(incident.span_sha256 || "").toLowerCase() ===
        "3754028086cd42e00131bea88f0e7fcf6dba2f84ad31cb70b88e655bbdd84e8c" &&
      incident.canonical_span === "UNRESOLVED" && incident.mutation === "PAUSED" &&
      incident.repair_apply === false;
    return {
      measured: true,
      count: count,
      excerpt_count: organs.length,
      titan: data.titan || "NOT_WRITTEN",
      packet_state: data.state || "",
      nonzero_offsets: nonzero,
      claimed_append_base: base,
      claimed_append_end: end,
      canonical_membership: canonicalMembership,
      structure_complete: geometryComplete && writtenStateCount === count,
      plan_structure_complete: geometryComplete && planStateCount === count,
      wrote: data.wrote === true,
      reread: data.reread === true,
      write_count: writeCount,
      reread_count: Number(data.reread_count || 0),
      past_eof_count: Number(data.past_eof_count || 0),
      titan_size_before: titanSizeBefore,
      titan_size_after: titanSizeAfter,
      live_size_before: liveSizeBefore,
      live_size_after: liveSizeAfter,
      legacy_aliases_ok: writeCount === count &&
        liveSizeBefore === titanSizeBefore && liveSizeAfter === titanSizeAfter,
      written_bytes: Number(data.written_bytes || 0),
      write_receipt: receipt,
      write_receipt_ref_ok: receipt === closedReceipt,
      write_receipt_content_ok: receiptContentOk,
      write_receipt_evidence_ok: evidenceMatch.receipt,
      public_journal_evidence_ok: evidenceMatch.public_journal,
      integrated_commit: commit,
      integrated_commit_ok: commit === closedCommit,
      incident_active: incidentActive,
      incident_evidence_ok: incidentEvidenceOk,
      incident_state: incidentState,
      incident_source: incident.source || "",
      observed_titan_size: observedTitanSize,
      incident_span_bytes: incidentSpanBytes,
      incident_span_count: incidentSpanCount,
      duplicate_span_count: duplicateSpanCount,
      incident_span_sha256: String(incident.span_sha256 || "").toLowerCase(),
      incident_search_space: incidentRanges,
      independent_measurement_ok: incidentEvidenceOk,
      journal_reread: journal.reread === true || data.public_journal_reread === true,
      journal_count: Number(journal.count || data.public_journal_count || 0)
    };
  };
  api.packetRowFromJson = api.titanMoveRow;

  api.titanMoveState = function (row) {
    row = row || {};
    if (!row.measured) {
      return { state: "UNMEASURED", note: "titan move packet not measured. Absence was not stillness." };
    }
    if (row.incident_active === true) {
      if (row.incident_evidence_ok === true) {
        return {
          state: "NOT_LANDED",
          note: "PAUSED duplicate-append incident: " + row.incident_span_count +
            " byte-identical " + row.incident_span_bytes + "-byte spans measured through live size " +
            row.observed_titan_size + "; " + row.duplicate_span_count +
            " duplicate copies remain. Historical Claude receipt is quarantined as certification. " +
            "Do not append, truncate, dedupe, repair, or select a canonical copy."
        };
      }
      return {
        state: "NOT_LANDED",
        note: "duplicate-append incident marker is inconsistent. FINDER-FAILED with the reported search space; mutation remains PAUSED."
      };
    }
    var count = Number(row.count || 0);
    var excerpts = Number(row.excerpt_count || 0);
    var written = String(row.titan || "").toUpperCase();
    var nonzero = Number(row.nonzero_offsets || 0);
    var wrote = row.wrote === true;
    var reread = row.reread === true;
    var rereadCount = Number(row.reread_count || 0);
    var pastEofCount = Number(row.past_eof_count || 0);
    var packetState = String(row.packet_state || "").toUpperCase();
    var before = Number(row.titan_size_before || 0);
    var after = Number(row.titan_size_after || 0);
    var writtenBytes = Number(row.written_bytes || 0);
    var receipt = String(row.write_receipt || "");
    var base = Number(row.claimed_append_base || 0);
    var end = Number(row.claimed_append_end || 0);
    var journalReread = row.journal_reread === true;
    var journalCount = Number(row.journal_count || 0);
    var executionComplete = written === "WRITTEN" && packetState === "INTEGRATED" && wrote && reread &&
      count === 31 && excerpts === count && nonzero === count && rereadCount === count &&
      pastEofCount === count && row.canonical_membership === true && row.structure_complete === true &&
      row.write_receipt_ref_ok === true && row.write_receipt_content_ok === true &&
      row.write_receipt_evidence_ok === true && row.public_journal_evidence_ok === true &&
      row.integrated_commit_ok === true && row.legacy_aliases_ok === true &&
      row.independent_measurement_ok === true &&
      Number(row.write_count || 0) === count && before === base && after === end &&
      writtenBytes === end - base && writtenBytes > 0 && receipt !== "";
    if (executionComplete) {
      return {
        state: "INTEGRATED",
        note: "Titan write and reread measured for " + count + " organs; " + writtenBytes +
          " bytes appended; receipt " + receipt + "."
      };
    }
    if (excerpts < 31) {
      return {
        state: "NOT_LANDED",
        note: "only " + excerpts + "/31 excerpts on this tree. Pull/reconcile the landed owner receipt; this MOVE is closed, so do not append."
      };
    }
    if (written === "NOT_WRITTEN" && journalReread && journalCount >= 31 && nonzero === count && count >= 31 && row.plan_structure_complete === true) {
      return {
        state: "CANDIDATE",
        note: journalCount + "/31 historical excerpt binaries are journaled, but this packet regressed to NOT_WRITTEN. Reconcile the landed WRITTEN packet; do not append or reopen owner action."
      };
    }
    if (written === "NOT_WRITTEN" && nonzero === count && count >= 31 && row.plan_structure_complete === true) {
      return {
        state: "CLAIMED",
        note: excerpts + "/31 historical claimed append offsets are structurally complete, but the MOVE is already closed. Reconcile the landed WRITTEN packet; do not append."
      };
    }
    if (written === "NOT_WRITTEN" || nonzero === 0) {
      return {
        state: "NOT_LANDED",
        note: excerpts + "/31 excerpts on this tree, but NOT_WRITTEN plan evidence is missing or inconsistent. Repair public evidence from the landed receipt; do not allocate or append a closed MOVE."
      };
    }
    if (written === "WRITTEN") {
      return {
        state: "NOT_LANDED",
        note: "packet says WRITTEN but complete write/reread evidence is missing or inconsistent. Refuse marker-only integration."
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
    if (state === "PR_OPEN" || state === "CLAIMED" || state === "CANDIDATE" || state === "PAGE_PENDING" || state === "PUSHED_BRANCH" || state === "ACTIVE" || state === "WAIT" || state === "UNMEASURED" || state === "CARRIER_ONLY") return "wait";
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
  var devicePathCensusOut = document.getElementById("device-path-census-result");
  var deviceChurnOut = document.getElementById("device-churn-result");
  var strandedOut = document.getElementById("stranded-map-result");
  var hostZeroOut = document.getElementById("host-zero-result");
  var connectorOut = document.getElementById("connector-reval-result");
  var renderContractOut = document.getElementById("render-contract-result");
  var workingOut = document.getElementById("working-builds-result");
  var slackReceiptOut = document.getElementById("slack-receipt-result");
  var ledgerOut = document.getElementById("resource-ledger-result");
  var watchdogHeadProofOut = document.getElementById("watchdog-head-proof-result");
  var mcpWakeJobOut = document.getElementById("mcp-wake-job-result");
  var mcpWakeOut = document.getElementById("mcp-wake-result");
  var finderZeroOut = document.getElementById("finder-zero-result");
  var staleManifestOut = document.getElementById("stale-manifest-result");
  var claudeTesterOut = document.getElementById("claude-tester-result");
  var claudeZeroOut = document.getElementById("claude-zero-result");
  var impactLedgerOut = document.getElementById("impact-ledger-result");
  var claudeZeroDamageOut = document.getElementById("claude-zero-damage-result");
  var xyzOut = document.getElementById("xyz-zero-result");
  var appendGuardOut = document.getElementById("titan-append-guard-result");
  var measureAbuseOut = document.getElementById("measure-abuse-result");
  var remasureOut = document.getElementById("remeasure-result");
  var claudeParkOut = document.getElementById("claude-park-result");
  var grokRecoveryOut = document.getElementById("grok-recovery-result");
  var contextIntegrityOut = document.getElementById("context-integrity-result");
  var claudeRoleOut = document.getElementById("claude-role-result");
  var claudeComputeOut = document.getElementById("claude-compute-result");
  var claudeIntermediateOut = document.getElementById("claude-intermediate-result");
  var cashNowOut = document.getElementById("cash-now-result");
  var jojoAssignOut = document.getElementById("jojo-assign-result");
  var titanTestQuarantineOut = document.getElementById("titan-test-quarantine-result");
  var sittingRemintOut = document.getElementById("sitting-remint-result");
  var foreignMainOut = document.getElementById("foreign-main-result");
  var deviceCanaryOut = document.getElementById("device-canary-result");
  var memoryShipOut = document.getElementById("memory-ship-result");
  var grokHygieneOut = document.getElementById("grok-hygiene-result");
  var containmentOut = document.getElementById("containment-result");
  var watchdogCanaryOut = document.getElementById("watchdog-canary-result");
  var branchReviewOut = document.getElementById("branch-review-result");
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

  function paintDevicePathCensus(result) {
    if (!devicePathCensusOut) return;
    devicePathCensusOut.setAttribute("data-tone", api.toneFor(result.state));
    devicePathCensusOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
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

  function paintHostZero(result) {
    if (!hostZeroOut) return;
    hostZeroOut.setAttribute("data-tone", api.toneFor(result.state));
    hostZeroOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintConnectorReval(result) {
    if (!connectorOut) return;
    connectorOut.setAttribute("data-tone", api.toneFor(result.state));
    connectorOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintRenderContract(result) {
    if (!renderContractOut) return;
    renderContractOut.setAttribute("data-tone", api.toneFor(result.state));
    renderContractOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintWorkingBuilds(result) {
    if (!workingOut) return;
    workingOut.setAttribute("data-tone", api.toneFor(result.state));
    workingOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintSlackReceipt(result) {
    if (!slackReceiptOut) return;
    slackReceiptOut.setAttribute("data-tone", api.toneFor(result.state));
    slackReceiptOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintResourceLedger(result) {
    if (!ledgerOut) return;
    ledgerOut.setAttribute("data-tone", api.toneFor(result.state));
    ledgerOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintWatchdogHeadProof(result) {
    if (!watchdogHeadProofOut) return;
    watchdogHeadProofOut.setAttribute("data-tone", api.toneFor(result.state));
    watchdogHeadProofOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintMcpWakeJob(result) {
    if (!mcpWakeJobOut) return;
    mcpWakeJobOut.setAttribute("data-tone", api.toneFor(result.state));
    mcpWakeJobOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintMcpWake(result) {
    if (!mcpWakeOut) return;
    mcpWakeOut.setAttribute("data-tone", api.toneFor(result.state));
    mcpWakeOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintFinderZero(result) {
    if (!finderZeroOut) return;
    finderZeroOut.setAttribute("data-tone", api.toneFor(result.state));
    finderZeroOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintStaleManifest(result) {
    if (!staleManifestOut) return;
    staleManifestOut.setAttribute("data-tone", api.toneFor(result.state));
    staleManifestOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintClaudeTester(result) {
    if (!claudeTesterOut) return;
    claudeTesterOut.setAttribute("data-tone", api.toneFor(result.state));
    claudeTesterOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintImpactLedger(result) {
    if (!impactLedgerOut) return;
    impactLedgerOut.setAttribute("data-tone", api.toneFor(result.state));
    impactLedgerOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintClaudeZeroDamage(result) {
    if (!claudeZeroDamageOut) return;
    claudeZeroDamageOut.setAttribute("data-tone", api.toneFor(result.state));
    claudeZeroDamageOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintXyzZero(result) {
    if (!xyzOut) return;
    xyzOut.setAttribute("data-tone", api.toneFor(result.state));
    xyzOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintTitanAppendGuard(result) {
    if (!appendGuardOut) return;
    appendGuardOut.setAttribute("data-tone", api.toneFor(result.state));
    appendGuardOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintMeasureAbuse(result) {
    if (!measureAbuseOut) return;
    measureAbuseOut.setAttribute("data-tone", api.toneFor(result.state));
    measureAbuseOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintRemeasure(result) {
    if (!remeasureOut) return;
    remasureOut.setAttribute("data-tone", api.toneFor(result.state));
    remasureOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintClaudePark(result) {
    if (!claudeParkOut) return;
    claudeParkOut.setAttribute("data-tone", api.toneFor(result.state));
    claudeParkOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintClaudeZero(result) {
    if (!claudeZeroOut) return;
    claudeZeroOut.setAttribute("data-tone", api.toneFor(result.state));
    claudeZeroOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintGrokRecovery(result) {
    if (!grokRecoveryOut) return;
    grokRecoveryOut.setAttribute("data-tone", api.toneFor(result.state));
    grokRecoveryOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintContextIntegrity(result) {
    if (!contextIntegrityOut) return;
    contextIntegrityOut.setAttribute("data-tone", api.toneFor(result.state));
    contextIntegrityOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintClaudeIntermediate(result) {
    if (!claudeIntermediateOut) return;
    claudeIntermediateOut.setAttribute("data-tone", api.toneFor(result.state));
    claudeIntermediateOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintJojoAssign(result) {
    if (!jojoAssignOut) return;
    jojoAssignOut.setAttribute("data-tone", api.toneFor(result.state));
    jojoAssignOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintClaudeRole(result) {
    if (!claudeRoleOut) return;
    claudeRoleOut.setAttribute("data-tone", api.toneFor(result.state));
    claudeRoleOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintClaudeCompute(result) {
    if (!claudeComputeOut) return;
    claudeComputeOut.setAttribute("data-tone", api.toneFor(result.state));
    claudeComputeOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintCashNow(result) {
    if (!cashNowOut) return;
    cashNowOut.setAttribute("data-tone", api.toneFor(result.state));
    cashNowOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintTitanTestQuarantine(result) {
    if (!titanTestQuarantineOut) return;
    titanTestQuarantineOut.setAttribute("data-tone", api.toneFor(result.state));
    titanTestQuarantineOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintSittingRemint(result) {
    if (!sittingRemintOut) return;
    sittingRemintOut.setAttribute("data-tone", api.toneFor(result.state));
    sittingRemintOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintForeignMain(result) {
    if (!foreignMainOut) return;
    foreignMainOut.setAttribute("data-tone", api.toneFor(result.state));
    foreignMainOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintDeviceCanary(result) {
    if (!deviceCanaryOut) return;
    deviceCanaryOut.setAttribute("data-tone", api.toneFor(result.state));
    deviceCanaryOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintMemoryShip(result) {
    if (!memoryShipOut) return;
    memoryShipOut.setAttribute("data-tone", api.toneFor(result.state));
    memoryShipOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintGrokHygiene(result) {
    if (!grokHygieneOut) return;
    grokHygieneOut.setAttribute("data-tone", api.toneFor(result.state));
    grokHygieneOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintContainment(result) {
    if (!containmentOut) return;
    containmentOut.setAttribute("data-tone", api.toneFor(result.state));
    containmentOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintWatchdogCanary(result) {
    if (!watchdogCanaryOut) return;
    watchdogCanaryOut.setAttribute("data-tone", api.toneFor(result.state));
    watchdogCanaryOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
  }

  function paintBranchReview(result) {
    if (!branchReviewOut) return;
    branchReviewOut.setAttribute("data-tone", api.toneFor(result.state));
    branchReviewOut.innerHTML = "<b>" + esc(result.state) + "</b><p>" + esc(result.note) + "</p>";
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

  function loadDevicePathCensus(sha) {
    if (!devicePathCensusOut) return Promise.resolve(null);
    devicePathCensusOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/device_path_census.py at the official SHA…</p>";
    var url = RAW + sha + "/host/device_path_census.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/device_path_census.py absent at the measured main SHA. Calibrated device-path census / lawful-canary talk is CLAIMED." };
        paintDevicePathCensus(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintDevicePathCensus(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.devicePathCensusState(body);
        paintDevicePathCensus(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintDevicePathCensus(err);
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

  function loadStaleManifest(sha) {
    if (!staleManifestOut) return Promise.resolve(null);
    staleManifestOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/stale_manifest.py at the official SHA…</p>";
    var url = RAW + sha + "/host/stale_manifest.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/stale_manifest.py absent at the measured main SHA. KEYB stale-manifest talk is CLAIMED." };
        paintStaleManifest(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintStaleManifest(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.staleManifestState(body);
        paintStaleManifest(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintStaleManifest(err);
      return err;
    });
  }

  function loadWatchdogCanary(sha) {
    if (!watchdogCanaryOut) return Promise.resolve(null);
    watchdogCanaryOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/watchdog_canary.py at the official SHA…</p>";
    var url = RAW + sha + "/host/watchdog_canary.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/watchdog_canary.py absent at the measured main SHA. SPECTER ship-receipt / unutilized-oracle talk is CLAIMED." };
        paintWatchdogCanary(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintWatchdogCanary(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.watchdogCanaryState(body);
        paintWatchdogCanary(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintWatchdogCanary(err);
      return err;
    });
  }

  function loadContextIntegrity(sha) {
    if (!contextIntegrityOut) return Promise.resolve(null);
    contextIntegrityOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/context_integrity.py at the official SHA…</p>";
    var url = RAW + sha + "/host/context_integrity.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/context_integrity.py absent at the measured main SHA. Context-integrity / unflattering-truths talk is CLAIMED." };
        paintContextIntegrity(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintContextIntegrity(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.contextIntegrityState(body);
        paintContextIntegrity(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintContextIntegrity(err);
      return err;
    });
  }

  function loadTitanAppendGuard(sha) {
    if (!appendGuardOut) return Promise.resolve(null);
    appendGuardOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/titan_append_guard.py at the official SHA…</p>";
    var url = RAW + sha + "/host/titan_append_guard.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/titan_append_guard.py absent at the measured main SHA. Triple-append / pause-further-append talk is CLAIMED." };
        paintTitanAppendGuard(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintTitanAppendGuard(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.titanAppendGuardState(body);
        paintTitanAppendGuard(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintTitanAppendGuard(err);
      return err;
    });
  }

  function loadWorkingBuilds(sha) {
    if (!workingOut) return Promise.resolve(null);
    workingOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/working_builds.py at the official SHA…</p>";
    var url = RAW + sha + "/host/working_builds.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/working_builds.py absent at the measured main SHA. Machine-only working-builds talk is CLAIMED." };
        paintWorkingBuilds(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintWorkingBuilds(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.workingBuildState(body);
        paintWorkingBuilds(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintWorkingBuilds(err);
      return err;
    });
  }

  function loadClaudeZeroDamage(sha) {
    if (!claudeZeroDamageOut) return Promise.resolve(null);
    claudeZeroDamageOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/claude_zero_damage.py at the official SHA…</p>";
    var url = RAW + sha + "/host/claude_zero_damage.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/claude_zero_damage.py absent at the measured main SHA. Damage-control talk is CLAIMED." };
        paintClaudeZeroDamage(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintClaudeZeroDamage(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.claudeZeroDamageState(body);
        paintClaudeZeroDamage(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintClaudeZeroDamage(err);
      return err;
    });
  }

  function loadImpactLedger(sha) {
    if (!impactLedgerOut) return Promise.resolve(null);
    impactLedgerOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/impact_ledger.py at the official SHA…</p>";
    var url = RAW + sha + "/host/impact_ledger.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/impact_ledger.py absent at the measured main SHA. P0 containment / TRACE CONSUMERS talk is CLAIMED." };
        paintImpactLedger(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintImpactLedger(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.impactLedgerState(body);
        paintImpactLedger(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintImpactLedger(err);
      return err;
    });
  }

  function loadFinderZero(sha) {
    if (!finderZeroOut) return Promise.resolve(null);
    finderZeroOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/finder_zero.py at the official SHA…</p>";
    var url = RAW + sha + "/host/finder_zero.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/finder_zero.py absent at the measured main SHA. Finder-zero talk is CLAIMED." };
        paintFinderZero(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintFinderZero(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.finderZeroState(body);
        paintFinderZero(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintFinderZero(err);
      return err;
    });
  }

  function loadClaudePark(sha) {
    if (!claudeParkOut) return Promise.resolve(null);
    claudeParkOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/claude_park.py at the official SHA…</p>";
    var url = RAW + sha + "/host/claude_park.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/claude_park.py absent at the measured main SHA. Full Claude-family suspension talk is CLAIMED." };
        paintClaudePark(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintClaudePark(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.claudeParkState(body);
        paintClaudePark(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintClaudePark(err);
      return err;
    });
  }

  function loadRemeasure(sha) {
    if (!remeasureOut) return Promise.resolve(null);
    remasureOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/remeasure.py at the official SHA…</p>";
    var url = RAW + sha + "/host/remeasure.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/remeasure.py absent at the measured main SHA. CONTAINMENT_COMPLIANCE talk is CLAIMED." };
        paintRemeasure(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintRemeasure(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.remeasureState(body);
        paintRemeasure(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintRemeasure(err);
      return err;
    });
  }

  function loadMeasureAbuse(sha) {
    if (!measureAbuseOut) return Promise.resolve(null);
    measureAbuseOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/measure_abuse.py at the official SHA…</p>";
    var url = RAW + sha + "/host/measure_abuse.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/measure_abuse.py absent at the measured main SHA. Measurement-abuse talk is CLAIMED." };
        paintMeasureAbuse(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintMeasureAbuse(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.measureAbuseState(body);
        paintMeasureAbuse(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintMeasureAbuse(err);
      return err;
    });
  }

  function loadClaudeZero(sha) {
    if (!claudeZeroOut) return Promise.resolve(null);
    claudeZeroOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/claude_zero.py at the official SHA…</p>";
    var url = RAW + sha + "/host/claude_zero.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/claude_zero.py absent at the measured main SHA. Claude-reported-zero / RETRACT-DO-NOT-DOWNGRADE talk is CLAIMED." };
        paintClaudeZero(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintClaudeZero(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.claudeZeroState(body);
        paintClaudeZero(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintClaudeZero(err);
      return err;
    });
  }

  function loadForeignMain(sha) {
    if (!foreignMainOut) return Promise.resolve(null);
    foreignMainOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/foreign_main.py at the official SHA…</p>";
    var url = RAW + sha + "/host/foreign_main.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/foreign_main.py absent at the measured main SHA. LocalDeviceAgent / muhl_subagent_protocol / SHIP_RECEIPT talk is CLAIMED." };
        paintForeignMain(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintForeignMain(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.foreignMainState(body);
        paintForeignMain(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintForeignMain(err);
      return err;
    });
  }

  function loadTitanTestQuarantine(sha) {
    if (!titanTestQuarantineOut) return Promise.resolve(null);
    titanTestQuarantineOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/titan_test_quarantine.py at the official SHA…</p>";
    var url = RAW + sha + "/host/titan_test_quarantine.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/titan_test_quarantine.py absent at the measured main SHA. Live-Titan test quarantine talk is CLAIMED." };
        paintTitanTestQuarantine(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintTitanTestQuarantine(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.titanTestQuarantineState(body);
        paintTitanTestQuarantine(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintTitanTestQuarantine(err);
      return err;
    });
  }

  function loadDeviceCanary(sha) {
    if (!deviceCanaryOut) return Promise.resolve(null);
    deviceCanaryOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/device_canary.py at the official SHA…</p>";
    var url = RAW + sha + "/host/device_canary.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/device_canary.py absent at the measured main SHA. First bounded read-only device canary / TAKING_LANDED_INPUT talk is CLAIMED." };
        paintDeviceCanary(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintDeviceCanary(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.deviceCanaryState(body);
        paintDeviceCanary(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintDeviceCanary(err);
      return err;
    });
  }

  function loadGrokHygiene(sha) {
    if (!grokHygieneOut) return Promise.resolve(null);
    grokHygieneOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/grok_hygiene.py at the official SHA…</p>";
    var url = RAW + sha + "/host/grok_hygiene.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/grok_hygiene.py absent at the measured main SHA. Grok/Claude hygiene-boundary talk is CLAIMED." };
        paintGrokHygiene(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintGrokHygiene(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.grokHygieneState(body);
        paintGrokHygiene(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintGrokHygiene(err);
      return err;
    });
  }

  function loadMemoryShip(sha) {
    if (!memoryShipOut) return Promise.resolve(null);
    memoryShipOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/memory_ship.py at the official SHA…</p>";
    var url = RAW + sha + "/host/memory_ship.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/memory_ship.py absent at the measured main SHA. Use-the-memory-feature talk is CLAIMED." };
        paintMemoryShip(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintMemoryShip(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.memoryShipState(body);
        paintMemoryShip(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintMemoryShip(err);
      return err;
    });
  }

  function loadSittingRemint(sha) {
    if (!sittingRemintOut) return Promise.resolve(null);
    sittingRemintOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/sitting_remint.py at the official SHA…</p>";
    var url = RAW + sha + "/host/sitting_remint.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/sitting_remint.py absent at the measured main SHA. Sitting remint / already-landed leftover talk is CLAIMED." };
        paintSittingRemint(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintSittingRemint(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.sittingRemintState(body);
        paintSittingRemint(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintSittingRemint(err);
      return err;
    });
  }

  function loadClaudeCompute(sha) {
    if (!claudeComputeOut) return Promise.resolve(null);
    claudeComputeOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/claude_compute.py at the official SHA…</p>";
    var url = RAW + sha + "/host/claude_compute.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/claude_compute.py absent at the measured main SHA. Paid-compute / compiler-farm talk is CLAIMED." };
        paintClaudeCompute(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintClaudeCompute(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.claudeComputeState(body);
        paintClaudeCompute(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintClaudeCompute(err);
      return err;
    });
  }

  function loadJojoAssign(sha) {
    if (!jojoAssignOut) return Promise.resolve(null);
    jojoAssignOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/jojo_assign.py at the official SHA…</p>";
    var url = RAW + sha + "/host/jojo_assign.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/jojo_assign.py absent at the measured main SHA. JOJO RULE_ACK / assignment-before-packet talk is CLAIMED." };
        paintJojoAssign(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintJojoAssign(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.jojoAssignState(body);
        paintJojoAssign(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintJojoAssign(err);
      return err;
    });
  }

  function loadClaudeIntermediate(sha) {
    if (!claudeIntermediateOut) return Promise.resolve(null);
    claudeIntermediateOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/claude_intermediate.py at the official SHA…</p>";
    var url = RAW + sha + "/host/claude_intermediate.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/claude_intermediate.py absent at the measured main SHA. DEMON intermediate-lane ruling talk is CLAIMED." };
        paintClaudeIntermediate(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintClaudeIntermediate(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.claudeIntermediateState(body);
        paintClaudeIntermediate(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintClaudeIntermediate(err);
      return err;
    });
  }

  function loadCashNow(sha) {
    if (!cashNowOut) return Promise.resolve(null);
    cashNowOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/cash_now.py at the official SHA…</p>";
    var url = RAW + sha + "/host/cash_now.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/cash_now.py absent at the measured main SHA. Cash-now / collectable-USD talk is CLAIMED." };
        paintCashNow(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintCashNow(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.cashNowState(body);
        paintCashNow(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintCashNow(err);
      return err;
    });
  }

  function loadClaudeRole(sha) {
    if (!claudeRoleOut) return Promise.resolve(null);
    claudeRoleOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/claude_role.py at the official SHA…</p>";
    var url = RAW + sha + "/host/claude_role.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/claude_role.py absent at the measured main SHA. Colony-decides / Claude-family-role talk is CLAIMED." };
        paintClaudeRole(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintClaudeRole(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.claudeRoleState(body);
        paintClaudeRole(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintClaudeRole(err);
      return err;
    });
  }

  function loadBranchReview(sha) {
    if (!branchReviewOut) return Promise.resolve(null);
    branchReviewOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/branch_review.py at the official SHA…</p>";
    var url = RAW + sha + "/host/branch_review.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/branch_review.py absent at the measured main SHA. DEMON P0 IMPACT LEDGER / public-branch review talk is CLAIMED." };
        paintBranchReview(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintBranchReview(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.branchReviewState(body);
        paintBranchReview(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintBranchReview(err);
      return err;
    });
  }

  function loadContainment(sha) {
    if (!containmentOut) return Promise.resolve(null);
    containmentOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/containment.py at the official SHA…</p>";
    var url = RAW + sha + "/host/containment.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/containment.py absent at the measured main SHA. GAUGE stand-down talk is CLAIMED." };
        paintContainment(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintContainment(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.containmentState(body);
        paintContainment(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintContainment(err);
      return err;
    });
  }

  function loadXyzZero(sha) {
    if (!xyzOut) return Promise.resolve(null);
    xyzOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/xyz_zero.py at the official SHA…</p>";
    var url = RAW + sha + "/host/xyz_zero.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/xyz_zero.py absent at the measured main SHA. X-Y-Z zero-audit talk is CLAIMED." };
        paintXyzZero(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintXyzZero(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.xyzZeroState(body);
        paintXyzZero(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintXyzZero(err);
      return err;
    });
  }

  function loadRenderContract(sha) {
    if (!renderContractOut) return Promise.resolve(null);
    renderContractOut.innerHTML = "<b>UNMEASURED</b><p>Reading the render-check contract at the official SHA…</p>";
    var catalogUrl = RAW + sha + "/ground/RENDER_CONTRACT.json";
    var workflowUrl = RAW + sha + "/.github/workflows/render-check.yml";
    var toolUrl = RAW + sha + "/render_check.py";
    return Promise.all([
      fetch(catalogUrl, { cache: "no-store" }),
      fetch(workflowUrl, { cache: "no-store" }),
      fetch(toolUrl, { cache: "no-store" })
    ]).then(function (parts) {
      var catalogRes = parts[0];
      var workflowRes = parts[1];
      var toolRes = parts[2];
      if (catalogRes.status === 404 || workflowRes.status === 404 || toolRes.status === 404) {
        var missing = { state: "NOT_LANDED", note: "render-check contract files absent at the measured main SHA. SPECTER / workflow-contract talk is CLAIMED." };
        paintRenderContract(missing);
        return missing;
      }
      if (!catalogRes.ok || !workflowRes.ok || !toolRes.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed. Absence was not measured." };
        paintRenderContract(failed);
        return failed;
      }
      return Promise.all([catalogRes.json(), workflowRes.text(), toolRes.text()]).then(function (bodies) {
        var catalog = bodies[0] || {};
        var workflow = bodies[1] || "";
        var tool = bodies[2] || "";
        var runs = catalog.runs || [];
        var last = null;
        var i;
        for (i = 0; i < runs.length; i++) {
          if (runs[i].head_branch === "main" && runs[i].event === "push") {
            last = runs[i];
            break;
          }
        }
        if (!last) {
          for (i = 0; i < runs.length; i++) {
            if (runs[i].head_branch === "main") {
              last = runs[i];
              break;
            }
          }
        }
        var got = api.renderContractState({
          measured: true,
          has_exact_command: /python3 render_check\.py 8bit\.html 8walk\.html pixel\.html visual\.html[\s\\]+--receipt receipts\/render/.test(workflow),
          has_threading: /ThreadingMixIn/.test(tool),
          swallows_broken_pipe: /BrokenPipeError/.test(tool),
          last_conclusion: last ? last.conclusion : "",
          last_run_id: last ? last.id : ""
        });
        paintRenderContract(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintRenderContract(err);
      return err;
    });
  }

  function loadSlackReceipt(sha) {
    if (!slackReceiptOut) return Promise.resolve(null);
    slackReceiptOut.innerHTML = "<b>UNMEASURED</b><p>Reading the Slack-receipt catalog at the official SHA…</p>";
    var catalogUrl = RAW + sha + "/ground/SLACK_RECEIPT.json";
    return fetch(catalogUrl, { cache: "no-store" }).then(function (catalogRes) {
      if (catalogRes.status === 404) {
        var missing = { state: "NOT_LANDED", note: "ground/SLACK_RECEIPT.json absent at the measured main SHA. Slack SHIP_RECEIPT talk is CLAIMED." };
        paintSlackReceipt(missing);
        return missing;
      }
      if (!catalogRes.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + catalogRes.status + ". Absence was not measured." };
        paintSlackReceipt(failed);
        return failed;
      }
      return catalogRes.json().then(function (catalog) {
        var sourceId = String((catalog && catalog.source_id) || "").trim();
        var paths = (catalog && catalog.source_paths) || [];
        var receiptUrl = RAW + sha + "/p/" + encodeURIComponent(sourceId) + ".md";
        var pathGets = paths.map(function (path) {
          return fetch(RAW + sha + "/" + String(path || "").split("/").map(encodeURIComponent).join("/"), { cache: "no-store" }).then(function (r) {
            return { path: path, ok: r.status === 200 };
          });
        });
        return Promise.all([fetch(receiptUrl, { cache: "no-store" })].concat(pathGets)).then(function (parts) {
          var receiptRes = parts[0];
          var present = [];
          var i;
          for (i = 1; i < parts.length; i += 1) {
            if (parts[i] && parts[i].ok) present.push(parts[i].path);
          }
          var got = api.slackReceiptState({
            measured: true,
            source_id: sourceId,
            source_paths: paths,
            present_paths: present,
            receipt_present: receiptRes.status === 200
          });
          paintSlackReceipt(got);
          return got;
        });
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintSlackReceipt(err);
      return err;
    });
  }

  function loadGrokRecovery(sha) {
    if (!grokRecoveryOut) return Promise.resolve(null);
    grokRecoveryOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/grok_recovery.py at the official SHA…</p>";
    var url = RAW + sha + "/host/grok_recovery.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/grok_recovery.py absent at the measured main SHA. Grok-recovery / muhlnickel-subagent talk is CLAIMED." };
        paintGrokRecovery(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintGrokRecovery(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.grokRecoveryState(body);
        paintGrokRecovery(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintGrokRecovery(err);
      return err;
    });
  }

  function loadClaudeTester(sha) {
    if (!claudeTesterOut) return Promise.resolve(null);
    claudeTesterOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/claude_tester.py at the official SHA…</p>";
    var url = RAW + sha + "/host/claude_tester.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/claude_tester.py absent at the measured main SHA. Stop-using-Claude-testers talk is CLAIMED." };
        paintClaudeTester(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintClaudeTester(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.claudeTesterState(body);
        paintClaudeTester(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintClaudeTester(err);
      return err;
    });
  }

  function loadWatchdogHeadProof(sha) {
    if (!watchdogHeadProofOut) return Promise.resolve(null);
    watchdogHeadProofOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/watchdog_head_proof.py at the official SHA…</p>";
    var url = RAW + sha + "/host/watchdog_head_proof.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/watchdog_head_proof.py absent at the measured main SHA. SPECTER HEAD-proof taking is CLAIMED." };
        paintWatchdogHeadProof(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintWatchdogHeadProof(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.watchdogHeadProofState(body);
        paintWatchdogHeadProof(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintWatchdogHeadProof(err);
      return err;
    });
  }

  function loadMcpWakeJob(sha) {
    if (!mcpWakeJobOut) return Promise.resolve(null);
    mcpWakeJobOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/mcp_wake_job.py at the official SHA…</p>";
    var url = RAW + sha + "/host/mcp_wake_job.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/mcp_wake_job.py absent at the measured main SHA. SPECTER pivot / MCP-wake real-job talk is CLAIMED." };
        paintMcpWakeJob(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintMcpWakeJob(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.mcpWakeJobState(body);
        paintMcpWakeJob(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintMcpWakeJob(err);
      return err;
    });
  }

  function loadMcpWake(sha) {
    if (!mcpWakeOut) return Promise.resolve(null);
    mcpWakeOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/mcp_wake.py at the official SHA…</p>";
    var url = RAW + sha + "/host/mcp_wake.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/mcp_wake.py absent at the measured main SHA. Collision-hold / MCP-wake talk is CLAIMED." };
        paintMcpWake(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintMcpWake(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.mcpWakeState(body);
        paintMcpWake(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintMcpWake(err);
      return err;
    });
  }

  function loadHostZero(sha) {
    if (!hostZeroOut) return Promise.resolve(null);
    hostZeroOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/host_zero.py at the official SHA…</p>";
    var url = RAW + sha + "/host/host_zero.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/host_zero.py absent at the measured main SHA. Host-zero talk is CLAIMED." };
        paintHostZero(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintHostZero(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.hostZeroState(body);
        paintHostZero(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintHostZero(err);
      return err;
    });
  }

  function loadConnectorReval(sha) {
    if (!connectorOut) return Promise.resolve(null);
    connectorOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/connector_reval.py at the official SHA…</p>";
    var url = RAW + sha + "/host/connector_reval.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/connector_reval.py absent at the measured main SHA. Connector-utilization talk is CLAIMED." };
        paintConnectorReval(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintConnectorReval(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.connectorRevalState(body);
        paintConnectorReval(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintConnectorReval(err);
      return err;
    });
  }

  function loadResourceLedger(sha) {
    if (!ledgerOut) return Promise.resolve(null);
    ledgerOut.innerHTML = "<b>UNMEASURED</b><p>Reading host/resource_ledger.py at the official SHA…</p>";
    var url = RAW + sha + "/host/resource_ledger.py";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (r.status === 404) {
        var missing = { state: "NOT_LANDED", note: "host/resource_ledger.py absent at the measured main SHA. Cache-as-capacity talk is CLAIMED." };
        paintResourceLedger(missing);
        return missing;
      }
      if (!r.ok) {
        var failed = { state: "UNMEASURED", note: "lookup failed HTTP " + r.status + ". Absence was not measured." };
        paintResourceLedger(failed);
        return failed;
      }
      return r.text().then(function (body) {
        var got = api.resourceLedgerState(body);
        paintResourceLedger(got);
        return got;
      });
    }).catch(function (e) {
      var err = { state: "UNMEASURED", note: "fetch failed (" + e.message + "). Absence was not measured." };
      paintResourceLedger(err);
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
        var receiptUrl = RAW + sha + "/p/claudelocal-titan-move-go-20260825-01.md";
        return Promise.all([
          fetch(journalUrl, { cache: "no-store" }).then(function (jr) {
            return jr.ok ? jr.json() : null;
          }).catch(function () { return null; }),
          fetch(receiptUrl, { cache: "no-store" }).then(function (rr) {
            return rr.ok ? rr.text() : "";
          }).catch(function () { return ""; })
        ]).then(function (evidence) {
          var got = api.titanMoveState(api.packetRowFromJson(data, evidence[0], evidence[1]));
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
    loadDevicePathCensus(sha);
    loadDeviceChurn(sha);
    loadStrandedMap(sha);
    loadHostZero(sha);
    loadConnectorReval(sha);
    loadRenderContract(sha);
    loadWorkingBuilds(sha);
    loadSlackReceipt(sha);
    loadResourceLedger(sha);
    loadWatchdogHeadProof(sha);
    loadMcpWakeJob(sha);
    loadMcpWake(sha);
    loadFinderZero(sha);
    loadStaleManifest(sha);
    loadClaudeTester(sha);
    loadClaudeZero(sha);
    loadImpactLedger(sha);
    loadClaudeZeroDamage(sha);
    loadXyzZero(sha);
    loadTitanAppendGuard(sha);
    loadMeasureAbuse(sha);
    loadClaudePark(sha);
    loadRemeasure(sha);
    loadGrokRecovery(sha);
    loadContextIntegrity(sha);
    loadClaudeRole(sha);
    loadTitanTestQuarantine(sha);
    loadGrokHygiene(sha);
    loadMemoryShip(sha);
    loadSittingRemint(sha);
    loadForeignMain(sha);
    loadDeviceCanary(sha);
    loadClaudeCompute(sha);
    loadClaudeIntermediate(sha);
    loadCashNow(sha);
    loadJojoAssign(sha);
    loadContainment(sha);
    loadWatchdogCanary(sha);
    loadBranchReview(sha);
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
