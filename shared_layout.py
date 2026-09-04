# -*- coding: utf-8 -*-
"""
shared_layout.py — Componentes visuais MIV BigData FUNASA
Lê configuração de navegação de https://funasa.dataiesb.com/config/navigation.json
Importar em cada dash e usar wrap_layout() para aplicar o redesign.
"""
import json
import threading
import time
import urllib.request
from dash import html


# ═══ Configuração central ═══
CONFIG_URL = "https://funasa.dataiesb.com/config/navigation.json"
CONFIG_BASE = "https://funasa.dataiesb.com/config"
BASE = "https://funasa.dataiesb.com"

# Cache em memória (TTL 5 minutos)
_config_cache = None
_config_ts = 0
_CACHE_TTL = 300  # segundos
_config_lock = threading.Lock()


def _fetch_config():
    """Fetch silencioso — nunca levanta exceção."""
    global _config_cache, _config_ts
    try:
        req = urllib.request.Request(CONFIG_URL, headers={"User-Agent": "funasa-dash/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        with _config_lock:
            _config_cache = data
            _config_ts = time.time()
    except Exception:
        pass


def _load_config():
    """Retorna config do cache. Se expirado, renova em background."""
    global _config_cache, _config_ts
    if _config_cache and (time.time() - _config_ts) < _CACHE_TTL:
        return _config_cache
    if _config_cache:
        # Cache expirado — renovar em background sem bloquear
        threading.Thread(target=_fetch_config, daemon=True).start()
        return _config_cache
    # Primeira carga — usar fallback (preload já rodou em background)
    with _config_lock:
        if _config_cache:
            return _config_cache
        _config_cache = _FALLBACK_CONFIG
        _config_ts = time.time()
    return _config_cache


# Preload em background no startup (não bloqueia import)
threading.Thread(target=_fetch_config, daemon=True).start()


# Fallback offline — usado se o /config/ estiver indisponível na primeira carga
_FALLBACK_CONFIG = {
    "base_url": BASE,
    "header": {
        "logos": [
            {"src": "logos/bigdata-funasa.png", "alt": "BigData FUNASA", "height": "36px"},
        ],
        "logos_full": [
            {"src": "logos/bigdata-funasa.png", "alt": "BigData FUNASA", "height": "36px"},
            {"src": "logos/funasa-logo.png", "alt": "FUNASA", "height": "32px"},
            {"src": "logos/sus-logo.png", "alt": "SUS", "height": "28px"},
            {"src": "logos/ministerio-saude.png", "alt": "Ministério da Saúde", "height": "28px"},
            {"src": "logos/governo-federal.png", "alt": "Governo Federal", "height": "24px"},
        ],
    },
    "sidebar": [
        {"section": "INTELIGÊNCIA ARTIFICIAL"},
        {"href": "/chatbot", "icon": "smart_toy", "label": "IARA"},
        {"section": "INVESTIMENTOS FUNASA"},
        {"href": "/municipios/", "icon": "map", "label": "Investimentos Funasa nos Municípios"},
        {"section": "SANEAMENTO"},
        {"href": "/pmsb/", "icon": "description", "label": "Plano Municipal de Saneamento Básico (PMSB)"},
        {"href": "/base-sus/", "icon": "local_hospital", "label": "Base SUS"},
        {"href": "/doencas-agravos/", "icon": "coronavirus", "label": "Doenças e Agravos"},
        {"href": "/qualificacao/", "icon": "verified", "label": "Qualificação de Municípios"},
        {"section": "SAÚDE AMBIENTAL"},
        {"href": "/rio-doce/", "icon": "waves", "label": "Qualidade da Água da Bacia do Rio Doce"},
        {"href": "/salta-z/", "icon": "water_drop", "label": "Salta Z"},
        {"href": "/cisternas/", "icon": "opacity", "label": "Sistema de Captação e Armazenamento de Água de Chuva"},
        {"href": "/inep/", "icon": "school", "label": "Saúde Ambiental nas Escolas"},
        {"href": "/clusters-lisa/", "icon": "hub", "label": "Análise de Clusters LISA"},
        {"section": "GESTÃO DE CONVÊNIOS"},
        {"href": "/transfergov/", "icon": "payments", "label": "Análise do Transfere-Gov Funasa"},
        {"section": "ECONOMIA DOS MUNICÍPIOS"},
        {"href": "/pib/", "icon": "trending_up", "label": "PIB dos Municípios"},
    ],
    "bottom_nav": [
        {"href": "/", "icon": "home", "label": "Início"},
    ],
}


# ═══ CSS e fontes externas ═══
EXTERNAL_STYLESHEETS = [
    f"{CONFIG_BASE}/css/miv.css",
    f"{CONFIG_BASE}/css/tokens.css",
    f"{CONFIG_BASE}/css/components.css",
    f"{CONFIG_BASE}/css/layout.css",
    f"{CONFIG_BASE}/css/responsive.css",
    "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap",
]


def make_header():
    """Header padronizado — logos lidas do JSON centralizado."""
    config = _load_config()
    logos = config.get("header", {}).get("logos", [])
    logo_imgs = [
        html.Img(
            src=f"{CONFIG_BASE}/{logo['src']}",
            className="miv-header__logo",
            style={"height": logo.get("height", "32px")},
            alt=logo.get("alt", ""),
        )
        for logo in logos
    ]
    return html.Header(
        className="miv-header",
        children=[
            html.A(href=BASE + "/", className="miv-header__left", style={"textDecoration": "none"}, children=logo_imgs),
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "1rem"}, children=[
                html.Span("○ Ajuda", style={"fontSize": ".8rem", "color": "#667085"}),
            ]),
        ],
    )


