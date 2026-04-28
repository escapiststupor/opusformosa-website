document.addEventListener("DOMContentLoaded", function () {
  var t = document.getElementById("nav-toggle");
  var m = document.getElementById("nav-menu");
  var openIcon = document.getElementById("nav-icon-open");
  var closeIcon = document.getElementById("nav-icon-close");
  if (t && m) {
    t.addEventListener("click", function () {
      m.classList.toggle("hidden");
      if (openIcon && closeIcon) {
        openIcon.classList.toggle("hidden");
        closeIcon.classList.toggle("hidden");
      }
      t.setAttribute("aria-expanded", m.classList.contains("hidden") ? "false" : "true");
    });
  }
});
