;(function () {
  function apply() {
    if (window.__CURATION_TEST && window.__CURATION_TEST.isError) {
      console.error("Erro simulado: dialog blocking execution");
      var btn = document.getElementById("btn-alert");
      if (btn) {
        btn.addEventListener("click", function() {
          try {
            alert("Alerta bloqueante");
            document.getElementById("result").textContent = "Alert fechado!";
          } catch (e) {
            console.error("Dialog blocked:", e);
          }
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
