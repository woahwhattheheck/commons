/* The existing command center's review view. No inference or dispatch. */
(() => {
  "use strict";
  const root = "https://raw.githubusercontent.com/woahwhattheheck/commons/state/coordination/";
  const panel = document.getElementById("swarm-order");
  if (!panel) return;
  let previous = null, state = null, busy = false;
  const row = (tag, text, parent) => {
    const node = document.createElement(tag); node.textContent = text; parent.appendChild(node); return node;
  };
  async function read(name) {
    const response = await fetch(root + name, {cache: "no-store", signal: AbortSignal.timeout(12000)});
    if (!response.ok) throw new Error("HTTP " + response.status);
    return response.json();
  }
  function render(error) {
    const box = document.getElementById("swarm-rows");
    box.replaceChildren();
    const observed = state && state.observed_at;
    const age = observed ? (Date.now() - Date.parse(observed)) / 1000 : NaN;
    const stale = !Number.isFinite(age) || age < -300 || age >= 600 || error;
    document.getElementById("swarm-freshness").textContent = stale ? "STALE / re-read live PRs" : "Current observation";
    const swarm = state && state.swarm;
    if (!swarm) {
      row("li", "Review state has not been published. Run the existing coordination publisher; missing data is not clearance.", box);
    } else {
      row("li", Object.entries(swarm.counts || {}).map(([k,v]) => k + ": " + v).join(" · "), box);
      for (const batch of (swarm.batches || []).slice(0, 12)) {
        row("li", "GPT batch: " + batch.prs.map(n => "#" + n).join(", ") + " · " + batch.dispatch +
          (batch.independent_preflight ? " · independent preflight required" : ""), box);
      }
      for (const pr of (state.prs || []).filter(p => p.swarm).slice(0, 50)) {
        const item = row("li", "", box);
        const link = row("a", "#" + pr.number + " " + pr.title, item);
        link.href = "https://github.com/woahwhattheheck/commons/pull/" + Number(pr.number);
        row("div", (pr.swarm.work?.seat || "seat undeclared") + " · " +
          (pr.swarm.review?.state || "UNKNOWN") + " · " + (pr.swarm.review?.reason || ""), item);
      }
    }
    document.getElementById("swarm-source").textContent =
      "Observed " + (observed || "unknown") + (error ? " · Read failed: " + error : "") +
      ". GPTs build and lead. This view records observations; integration rechecks live bytes.";
  }
  async function refresh() {
    if (busy || document.visibilityState === "hidden") return;
    busy = true;
    try {
      const head = await read("coordination-head.json");
      if (!state || head.observed_at !== previous) {
        state = await read("coordination.json"); previous = state.observed_at;
      }
      render(null);
    } catch (error) { render(String(error.message)); }
    finally { busy = false; }
  }
  document.getElementById("swarm-refresh").addEventListener("click", () => { previous = null; refresh(); });
  document.addEventListener("visibilitychange", refresh);
  refresh(); setInterval(refresh, 60000);
})();
