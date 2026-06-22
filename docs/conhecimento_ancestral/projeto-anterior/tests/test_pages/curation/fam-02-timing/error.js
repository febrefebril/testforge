;(function () {
  function apply() {
    if (window.__CURATION_TEST && window.__CURATION_TEST.isError) {
      var p = document.querySelector("#container p");
      if (p) p.textContent = "Carregando... (simulando lentidão)";
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
