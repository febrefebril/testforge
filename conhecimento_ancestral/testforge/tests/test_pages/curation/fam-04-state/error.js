;(function () {
  function apply() {
    if (window.__CURATION_TEST && window.__CURATION_TEST.isError) {
      var btn = document.getElementById("btn-confirmar");
      if (btn) {
        btn.disabled = true;
        var adv = document.getElementById("btn-avancar");
        if (adv) adv.style.display = "none";
      }
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
