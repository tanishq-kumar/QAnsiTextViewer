// Tractor feed: the sprocket rails move with the scroll at paper speed,
// and every listing gets a header strip with its line count.
(function () {
  var root = document.documentElement;
  var still = window.matchMedia("(prefers-reduced-motion: reduce)");
  var queued = false;

  function feed() {
    queued = false;
    root.style.setProperty("--gb-feed", -window.scrollY + "px");
  }

  function onScroll() {
    if (still.matches || queued) return;
    queued = true;
    window.requestAnimationFrame(feed);
  }

  function lineLabel(code) {
    var n = code.textContent.replace(/\n$/, "").split("\n").length;
    return n === 1 ? "1 line" : "Lines 1-" + n;
  }

  function stripListings() {
    document.querySelectorAll(".md-content .highlight").forEach(function (block) {
      // A titled block with line numbers nests a second .highlight; skip it.
      if (block.parentElement.closest(".highlight")) return;
      var code = block.querySelector("pre > code");
      if (!code) return;
      var head = block.querySelector("span.filename");
      if (!head) {
        head = document.createElement("span");
        head.className = "filename gb-auto";
        head.textContent = "Listing";
        block.insertBefore(head, block.firstChild);
      }
      head.setAttribute("data-gb-lines", lineLabel(code));
    });
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  if (typeof document$ !== "undefined") {
    document$.subscribe(stripListings);
  } else {
    document.addEventListener("DOMContentLoaded", stripListings);
  }
  feed();
})();
