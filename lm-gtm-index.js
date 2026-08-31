(function () {
  "use strict";

  var HOLD = {
    HOLD_DO_NOT_RESEND: true,
    HOLD_DO_NOT_CONTACT: true
  };

  function text(tag, value, className) {
    var node = document.createElement(tag);
    node.textContent = String(value == null ? "" : value);
    if (className) node.className = className;
    return node;
  }

  function cell(value, label) {
    var node = document.createElement("span");
    node.appendChild(text("b", value));
    node.appendChild(document.createTextNode(label));
    return node;
  }

  function hotClass(row) {
    var role = row && row.role;
    if (role !== "external_prospect" && role !== "inbound_contact") return null;
    if (!row.live) return null;
    if (row.decision === "MATERIAL_REPLY") return "material_reply";
    if (row.dnr || HOLD[row.decision]) return null;
    if (row.decision === "SENT_AWAITING_REPLY") return "sent_awaiting_reply";
    if (row.decision === "READY_TO_DRAFT") return "ready_to_draft";
    if (row.decision === "VERIFIED_LEAD_UNSENT") return "verified_lead_unsent";
    return null;
  }

  var HOT_RANK = {
    material_reply: 0,
    sent_awaiting_reply: 1,
    ready_to_draft: 2,
    verified_lead_unsent: 3
  };

  function parseIndex(raw) {
    var rows = [];
    var header = null;
    String(raw || "").split(/\n/).forEach(function (line) {
      line = line.trim();
      if (!line) return;
      var item = JSON.parse(line);
      if (item.kind === "LM_GTM_INDEX_HEADER") header = item;
      else if (item.kind === "LM_GTM_INDEX_ROW") rows.push(item);
    });
    return { header: header, rows: rows };
  }

  function renderState(state) {
    if (!state || state.kind !== "LM_GTM_INDEX_STATE") {
      throw new Error("unsupported GTM index state");
    }
    var truth = state.truth || {};
    var status = document.getElementById("index-status");
    if (status) {
      status.textContent =
        "Composed " +
        state.composed_at +
        ". Canonical CRM " +
        state.canonical_crm +
        ". " +
        (truth.hot_next_actions || 0) +
        " hot, " +
        truth.live_next_actions +
        " live next-actions, " +
        truth.external_prospects +
        " external prospects, mailbox " +
        truth.mailbox +
        ", USD " +
        truth.cash_usd +
        " cash. Public projection is not a CRM.";
    }
    var truthRoot = document.getElementById("truth");
    if (truthRoot) {
      truthRoot.replaceChildren(
        cell(truth.hot_next_actions || 0, "hot"),
        cell(truth.live_next_actions, "live next"),
        cell(truth.external_prospects, "prospects"),
        cell(truth.inbound_contacts, "inbound"),
        cell(truth.seller_context_rows, "seller context"),
        cell(truth.transport_actions, "sent by this composer"),
        cell("USD " + truth.cash_usd, "cash")
      );
    }
  }

  function renderHot(parsed) {
    var body = document.getElementById("hot-actions");
    if (!body) return;
    body.replaceChildren();
    var ranked = [];
    (parsed.rows || []).forEach(function (row) {
      var klass = hotClass(row);
      if (!klass) return;
      ranked.push({ row: row, klass: klass, rank: HOT_RANK[klass] });
    });
    ranked.sort(function (a, b) {
      if (a.rank !== b.rank) return a.rank - b.rank;
      return String(a.row.id).localeCompare(String(b.row.id));
    });
    ranked.forEach(function (item) {
      var row = item.row;
      var tr = document.createElement("tr");
      tr.appendChild(text("td", item.klass));
      tr.appendChild(text("td", row.id));
      tr.appendChild(text("td", row.organization || ""));
      tr.appendChild(text("td", row.person || ""));
      tr.appendChild(text("td", row.decision || ""));
      tr.appendChild(text("td", row.next_action || ""));
      tr.appendChild(text("td", row.owner || "UNSEATED"));
      body.appendChild(tr);
    });
  }

  function renderIndex(parsed) {
    var body = document.getElementById("next-actions");
    if (!body) return;
    body.replaceChildren();
    (parsed.rows || []).forEach(function (row) {
      if (!row.live) return;
      var tr = document.createElement("tr");
      tr.appendChild(text("td", row.id));
      tr.appendChild(text("td", row.organization || ""));
      tr.appendChild(text("td", row.decision || ""));
      tr.appendChild(text("td", row.next_action || ""));
      tr.appendChild(text("td", row.route_ref || row.route_kind || ""));
      tr.appendChild(text("td", row.owner || "UNSEATED"));
      body.appendChild(tr);
    });
  }

  Promise.all([
    fetch("./revenue/lm_gtm_index/state.json", { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error("state.json " + response.status);
      return response.json();
    }),
    fetch("./revenue/lm_gtm_index/INDEX.jsonl", { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error("INDEX.jsonl " + response.status);
      return response.text();
    })
  ])
    .then(function (pair) {
      renderState(pair[0]);
      var parsed = parseIndex(pair[1]);
      renderHot(parsed);
      renderIndex(parsed);
    })
    .catch(function (error) {
      var status = document.getElementById("index-status");
      if (status) {
        status.textContent =
          "Live INDEX unavailable. Noscript numbers remain the last landed snapshot. " +
          error.message;
      }
    });
})();