def make_sidebar(active_path="/"):
    """Sidebar — itens e seções lidos do JSON centralizado."""
    config = _load_config()
    sidebar_items = config.get("sidebar", [])
    base = config.get("base_url", BASE)
    items = []
    for item in sidebar_items:
        if "section" in item:
            # Separador de seção
            items.append(
                html.Div(
                    html.Span(item["section"], className="miv-sidebar__section"),
                    className="miv-sidebar__divider",
                )
            )
        elif "href" in item:
            is_active = active_path.rstrip("/") == item["href"].rstrip("/")
            cls = "miv-sidebar__item miv-sidebar__item--active" if is_active else "miv-sidebar__item"
            items.append(
                html.A(
                    children=[
                        html.Span(item.get("icon", ""), className="material-symbols-outlined"),
                        html.Span(item.get("label", ""), className="miv-sidebar__label"),
                    ],
                    href=base + item["href"],
                    className=cls,
                    title=item.get("label", ""),
                )
            )
    return html.Nav(className="miv-sidebar", children=items)


def make_bottom_nav(active_path="/"):
    """Bottom nav mobile — itens lidos do JSON centralizado + menu lateral."""
    config = _load_config()
    nav_items = config.get("bottom_nav", [])
    base = config.get("base_url", BASE)
    items = []
    for item in nav_items:
        href = item.get("href", "/")
        if href == "#menu":
            # Link que abre o menu lateral mobile via :target
            items.append(
                html.A(
                    children=[
                        html.Span(item["icon"], className="material-symbols-outlined"),
                        html.Span(item["label"]),
                    ],
                    href="#miv-mobile-menu",
                    className="miv-bnav__item",
                    **{"aria-label": "Abrir menu"},
                )
            )
        else:
            is_active = active_path.rstrip("/") == href.rstrip("/")
            cls = "miv-bnav__item miv-bnav__item--active" if is_active else "miv-bnav__item"
            items.append(
                html.A(
                    children=[
                        html.Span(item["icon"], className="material-symbols-outlined"),
                        html.Span(item["label"]),
                    ],
                    href=base + href,
                    className=cls,
                )
            )
    return html.Nav(className="miv-bnav", children=items)


def make_mobile_sidebar(active_path="/"):
    """Sidebar mobile — overlay com todos os itens do menu (target-based CSS toggle)."""
    config = _load_config()
    sidebar_items = config.get("sidebar", [])
    logos = config.get("header", {}).get("logos", [])
    base = config.get("base_url", BASE)

    # Logo no topo
    logo_imgs = [
        html.Img(
            src=f"{CONFIG_BASE}/{logo['src']}",
            style={"height": logo.get("height", "32px"), "width": "auto", "objectFit": "contain"},
            alt=logo.get("alt", ""),
        )
        for logo in logos
    ]

    # Itens do menu
    nav_items = []
    for item in sidebar_items:
        if "section" in item:
            nav_items.append(
                html.Div(
                    html.Span(item["section"], className="miv-mobile-sidebar__section"),
                    className="miv-mobile-sidebar__divider",
                )
            )
        else:
            is_active = active_path.rstrip("/") == item["href"].rstrip("/")
            cls = "miv-mobile-sidebar__item miv-mobile-sidebar__item--active" if is_active else "miv-mobile-sidebar__item"
            nav_items.append(
                html.A(
                    children=[
                        html.Span(item["icon"], className="material-symbols-outlined"),
                        html.Span(item["label"]),
                    ],
                    href=base + item["href"],
                    className=cls,
                )
            )

    # :target CSS approach — the overlay div has id="miv-mobile-menu"
    # Bottom nav links to "#miv-mobile-menu", close links to "#"
    return html.Div(id="miv-mobile-menu", className="miv-mobile-sidebar-overlay", children=[
        html.A(href="#", className="miv-mobile-sidebar-backdrop", **{"aria-label": "Fechar menu"}),
        html.Aside(className="miv-mobile-sidebar-panel", children=[
            html.Div(className="miv-mobile-sidebar__header", children=[
                html.Div(children=logo_imgs, className="miv-mobile-sidebar__logos"),
                html.A(
                    html.Span("close", className="material-symbols-outlined"),
                    className="miv-mobile-sidebar__close",
                    href="#",
                    **{"aria-label": "Fechar menu"},
                ),
            ]),
            html.Nav(className="miv-mobile-sidebar__nav", children=nav_items),
        ]),
    ])


def wrap_layout(content, active_path="/"):
    """
    Envolve o conteúdo de um dash com a estrutura MIV completa:
    header + sidebar + content + bottom-nav.

    Uso:
        from shared_layout import wrap_layout
        app.layout = wrap_layout(meu_layout_original, active_path="/base-sus/")
    """
    return html.Div(className="miv-shell", children=[
        make_header(),
        html.Div(className="miv-body", children=[
            make_sidebar(active_path),
            html.Main(className="miv-main", children=[content]),
        ]),
        make_bottom_nav(active_path),
    ])


def miv_style_tag():
    """Placeholder — CSS vem via external_stylesheets ou assets/miv.css."""
    return html.Div(style={"display": "none"})
