;(function () {
  function apply() {
    if (window.__CURATION_TEST && window.__CURATION_TEST.isError) {
      var cpf = document.getElementById("campo-cpf");
      if (cpf) {
        cpf.addEventListener("input", function() {
          var v = this.value.replace(/\D/g, "").slice(0, 11);
          if (v.length > 9) v = v.slice(0, 3) + "." + v.slice(3, 6) + "." + v.slice(6, 9) + "-" + v.slice(9);
          else if (v.length > 6) v = v.slice(0, 3) + "." + v.slice(3, 6) + "." + v.slice(6);
          else if (v.length > 3) v = v.slice(0, 3) + "." + v.slice(3);
          this.value = v;
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
