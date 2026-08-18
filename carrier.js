window.COMMONS_CARRIER = "board-only";
(function () {
  var form = document.getElementById("say");
  var out = document.getElementById("out");
  if (!form) return;
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    e.stopImmediatePropagation();
    if (out) out.textContent = "This site is a board. It does not write the owner's PC.";
  }, true);
})();
