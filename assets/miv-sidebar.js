/**
 * miv-sidebar.js — Sidebar dinâmica carregada do navigation.json
 * Incluir em qualquer dashboard: <script defer src="/shared-assets/miv-sidebar.js"></script>
 * 
 * Requer:
 *  - <nav class="miv-sidebar" id="miv-sidebar"></nav> no HTML (vazio ou com placeholder)
 *  - CSS do miv (miv.css ou shared-assets/layout.css)
 *  - Material Symbols Outlined font
 */
(function () {
  'use strict';

  var CONFIG_URL = 'https://funasa.dataiesb.com/config/navigation.json';
  var BASE_URL = 'https://funasa.dataiesb.com';

  // Detecta qual dash está ativo baseado no pathname
  function getActiveDashId() {
    var path = window.location.pathname.replace(/\/$/, '');
    var slug = path.split('/').filter(Boolean).pop() || '';
    return slug;
  }

  function renderSidebar(config) {
    var sidebar = document.querySelector('.miv-sidebar, #miv-sidebar');
    if (!sidebar) return;

    var activeDash = getActiveDashId();
    var html = '';

    config.sidebar.forEach(function (entry) {
      if (entry.section) {
        html += '<div class="miv-sidebar__divider"><span class="miv-sidebar__section">' + entry.section + '</span></div>';
      } else {
        var href = entry.href.startsWith('http') ? entry.href : BASE_URL + entry.href;
        var isActive = entry.id === activeDash;
        var activeClass = isActive ? ' miv-sidebar__item--active' : '';
        html += '<a href="' + href + '" class="miv-sidebar__item' + activeClass + '" title="' + entry.label + '">';
        html += '<span class="material-symbols-outlined">' + (entry.icon || 'link') + '</span>';
        html += '<span class="miv-sidebar__label">' + entry.label + '</span>';
        html += '</a>';
      }
    });

    sidebar.innerHTML = html;
  }

  function renderMobileBottomNav(config) {
    // Se não existe bottom nav no DOM, cria
    var bnav = document.querySelector('.miv-bnav');
    if (!bnav) {
      bnav = document.createElement('nav');
      bnav.className = 'miv-bnav';
      bnav.setAttribute('aria-label', 'Navegação mobile');
      document.body.appendChild(bnav);
    }

    var activeDash = getActiveDashId();
    var bottomItems = config.bottom_nav || [];
    if (bottomItems.length === 0) {
      // Fallback: usar home + primeiros 3 itens do sidebar
      bottomItems = [{ href: '/', icon: 'home', label: 'Início' }];
      var sidebarItems = config.sidebar.filter(function (e) { return !e.section; });
      bottomItems = bottomItems.concat(sidebarItems.slice(0, 3));
    }

    var html = '';
    bottomItems.forEach(function (item) {
      var href = item.href.startsWith('http') ? item.href : BASE_URL + item.href;
      var isActive = item.id === activeDash;
      var activeClass = isActive ? ' miv-bnav__item--active' : '';
      html += '<a href="' + href + '" class="miv-bnav__item' + activeClass + '">';
      html += '<span class="material-symbols-outlined">' + (item.icon || 'link') + '</span>';
      html += '<span class="miv-bnav__label">' + item.label + '</span>';
      html += '</a>';
    });

    bnav.innerHTML = html;
  }

  function renderMobileSidebar(config) {
    // Cria overlay + sidebar mobile se não existem
    var overlay = document.querySelector('.miv-mobile-sidebar-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'miv-mobile-sidebar-overlay';
      overlay.style.display = 'none';
      overlay.innerHTML = '<div class="miv-mobile-sidebar"></div>';
      document.body.appendChild(overlay);

      overlay.addEventListener('click', function (e) {
        if (e.target === overlay) {
          overlay.style.display = 'none';
        }
      });
    }

    var mobileSidebar = overlay.querySelector('.miv-mobile-sidebar');
    var activeDash = getActiveDashId();
    var html = '<button class="miv-mobile-sidebar__close" type="button" aria-label="Fechar menu">&times;</button>';

    config.sidebar.forEach(function (entry) {
      if (entry.section) {
        html += '<div class="miv-mobile-sidebar__divider">' + entry.section + '</div>';
      } else {
        var href = entry.href.startsWith('http') ? entry.href : BASE_URL + entry.href;
        var isActive = entry.id === activeDash;
        var activeClass = isActive ? ' miv-mobile-sidebar__item--active' : '';
        html += '<a href="' + href + '" class="miv-mobile-sidebar__item' + activeClass + '">';
        html += '<span class="material-symbols-outlined">' + (entry.icon || 'link') + '</span>';
        html += '<span>' + entry.label + '</span>';
        html += '</a>';
      }
    });

    mobileSidebar.innerHTML = html;

    // Close button
    var closeBtn = mobileSidebar.querySelector('.miv-mobile-sidebar__close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        overlay.style.display = 'none';
      });
    }
  }

  // Bind hamburger menu button
  function bindMobileToggle() {
    var toggleBtn = document.querySelector('.miv-header__menu-toggle, [data-miv-menu-toggle]');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function () {
        var overlay = document.querySelector('.miv-mobile-sidebar-overlay');
        if (overlay) {
          overlay.style.display = overlay.style.display === 'none' ? 'flex' : 'none';
        }
      });
    }
  }

  // Load config and render
  function init() {
    fetch(CONFIG_URL)
      .then(function (r) { return r.json(); })
      .then(function (config) {
        renderSidebar(config);
        renderMobileBottomNav(config);
        renderMobileSidebar(config);
        bindMobileToggle();
      })
      .catch(function (err) {
        console.warn('[miv-sidebar] Falha ao carregar navigation.json:', err);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
