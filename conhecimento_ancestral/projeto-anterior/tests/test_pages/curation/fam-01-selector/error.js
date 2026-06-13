;(function () {
  function apply() {
    if (window.__CURATION_TEST && window.__CURATION_TEST.isError) {
      var btn = document.getElementById("btn-salvar");
      if (btn) {
        btn.removeAttribute("data-testid");
        btn.removeAttribute("id");
      }
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
