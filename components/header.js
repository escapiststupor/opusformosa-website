class OpusHeader extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  static get observedAttributes() {
    return ['language', 'current-page'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue !== newValue) {
      this.render();
    }
  }

  connectedCallback() {
    this.render();
  }

  render() {
    const language = this.getAttribute('language') || 'zh';
    const currentPage = this.getAttribute('current-page') || 'home';

    const isEnglish = language === 'en';
    const logoPath = isEnglish
      ? "../opus_formosa_logo_white.png"
      : "opus_formosa_logo_white.png";
    const homeHref = isEnglish ? 'index.html' : '../index.html';
    const eventsHref = isEnglish ? 'events.html' : '../events.html';
    const bilbaoHref = isEnglish ? 'bilbao.html' : '../bilbao.html';

    const content = `
      <style>
        nav {
          background-color: #1c1917;
          color: white;
          padding: 1rem 1.5rem;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .nav-container {
          max-width: 72rem;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .logo-link {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          transition: opacity 0.2s;
        }
        .logo-link:hover {
          opacity: 0.8;
        }
        .logo-img {
          height: 2rem;
        }
        .brand-name {
          font-family: 'Playfair Display', serif;
          font-weight: bold;
        }
        .nav-menu {
          display: flex;
          align-items: center;
          gap: 1.5rem;
        }
        .nav-link {
          transition: color 0.2s;
        }
        .nav-link:hover {
          color: #b45309;
        }
        .nav-link.active {
          color: #b45309;
          border-bottom: 1px solid #b45309;
        }
        .dropdown {
          position: relative;
        }
        .dropdown-button {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          transition: color 0.2s;
        }
        .dropdown-button:hover {
          color: #b45309;
        }
        .dropdown-menu {
          position: absolute;
          right: 0;
          top: 100%;
          margin-top: 0.5rem;
          width: 12rem;
          background: white;
          border-radius: 0.375rem;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
          opacity: 0;
          visibility: hidden;
          transition: all 0.2s;
        }
        .dropdown:hover .dropdown-menu {
          opacity: 1;
          visibility: visible;
        }
        .dropdown-link {
          display: block;
          padding: 0.5rem 1rem;
          font-size: 0.875rem;
          color: #1c1917;
          transition: all 0.2s;
        }
        .dropdown-link:hover {
          background-color: #b45309;
          color: white;
        }
        .dropdown-link:first-child {
          border-radius: 0.375rem 0.375rem 0 0;
        }
        .dropdown-link:last-child {
          border-radius: 0 0 0.375rem 0.375rem;
        }
        .lang-switch {
          color: #a8a29e;
          transition: color 0.2s;
          font-size: 0.875rem;
        }
        .lang-switch:hover {
          color: white;
        }
        .dropdown-arrow {
          width: 1rem;
          height: 1rem;
          transition: transform 0.2s;
        }
        .dropdown:hover .dropdown-arrow {
          transform: rotate(180deg);
        }
        .nav-menu.open {
          display: flex;
          max-height: 20rem;
          opacity: 1;
        }
        .hamburger {
          display: none;
          padding: 0.5rem;
          background: none;
          border: none;
          color: white;
          cursor: pointer;
          border-radius: 0.375rem;
        }
        .hamburger:hover {
          color: #b45309;
        }
        .hamburger svg {
          width: 1.5rem;
          height: 1.5rem;
        }
        .hamburger-close {
          display: none;
        }
        .nav-menu.open ~ .hamburger .hamburger-open {
          display: none;
        }
        .nav-menu.open ~ .hamburger .hamburger-close {
          display: block;
        }
        @media (max-width: 768px) {
          .nav-container {
            flex-wrap: wrap;
          }
          .hamburger {
            display: block;
          }
          .nav-menu {
            display: none;
            flex-direction: column;
            width: 100%;
            order: 3;
            gap: 0;
            padding: 1rem 0 0;
            margin-top: 0.5rem;
            border-top: 1px solid rgba(255,255,255,0.1);
            max-height: 0;
            overflow: hidden;
            opacity: 0;
            transition: max-height 0.3s ease, opacity 0.2s;
          }
          .nav-menu a {
            display: block;
            padding: 0.75rem 0;
            font-size: 1rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
          }
          .nav-menu a:last-child {
            border-bottom: none;
          }
        }
      </style>

      <nav>
        <div class="nav-container">
          <a href="${homeHref}" class="logo-link">
            <img src="${logoPath}" alt="Opus Formosa Logo" class="logo-img">
            <span class="brand-name">Opus Formosa</span>
          </a>

          <div class="nav-menu" id="nav-menu" role="menu">
            <a href="${homeHref}" class="nav-link ${currentPage === 'home' ? 'active' : ''}">
              ${isEnglish ? 'Home' : '首頁'}
            </a>
            <a href="${eventsHref}" class="nav-link ${currentPage === 'events' ? 'active' : ''}">
              ${isEnglish ? 'Events' : '活動時間軸'}
            </a>
            <a href="${bilbaoHref}" class="nav-link ${currentPage === 'bilbao' ? 'active' : ''}">
              ${isEnglish ? 'Bilbao' : '畢爾包'}
            </a>

            <!-- Support dropdown (commented out for now) -->
            <!--
            <div class="dropdown">
              <button class="dropdown-button nav-link">
                <span>${isEnglish ? 'Support Us' : '支持我們'}</span>
                <svg class="dropdown-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              <div class="dropdown-menu">
                <a href="mailto:info@opusformosa.org" class="dropdown-link">
                  ${isEnglish ? 'Donate Now' : '立即捐款'}
                </a>
                <a href="${isEnglish ? 'donors.html' : '../donors.html'}" class="dropdown-link">
                  ${isEnglish ? 'Our Donors' : '我們的捐助者'}
                </a>
                <a href="${isEnglish ? 'partners.html' : '../partners.html'}" class="dropdown-link">
                  ${isEnglish ? 'Sponsors & Partners' : '贊助夥伴'}
                </a>
              </div>
            </div>
            -->

            <a href="${isEnglish ? '../index.html' : 'en/index.html'}" class="nav-link lang-switch">
              ${isEnglish ? '中文' : 'EN'}
            </a>
          </div>
          <button type="button" class="hamburger" id="nav-toggle" aria-label="${isEnglish ? 'Open menu' : '開啟選單'}" aria-expanded="false">
            <span class="hamburger-open"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg></span>
            <span class="hamburger-close"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg></span>
          </button>
        </div>
      </nav>
    `;

    this.shadowRoot.innerHTML = content;
    const toggle = this.shadowRoot.getElementById('nav-toggle');
    const menu = this.shadowRoot.getElementById('nav-menu');
    if (toggle && menu) {
      toggle.addEventListener('click', () => {
        menu.classList.toggle('open');
        toggle.setAttribute('aria-expanded', menu.classList.contains('open'));
      });
    }
  }
}

customElements.define('opus-header', OpusHeader);