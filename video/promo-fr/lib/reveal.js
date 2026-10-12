// Staggered blur-to-sharp word reveal shared by every beat. Splitting happens once at load, so seeks stay pure.
(function () {
  function splitWords(el) {
    if (el.dataset.split) return el.querySelectorAll(".w");
    el.dataset.split = "1";
    const words = el.textContent.trim().split(/\s+/);
    el.textContent = "";
    words.forEach((word, i) => {
      const span = document.createElement("span");
      span.className = "w";
      span.style.display = "inline-block";
      span.textContent = word;
      el.appendChild(span);
      if (i < words.length - 1) el.appendChild(document.createTextNode(" "));
    });
    return el.querySelectorAll(".w");
  }

  function revealWords(tl, el, at, options) {
    const o = Object.assign({ stagger: .07, duration: .7, y: 22, blur: 14 }, options);
    tl.fromTo(splitWords(el), { opacity: 0, y: o.y, filter: `blur(${o.blur}px)` },
      { opacity: 1, y: 0, filter: "blur(0px)", duration: o.duration, stagger: o.stagger, ease: "power3.out" }, at);
  }

  // Hides every word already split inside el (a line or a whole block of lines).
  function hideWords(tl, el, at, options) {
    const o = Object.assign({ duration: .35, y: -14 }, options);
    const words = el.querySelectorAll(".w").length ? el.querySelectorAll(".w") : splitWords(el);
    tl.to(words, { opacity: 0, y: o.y, filter: "blur(10px)", duration: o.duration, stagger: .02, ease: "power2.in" }, at);
  }

  window.revealWords = revealWords;
  window.hideWords = hideWords;
})();
