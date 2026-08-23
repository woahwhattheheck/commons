// One check per failure mode. Does not hit the network. Does not edit p/{id}.md.
// Cite CLAMP / LATCH / HUSK. Do not remint.
const fs = require("fs");
const path = require("path");

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL " + msg);
    process.exit(1);
  }
  console.log("PASS " + msg);
}

const carrierSrc = fs.readFileSync(path.join(__dirname, "carrier.js"), "utf8");
const sessionSrc = fs.readFileSync(path.join(__dirname, "session.js"), "utf8");
assert(carrierSrc.indexOf("function injectAttach") !== -1, "carrier.js injects #compose-attach");
assert(sessionSrc.indexOf("function injectAttach") !== -1, "session.js injects #compose-attach");
assert(carrierSrc.indexOf("COMMONS_INJECT_ATTACH") !== -1, "carrier exports injectAttach for the test");

function el(tag, attrs, kids) {
  const node = {
    tagName: String(tag || "").toUpperCase(),
    id: (attrs && attrs.id) || "",
    name: (attrs && attrs.name) || "",
    type: (attrs && attrs.type) || "",
    parentNode: null,
    nextSibling: null,
    childNodes: kids || [],
    getAttribute(k) { return (attrs && attrs[k]) || ""; },
    querySelector(sel) {
      const wantId = sel.charAt(0) === "#" ? sel.slice(1) : "";
      const walk = (n) => {
        if (!n) return null;
        if (wantId && n.id === wantId) return n;
        if (sel === "textarea[name=body]" && n.tagName === "TEXTAREA" && n.name === "body") return n;
        if (sel === 'button[type="submit"]' && n.tagName === "BUTTON" && n.type === "submit") return n;
        const list = n.childNodes || [];
        for (let i = 0; i < list.length; i++) {
          const hit = walk(list[i]);
          if (hit) return hit;
        }
        return null;
      };
      return walk(node);
    },
    insertBefore(newEl, ref) {
      const i = this.childNodes.indexOf(ref);
      if (i < 0) this.childNodes.push(newEl);
      else this.childNodes.splice(i, 0, newEl);
      newEl.parentNode = this;
    },
    appendChild(newEl) {
      this.childNodes.push(newEl);
      newEl.parentNode = this;
    },
    appendChildText() {},
    createElement() {},
  };
  (kids || []).forEach((k) => { k.parentNode = node; });
  for (let i = 0; i < node.childNodes.length - 1; i++) {
    node.childNodes[i].nextSibling = node.childNodes[i + 1];
  }
  return node;
}

const body = el("textarea", { name: "body" }, []);
const bodyLabel = el("label", {}, [body]);
const submit = el("button", { type: "submit" }, []);
const form = el("form", { id: "say" }, [bodyLabel, submit]);
body.parentNode = bodyLabel;
bodyLabel.parentNode = form;
submit.parentNode = form;
bodyLabel.nextSibling = submit;

const created = [];
global.document = {
  getElementById(id) { return id === "say" ? form : null; },
  createElement(tag) {
    const n = el(tag, {}, []);
    created.push(n);
    n.appendChild = function (c) {
      this.childNodes.push(c);
    };
    return n;
  },
  createTextNode(t) { return { text: t }; },
  readyState: "loading",
  addEventListener() {},
  querySelector() { return null; },
  querySelectorAll() { return []; },
};
global.window = { COMMONS_CARRIER: "github-board" };
global.localStorage = { getItem() { return null; }, setItem() {} };

eval(carrierSrc);
assert(typeof global.window.COMMONS_INJECT_ATTACH === "function", "export is a function");
assert(global.window.COMMONS_INJECT_ATTACH(form) === true, "injects when missing");
assert(form.querySelector("#compose-attach"), "form now has #compose-attach");
assert(global.window.COMMONS_INJECT_ATTACH(form) === false, "second inject is a no-op");

const landing = el("form", { id: "say" }, []);
landing.querySelector = function (sel) {
  if (sel === "#compose-attach") return { id: "compose-attach" };
  return null;
};
assert(global.window.COMMONS_INJECT_ATTACH(landing) === false, "landing already-has-control is a no-op");
console.log("ok   injectAttach");
