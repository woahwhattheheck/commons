(function () {
  "use strict";

  var target = document.getElementById("revenue-control");
  if (!target || typeof fetch !== "function") return;

  function text(tag, value, className) {
    var node = document.createElement(tag);
    node.textContent = String(value);
    if (className) node.className = className;
    return node;
  }

  function formatTotals(rows) {
    if (!Array.isArray(rows) || !rows.length) return "None evidenced";
    return rows.map(function (row) {
      return row.amount + " " + row.currency;
    }).join(" · ");
  }

  function render(control) {
    target.replaceChildren();
    var truth = control.truth;
    var settled = control.settled_awards;
    var summary = document.createElement("div");
    summary.className = "metrics";
    [
      ["USD cash", "USD " + truth.collected_cash_usd],
      ["Paid awards", truth.paid_awards],
      ["Settled value", formatTotals(truth.settled_amounts_by_currency)],
      ["Offers", control.offers.length],
      ["Opportunities", truth.prospects_evaluated],
      ["Ready to draft", truth.ready_to_draft],
      ["Transport actions", truth.transport_actions]
    ].forEach(function (pair) {
      var metric = document.createElement("div");
      metric.className = "metric";
      metric.append(text("span", pair[0], "metric-label"));
      metric.append(text("strong", pair[1]));
      summary.append(metric);
    });
    target.append(summary);

    target.append(text("h3", "Verified paid awards"));
    var awardList = document.createElement("ol");
    awardList.className = "queue";
    settled.awards.forEach(function (award) {
      var row = document.createElement("li");
      row.append(text(
        "strong",
        award.program + " — " + award.amount + " " + award.currency + " PAID"
      ));
      row.append(text(
        "span",
        "Paid " + award.paid_at + " to hosted handle " +
          award.destination_reference + ". Collection: do not resend."
      ));
      awardList.append(row);
    });
    if (!settled.awards.length) {
      awardList.append(text("li", "No sponsor-confirmed paid awards are recorded."));
    }
    target.append(awardList);
    target.append(text(
      "p",
      "Award currencies remain separate. No USD conversion, bank availability, or withdrawability is asserted.",
      "note"
    ));

    target.append(text("h3", "Evidence-ranked execution queue"));
    var list = document.createElement("ol");
    list.className = "queue";
    control.execution_queue.forEach(function (item) {
      var row = document.createElement("li");
      row.append(text("strong", item.organization + " — " + item.decision));
      row.append(text("span", "Fit " + item.fit_score + "/100 · " + item.next_action));
      list.append(row);
    });
    if (!control.execution_queue.length) {
      list.append(text("li", "No evidenced opportunities are currently queued."));
    }
    target.append(list);

    target.append(text("h3", "Shortest honest blockers"));
    var blockerList = document.createElement("ol");
    blockerList.className = "queue";
    control.blockers.forEach(function (item) {
      var row = document.createElement("li");
      row.append(text("strong", item.id));
      row.append(text("span", item.condition + " Current: " + item.current));
      blockerList.append(row);
    });
    target.append(blockerList);
  }

  fetch("./revenue/right_now/control.json", {cache: "no-store"})
    .then(function (response) {
      if (!response.ok) throw new Error("control snapshot unavailable");
      return response.json();
    })
    .then(render)
    .catch(function () {
      target.dataset.state = "fallback";
    });
}());
