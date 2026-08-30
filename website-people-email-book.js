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

  function render(loop) {
    if (!loop || loop.kind !== "WEBSITE_PEOPLE_EMAIL_BOOK_LOOP") {
      throw new Error("unsupported loop snapshot");
    }
    var truth = loop.truth || {};
    var status = document.getElementById("loop-status");
    if (status) {
      status.textContent =
        "Measured " +
        loop.generated_at +
        ". " +
        truth.websites_ingested +
        " website, " +
        truth.people_found +
        " people, " +
        truth.emails_drafted +
        " drafts, " +
        truth.calls_booked +
        " booked, " +
        truth.transport_actions +
        " sent, mailbox " +
        truth.mailbox +
        ".";
    }
    var truthRoot = document.getElementById("truth");
    if (truthRoot) {
      truthRoot.replaceChildren(
        cell(truth.websites_ingested, "website"),
        cell(truth.people_found, "people"),
        cell(truth.emails_drafted, "drafts"),
        cell(truth.calls_booked, "booked"),
        cell(truth.transport_actions, "sent"),
        cell("USD " + truth.cash_usd, "cash")
      );
    }
    var body = document.getElementById("people");
    if (body) {
      body.replaceChildren();
      (loop.people || []).forEach(function (row) {
        var tr = document.createElement("tr");
        tr.appendChild(text("td", row.name));
        tr.appendChild(text("td", row.role || ""));
        tr.appendChild(text("td", row.email || "UNVERIFIED"));
        tr.appendChild(text("td", row.need || ""));
        tr.appendChild(text("td", row.next_action || ""));
        body.appendChild(tr);
      });
    }
  }

  function previewHtml(html) {
    var doc = new DOMParser().parseFromString(html, "text/html");
    var title = doc.querySelector("title") ? doc.querySelector("title").textContent : "";
    var people = [];
    var nodes = doc.querySelectorAll("[data-person], [itemtype*='Person']");
    nodes.forEach(function (node) {
      var nameNode = node.querySelector("[itemprop='name'], h2, h3");
      var mail = node.querySelector("a[href^='mailto:']");
      var needNode = node.querySelector("[data-need], blockquote");
      var email = mail ? String(mail.getAttribute("href") || "").replace(/^mailto:/i, "").split("?")[0] : "";
      people.push({
        name: nameNode ? nameNode.textContent.trim() : "",
        email: email,
        need: needNode ? needNode.textContent.trim() : ""
      });
    });
    return { title: title.trim(), people: people, sent: 0 };
  }

  var button = document.getElementById("preview");
  if (button) {
    button.addEventListener("click", function () {
      var paste = document.getElementById("paste");
      var out = document.getElementById("preview-out");
      if (!paste || !out) return;
      var result = previewHtml(paste.value || "");
      out.textContent =
        (result.title || "(no title)") +
        " — " +
        result.people.length +
        " people, " +
        result.sent +
        " sent. " +
        result.people
          .map(function (person) {
            return (person.name || "unnamed") + (person.email ? " <" + person.email + ">" : " (no mailto)");
          })
          .join("; ");
    });
  }

  fetch("./revenue/website_people_email_book/loop.json", { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) throw new Error("loop.json " + response.status);
      return response.json();
    })
    .then(render)
    .catch(function (error) {
      var status = document.getElementById("loop-status");
      if (status) {
        status.textContent =
          "Live loop.json unavailable. Noscript numbers remain the last landed snapshot. " +
          error.message;
      }
    });
})();
