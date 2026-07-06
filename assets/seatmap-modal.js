(function () {
  function onReady(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback);
      return;
    }
    callback();
  }

  onReady(function () {
    var triggers = Array.prototype.slice.call(document.querySelectorAll("[data-seatmap-dialog]"));
    if (!triggers.length) return;

    var modal = document.createElement("div");
    modal.className = "seatmap-modal";
    modal.hidden = true;
    modal.innerHTML = [
      '<div class="seatmap-modal__backdrop" data-seatmap-close></div>',
      '<section class="seatmap-modal__panel" role="dialog" aria-modal="true" aria-labelledby="seatmap-modal-title">',
      '  <header class="seatmap-modal__header">',
      "    <div>",
      '      <p class="seatmap-modal__eyebrow">Seat map snapshot</p>',
      '      <h2 class="seatmap-modal__title" id="seatmap-modal-title"></h2>',
      "    </div>",
      '    <a class="seatmap-modal__open" href="#" target="_blank" rel="noopener noreferrer">另開頁面</a>',
      '    <button class="seatmap-modal__close" type="button" aria-label="關閉座位圖" data-seatmap-close>&times;</button>',
      "  </header>",
      '  <iframe class="seatmap-modal__frame" title="座位圖快照" loading="lazy"></iframe>',
      "</section>",
    ].join("");
    document.body.appendChild(modal);

    var title = modal.querySelector("#seatmap-modal-title");
    var frame = modal.querySelector(".seatmap-modal__frame");
    var openLink = modal.querySelector(".seatmap-modal__open");
    var closeButton = modal.querySelector(".seatmap-modal__close");
    var lastTrigger = null;

    function getTitle(trigger) {
      if (trigger.dataset.seatmapTitle) return trigger.dataset.seatmapTitle;
      var row = trigger.closest("li");
      if (row) {
        var label = row.querySelector("span");
        if (label && label.textContent.trim()) return label.textContent.trim();
      }
      return "座位圖快照";
    }

    function openModal(trigger) {
      var href = trigger.getAttribute("href");
      if (!href) return;
      lastTrigger = trigger;
      title.textContent = getTitle(trigger);
      openLink.href = href;
      frame.src = href;
      modal.hidden = false;
      document.documentElement.classList.add("seatmap-modal-open");
      closeButton.focus();
    }

    function closeModal() {
      if (modal.hidden) return;
      modal.hidden = true;
      frame.src = "about:blank";
      document.documentElement.classList.remove("seatmap-modal-open");
      if (lastTrigger) lastTrigger.focus();
    }

    triggers.forEach(function (trigger) {
      trigger.setAttribute("aria-haspopup", "dialog");
      trigger.addEventListener("click", function (event) {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
        event.preventDefault();
        openModal(trigger);
      });
    });

    modal.addEventListener("click", function (event) {
      if (event.target.closest("[data-seatmap-close]")) closeModal();
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeModal();
    });
  });
})();
