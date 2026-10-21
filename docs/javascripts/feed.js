// Tractor feed: the sprocket rails move with the scroll at paper speed,
// and every listing gets a header strip with its line count.
(function () {
  var PITCH = 36; // must match --gb-pitch
  var still = window.matchMedia("(prefers-reduced-motion: reduce)");
  var rails = document.getElementsByClassName("gb-feed");
  var queued = false;

  // Each rail is one pitch taller than the viewport; sliding it up by
  // (scrollY mod pitch) looks like endless paper and only moves layers.
  function feed() {
    queued = false;
    var offset = still.matches ? 0 : -(window.scrollY % PITCH);
    for (var i = 0; i < rails.length; i++) {
      rails[i].style.transform = "translateY(" + offset + "px)";
    }
  }

  function onScroll() {
    if (still.matches || queued) return;
    queued = true;
    window.requestAnimationFrame(feed);
  }

  still.addEventListener("change", feed);

  function countLines(code) {
    return code.textContent.replace(/\n$/, "").split("\n").length;
  }

  // Numbered listings are whole files ("Lines 1-11"); fragments that go
  // inside other code only report their size ("4 lines").
  function lineLabel(n, numbered) {
    if (n === 1) return "1 line";
    return numbered ? "Lines 1-" + n : n + " lines";
  }

  function stripListings() {
    document.querySelectorAll(".md-content .highlight").forEach(function (block) {
      // A titled block with line numbers nests a second .highlight; skip it.
      if (block.parentElement.closest(".highlight")) return;
      var code = block.querySelector("pre > code");
      if (!code) return;
      var n = countLines(code);
      var head = block.querySelector("span.filename");
      if (!head) {
        // A one-line command needs no header strip.
        if (n === 1) return;
        head = document.createElement("span");
        head.className = "filename gb-auto";
        head.setAttribute("aria-hidden", "true");
        head.textContent = "Listing";
        block.insertBefore(head, block.firstChild);
      }
      head.setAttribute("data-gb-lines", lineLabel(n, !!block.querySelector(".linenos")));
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
