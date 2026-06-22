;(function () {
  function apply() {
    if (window.__CURATION_TEST && window.__CURATION_TEST.isError) {
      var select = document.getElementById("select-estado");
      if (select) {
        var div = document.createElement("div");
        div.id = "select-estado";
        div.setAttribute("data-simulado", "true");
        var valores = ["", "SP", "RJ", "MG"];
        var textos = ["Selecione...", "São Paulo", "Rio de Janeiro", "Minas Gerais"];
        valores.forEach(function(v, i) {
          var opt = document.createElement("div");
          opt.setAttribute("data-value", v);
          opt.textContent = textos[i];
          opt.style.cursor = "pointer";
          opt.addEventListener("click", function() {
            div.setAttribute("data-selected", v);
            div.textContent = "Selecionado: " + textos[i];
          });
          div.appendChild(opt);
        });
        select.parentNode.replaceChild(div, select);
      }
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
