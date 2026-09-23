"use strict";

// Load after app.js. Keep the shared app and its receipt-bound saved drafts intact.
(() => {
  if (!globalThis.UIowaReviewNavigation || document.getElementById("review-navigation")) return;
  let selectionRequest = 0;
  function afterTransition(action) {
    const request = ++selectionRequest, generation = state.generation, hash = location.hash;
    // Other adapters may restore their selected cell after installReport returns.
    // Apply only the final navigation selection, before the next browser paint.
    queueMicrotask(() => {
      if (request === selectionRequest && generation === state.generation && hash === location.hash) action();
    });
  }
  const navigation = UIowaReviewNavigation.attach({
    clearSelection: () => afterTransition(() => {
      state.selectedKey = null; renderMatrix();
      el.detail.textContent = "No cell selected: resolve the review link below.";
      el.cellSummary.replaceChildren();
      const heading = appendText(el.cellSummary, "h3", "No cell selected");
      heading.id = "selectedCellHeading"; heading.tabIndex = -1;
      el.sourceList.replaceChildren(); el.backToCellBtn.disabled = true;
      el.note.value = ""; el.note.disabled = true;
      el.disposition.value = "UNREVIEWED"; el.disposition.disabled = true;
    }),
    selectCell: key => afterTransition(() => {
      el.search.value = ""; el.statusFilter.value = "";
      selectCell(key, false);
    })
  });
  let generation = state.generation;
  function syncReport() {
    // A failed draft-preservation attempt leaves both report and review packet intact.
    if (generation === state.generation) return;
    generation = state.generation;
    navigation.setReport(state.report);
  }
  const originalInstall = installReport;
  installReport = function (...args) {
    try { return originalInstall.apply(this, args); }
    finally { syncReport(); }
  };
  const originalReset = resetWorkbench;
  resetWorkbench = function (...args) {
    try { return originalReset.apply(this, args); }
    finally { syncReport(); }
  };
  // app.js already registered its original reset function as a click listener.
  // Observe it after that listener; programmatic resets use the wrapper above.
  el.resetBtn.addEventListener("click", syncReport);
  navigation.setReport(state.report);
})();
