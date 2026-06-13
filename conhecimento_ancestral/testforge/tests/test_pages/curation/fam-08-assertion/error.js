;(function () {
  function apply() {
    if (window.__CURATION_TEST && window.__CURATION_TEST.isError) {
      var btn = document.getElementById("btn-processar");
      if (btn) {
        btn.addEventListener("click", function() {
          document.getElementById("status").textContent = "Status: Erro ao processar";
        });
      }
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
