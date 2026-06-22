;(function () {
  function apply() {
    if (window.__CURATION_TEST && window.__CURATION_TEST.isError) {
      var iframe = document.getElementById("iframe-content");
      if (iframe) iframe.srcdoc = "";
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
