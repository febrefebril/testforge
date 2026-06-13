;(function () {
  function apply() {
    if (window.__CURATION_TEST && window.__CURATION_TEST.isError) {
      var upload = document.getElementById("file-upload");
      if (upload) {
        upload.removeAttribute("accept");
        upload.setAttribute("data-error", "multiple_removed");
      }
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
