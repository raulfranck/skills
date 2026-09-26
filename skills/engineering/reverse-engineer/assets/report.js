(function () {
  // Tooltips for glossary terms: one floating element, kept inside the viewport.
  var tip = document.createElement("div");
  tip.id = "tooltip";
  tip.setAttribute("role", "tooltip");
  document.body.appendChild(tip);
  function show(el) {
    tip.innerHTML = "<b></b><span></span>";
    tip.firstChild.textContent = el.getAttribute("data-term");
    tip.lastChild.textContent = el.getAttribute("data-def");
    tip.classList.add("show");
    var r = el.getBoundingClientRect(), t = tip.getBoundingClientRect();
    var left = Math.min(Math.max(8, r.left + r.width / 2 - t.width / 2), window.innerWidth - t.width - 8);
    var top = r.top - t.height - 8;
    if (top < 8) top = r.bottom + 8;
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  }
  function hide() { tip.classList.remove("show"); }
  document.querySelectorAll(".term").forEach(function (el) {
    el.addEventListener("mouseenter", function () { show(el); });
    el.addEventListener("focus", function () { show(el); });
    el.addEventListener("mouseleave", hide);
    el.addEventListener("blur", hide);
  });
  window.addEventListener("scroll", hide, { passive: true });

  // Highlight the section being read in the table of contents.
  var links = {};
  document.querySelectorAll(".toc a").forEach(function (a) { links[a.getAttribute("href").slice(1)] = a; });
  if ("IntersectionObserver" in window) {
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting && links[e.target.id]) {
          Object.keys(links).forEach(function (k) { links[k].classList.remove("active"); });
          links[e.target.id].classList.add("active");
        }
      });
    }, { rootMargin: "0px 0px -75% 0px" });
    document.querySelectorAll("main h2[id], main h3[id]").forEach(function (h) { obs.observe(h); });
  }

  // Opening an evidence link inside a closed appendix group opens the group.
  function openTarget() {
    var id = decodeURIComponent(location.hash.slice(1));
    var el = id && document.getElementById(id);
    if (el) { var d = el.closest("details"); if (d) d.open = true; }
  }
  window.addEventListener("hashchange", openTarget);
  openTarget();

  // Diagrams: Mermaid from a CDN; without network the source text stays visible.
  if (document.querySelector("pre.mermaid")) {
    var s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js";
    s.onload = function () {
      var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      window.mermaid.initialize({ startOnLoad: false, theme: dark ? "dark" : "neutral", securityLevel: "strict" });
      window.mermaid.run({ querySelector: "pre.mermaid" });
    };
    document.head.appendChild(s);
  }
})();
