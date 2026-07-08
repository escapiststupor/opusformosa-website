(function () {
  var isEn = false;
  var base = "";
  var currentId = "index";

  var items = [
    { id: "index", page: "", labelZh: "首頁", labelEn: "Home" },
    {
      id: "events",
      page: "events",
      labelZh: "活動時間軸",
      labelEn: "Events",
    },
    { id: "team", page: "team", labelZh: "團隊介紹", labelEn: "Team" },
    { id: "bilbao", page: "bilbao", labelZh: "畢爾包", labelEn: "Bilbao" },
    { id: "festival2026", page: "festival2026", labelZh: "Edition 2026", labelEn: "Edition 2026" },
    { id: "artists", page: "artists", labelZh: "藝術家", labelEn: "Artists" },
    { id: "partners", page: "partners", labelZh: "贊助夥伴", labelEn: "Partners" },
    { id: "friends", page: "friends", labelZh: "支持我們", labelEn: "Support Us" },
  ];

  /** Pages that exist in both zh and en; language switch goes to same page. Others go to index. */
  var pagesWithBothLangs = [
    "",
    "events",
    "team",
    "bilbao",
    "donors",
    "festival2026",
    "2026-friends",
    "artists",
    "friends",
    "partners",
  ];

  function getCurrentPathWithoutLang() {
    var path =
      typeof window !== "undefined" && window.location
        ? window.location.pathname
        : "";
    path = decodeURIComponent(path || "");
    path = path.replace(/\\/g, "/");
    path = path.replace(/^\/+/, "").replace(/\/+$/, "");
    if (path === "en") {
      path = "";
    } else if (path.indexOf("en/") === 0) {
      path = path.slice(3);
    }
    if (path.indexOf("/") !== -1) {
      path = path.split("/").pop();
    }
    path = path.replace(/\.html$/, "");
    return path === "index" ? "" : path;
  }

  function getCurrentId() {
    var path = getCurrentPathWithoutLang();
    if (!path) return "index";
    if (path === "events") return "events";
    if (path === "team") return "team";
    if (path === "bilbao") return "bilbao";
    if (path === "festival2026") return "festival2026";
    if (path === "2026-friends") return "2026-friends";
    if (path === "artists") return "artists";
    if (path === "partners") return "partners";
    if (path === "friends") return "friends";
    return "index";
  }

  function getCurrentPageFile() {
    return getCurrentPathWithoutLang();
  }

  function getLang(el) {
    var lang = (el && el.getAttribute("lang")) || "";
    if (lang === "en" || lang === "zh") return lang;
    if (typeof document !== "undefined" && document.documentElement) {
      var docLang = (
        document.documentElement.getAttribute("lang") || ""
      ).toLowerCase();
      if (docLang.startsWith("en")) return "en";
    }
    return "zh";
  }

  function pageHref(page, lang) {
    page = page || "";
    if (lang === "en") return page ? "/en/" + page : "/en/";
    return page ? "/" + page : "/";
  }

  function renderFestivalSupportLink() {
    if (currentId !== "friends" && currentId !== "festival2026") return "";

    var href = pageHref("2026-friends", isEn ? "en" : "zh");
    var eyebrow = isEn ? "2026 Festival" : "2026 音樂節";
    var title = isEn
      ? "Support the 2026 Opus Festival"
      : "支持 2026 Opus 音樂節";
    var detail = isEn
      ? "Reserve VIP seats not released for public sale on OPENTIX."
      : "預訂 OPENTIX 未公開販售之 VIP 保留席。";
    var cta = isEn ? "View Friends of Opus Formosa" : "查看 Friends of Opus Formosa";

    return (
      '<style>' +
      "nav-bar .festival-support-strip{display:block;background:#0d0b09;padding:72px 24px 0;}" +
      "nav-bar .festival-support-strip__link{box-sizing:border-box;display:flex;align-items:center;justify-content:space-between;gap:18px;max-width:1152px;margin:0 auto;padding:13px 18px;border-top:1px solid rgba(200,152,64,.22);border-bottom:1px solid rgba(200,152,64,.22);color:#f0e8d8;text-decoration:none;background:rgba(200,152,64,.045);transition:background-color .25s ease,border-color .25s ease,color .25s ease;}" +
      "nav-bar .festival-support-strip__link:hover,nav-bar .festival-support-strip__link:focus-visible{background:rgba(200,152,64,.09);border-color:rgba(200,152,64,.45);outline:none;}" +
      "nav-bar .festival-support-strip__eyebrow{flex:0 0 auto;font-family:'Crimson Pro',Georgia,serif;font-size:.68rem;letter-spacing:.18em;text-transform:uppercase;color:rgba(200,152,64,.75);}" +
      "nav-bar .festival-support-strip__copy{display:flex;align-items:baseline;gap:10px;min-width:0;}" +
      "nav-bar .festival-support-strip__title{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.06rem;font-weight:600;color:#f0e8d8;white-space:nowrap;}" +
      "nav-bar .festival-support-strip__detail{font-family:'Crimson Pro',Georgia,serif;font-size:.92rem;color:rgba(240,232,216,.66);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}" +
      "nav-bar .festival-support-strip__cta{flex:0 0 auto;font-family:'Crimson Pro',Georgia,serif;font-size:.82rem;color:#c89840;white-space:nowrap;}" +
      "@media (max-width:760px){nav-bar .festival-support-strip{padding:70px 18px 0;}nav-bar .festival-support-strip__link{align-items:flex-start;flex-direction:column;gap:7px;padding:12px 14px;}nav-bar .festival-support-strip__copy{display:block;}nav-bar .festival-support-strip__title,nav-bar .festival-support-strip__detail{display:block;white-space:normal;}nav-bar .festival-support-strip__detail{margin-top:2px;}nav-bar .festival-support-strip__cta{font-size:.86rem;}}" +
      "</style>" +
      '<div class="festival-support-strip">' +
      '<a class="festival-support-strip__link" href="' + href + '">' +
      '<span class="festival-support-strip__eyebrow">' + eyebrow + "</span>" +
      '<span class="festival-support-strip__copy">' +
      '<span class="festival-support-strip__title">' + title + "</span>" +
      '<span class="festival-support-strip__detail">' + detail + "</span>" +
      "</span>" +
      '<span class="festival-support-strip__cta">' + cta + " →</span>" +
      "</a>" +
      "</div>"
    );
  }

  var fbSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>';
  var igSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/></svg>';
  var ytSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>';

  function render(lang) {
    isEn = lang === "en";
    base = isEn ? "../" : "";
    currentId = getCurrentId();

    var menuLabel = isEn ? "Open menu" : "開啟選單";
    var linkClass =
      "p-3 lg:py-0 hover:text-classical-gold transition-colors border-b border-white/5 lg:border-0";
    var activeClass =
      "p-3 lg:py-0 text-classical-gold border-b border-classical-gold lg:border-0";
    /* Same-language nav links (no lang switcher) */
    var linksHtml = items
      .map(function (item) {
        var isActive = item.id === currentId;
        var cls = isActive ? activeClass : linkClass;
        var href = pageHref(item.page, isEn ? "en" : "zh");
        var label = isEn ? item.labelEn : item.labelZh;
        return '<a href="' + href + '" class="' + cls + '">' + label + "</a>";
      })
      .join("\n          ");

    var currentPage = getCurrentPageFile();
    var hasCounterpart = pagesWithBothLangs.indexOf(currentPage) !== -1;
    var langHref;
    if (isEn) {
      langHref = pageHref(hasCounterpart ? currentPage : "", "zh");
    } else {
      langHref = pageHref(hasCounterpart ? currentPage : "", "en");
    }
    var langLabel = isEn ? "中文" : "EN";
    var targetLang = isEn ? "zh" : "en";
    var langOnClick = 'onclick="try{sessionStorage.setItem(\'opus-lang-pref\',\'' + targetLang + '\');localStorage.setItem(\'opus-lang-pref\',\'' + targetLang + '\');}catch(e){}"';

    var logoHref = pageHref("", isEn ? "en" : "zh");
    var logoSrc = base + "opus_formosa_logo_white.png";

    return (
      '<nav class="bg-classical-dark text-white py-4 px-6 shadow-lg fixed top-0 left-0 right-0 z-50">' +
      '<div class="max-w-6xl mx-auto flex justify-between items-center flex-wrap lg:flex-nowrap">' +
      /* Logo + lang switcher always visible next to logo */
      '<div class="flex items-center gap-3">' +
      '<a href="' + logoHref + '" class="flex items-center space-x-3 hover:opacity-80 transition-opacity">' +
      '<img src="' + logoSrc + '" alt="Opus Formosa Logo" class="h-8" />' +
      '</a>' +
      '<a href="' + langHref + '" class="text-stone-400 hover:text-white transition-colors text-sm" ' + langOnClick + '>' + langLabel + '</a>' +
      '</div>' +
      '<button type="button" id="nav-toggle" class="lg:hidden p-2 -mr-2 text-white hover:text-classical-gold rounded-lg focus:outline-none focus:ring-2 focus:ring-classical-gold focus:ring-offset-2 focus:ring-offset-classical-dark" aria-expanded="false" aria-label="' +
      menuLabel +
      '">' +
      '<span id="nav-icon-open"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg></span>' +
      '<span id="nav-icon-close" class="hidden"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg></span>' +
      '</button>' +
      '<div id="nav-menu" class="hidden lg:flex flex flex-col lg:flex-row w-full lg:w-auto lg:items-center lg:space-x-5 absolute lg:relative top-full left-0 right-0 lg:top-auto lg:left-auto bg-classical-dark lg:bg-transparent py-4 lg:py-0 px-6 lg:px-0 -mx-6 lg:mx-0 mt-2 lg:mt-0 shadow-lg lg:shadow-none z-50 border-t border-white/10 lg:border-0">' +
      linksHtml +
      '</div>' +
      '</div>' +
      '</nav>' +
      renderFestivalSupportLink()
    );
  }

  function NavBarElement() {
    return Reflect.construct(HTMLElement, [], NavBarElement);
  }
  NavBarElement.prototype = Object.create(HTMLElement.prototype);
  NavBarElement.prototype.connectedCallback = function () {
    var lang = getLang(this);
    this.innerHTML = render(lang);
  };
  Object.setPrototypeOf(NavBarElement, HTMLElement);
  customElements.define("nav-bar", NavBarElement);
})();
