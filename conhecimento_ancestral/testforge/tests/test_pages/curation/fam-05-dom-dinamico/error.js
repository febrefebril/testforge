;(function () {
  function apply() {
    if (window.__CURATION_TEST && window.__CURATION_TEST.isError) {
      var container = document.getElementById("container");
      if (container) {
        container.innerHTML = '<ul id="lista-itens"><li data-testid="item-3">Item 3</li><li data-testid="item-1">Item 1</li></ul>';
      }
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
