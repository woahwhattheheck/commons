(function () {
  "use strict";

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
        cell(truth.live_next_actions, "live next"),
        cell(truth.external_prospects, "prospects"),
        cell(truth.inbound_contacts, "inbound"),
        cell(truth.seller_context_rows, "seller context"),
        cell(truth.transport_actions, "sent"),
        cell("USD " + truth.cash_usd, "cash")
      );
    }
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
      renderIndex(parseIndex(pair[1]));
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
