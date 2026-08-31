# -*- coding: utf-8 -*-
"""
dash_educacao_superior.py
Dashboard — Censo da Educação Superior (INEP 2024)
Fonte: public.inep_educacao_superior_cursos  e  public.inep_educacao_superior_ies
"""

import os
import math
import json

import dash
from dash import Input, Output, dcc, html
import pandas as pd
import plotly.graph_objects as go
import psycopg2
import requests
from sqlalchemy import create_engine

# ── Shared layout MIV BigData FUNASA ─────────────────────────────────────────
try:
    from shared_layout import wrap_layout, miv_style_tag
    from loading_components import funasa_page_loading
    _HAS_MIV = True
except ImportError:
    _HAS_MIV = False

# ── Conexão PostgreSQL ────────────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "5432")
DB_NAME     = os.getenv("DB_NAME",     "iesb")
DB_USER     = os.getenv("DB_USER",     "iesb")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

def _get_engine():
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url)

print("[EDUC] Carregando tabela de cursos...", flush=True)
engine = _get_engine()

COLS_CURSOS = [
    "nu_ano_censo", "no_regiao", "co_regiao", "no_uf", "sg_uf", "co_uf",
    "no_municipio", "co_municipio", "in_capital",
    "tp_organizacao_academica", "tp_rede", "tp_categoria_administrativa",
    "co_ies", "no_curso", "co_curso",
    "no_cine_area_geral", "no_cine_area_especifica",
    "tp_grau_academico", "tp_modalidade_ensino", "tp_nivel_academico",
    "qt_curso", "qt_vg_total", "qt_inscrito_total",
    "qt_ing", "qt_ing_fem", "qt_ing_masc",
    "qt_mat", "qt_mat_fem", "qt_mat_masc",
    "qt_conc", "qt_conc_fem", "qt_conc_masc",
    "qt_ing_enem", "qt_ing_financ",
    "qt_mat_prounii", "qt_mat_prounip", "qt_mat_fies",
    "qt_aluno_deficiente", "qt_mat_deficiente",
]

COLS_IES = [
    "nu_ano_censo", "no_regiao_ies", "co_regiao_ies", "no_uf_ies", "sg_uf_ies",
    "co_municipio_ies", "no_municipio_ies", "in_capital_ies",
    "tp_organizacao_academica", "tp_rede", "tp_categoria_administrativa",
    "co_ies", "no_ies", "sg_ies",
    "qt_doc_total", "qt_doc_exe",
    "qt_doc_ex_dout", "qt_doc_ex_mest",
    "qt_doc_ex_femi", "qt_doc_ex_masc",
    "qt_tec_total",
]

with engine.connect() as con:
    df_cursos = pd.read_sql(
        f"SELECT {', '.join(COLS_CURSOS)} FROM public.inep_educacao_superior_cursos;",
        con,
    )
    df_ies = pd.read_sql(
        f"SELECT {', '.join(COLS_IES)} FROM public.inep_educacao_superior_ies;",
        con,
    )

print(f"[EDUC] Cursos: {len(df_cursos)} linhas | IES: {len(df_ies)} linhas", flush=True)

# ── GeoJSON dos estados brasileiros ──────────────────────────────────────────
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
_ESTADOS_GEOJSON_CACHE = os.path.join(_CACHE_DIR, "brazil_states.geojson")
_ESTADOS_GEOJSON_URL = (
    "https://raw.githubusercontent.com/codeforamerica/"
    "click_that_hood/master/public/data/brazil-states.geojson"
)

try:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    if os.path.exists(_ESTADOS_GEOJSON_CACHE):
        with open(_ESTADOS_GEOJSON_CACHE, encoding="utf-8") as _f:
            geojson_estados = json.load(_f)
    else:
        print("[EDUC] Baixando GeoJSON dos estados...", flush=True)
        _resp = requests.get(_ESTADOS_GEOJSON_URL, timeout=30)
        _resp.raise_for_status()
        geojson_estados = _resp.json()
        with open(_ESTADOS_GEOJSON_CACHE, "w", encoding="utf-8") as _f:
            json.dump(geojson_estados, _f)
    print(f"[EDUC] GeoJSON carregado: {len(geojson_estados['features'])} estados", flush=True)
except Exception as _e:
    print(f"[EDUC] AVISO: falha ao carregar GeoJSON — {_e}", flush=True)
    geojson_estados = {"type": "FeatureCollection", "features": []}

# Mapeia sigla → nome no GeoJSON (campo "sigla")
_sigla_to_geojson = {
    f["properties"]["sigla"]: f["properties"]["sigla"]
    for f in geojson_estados.get("features", [])
    if "sigla" in f.get("properties", {})
}

# ── Limpeza / tratamento ──────────────────────────────────────────────────────
for col in ["qt_curso","qt_vg_total","qt_inscrito_total",
            "qt_ing","qt_ing_fem","qt_ing_masc",
            "qt_mat","qt_mat_fem","qt_mat_masc",
            "qt_conc","qt_conc_fem","qt_conc_masc",
            "qt_ing_enem","qt_ing_financ",
            "qt_mat_prounii","qt_mat_prounip","qt_mat_fies",
            "qt_aluno_deficiente","qt_mat_deficiente"]:
    df_cursos[col] = pd.to_numeric(df_cursos[col], errors="coerce").fillna(0)

for col in ["qt_doc_total","qt_doc_exe","qt_doc_ex_dout","qt_doc_ex_mest",
            "qt_doc_ex_femi","qt_doc_ex_masc","qt_tec_total"]:
    df_ies[col] = pd.to_numeric(df_ies[col], errors="coerce").fillna(0)

# Filtrar linha "Cursos a distância" no campo regiao/uf (artefato da tabela)
df_cursos = df_cursos[~df_cursos["no_regiao"].isin(["Cursos a distância"])]
df_cursos = df_cursos[~df_cursos["sg_uf"].isin(["Cursos a distância"])]

# ── Listas para filtros ────────────────────────────────────────────────────────
REGIOES       = ["Todas"] + sorted(df_cursos["no_regiao"].dropna().unique().tolist())
UFS           = ["Todas"] + sorted(df_cursos["sg_uf"].dropna().unique().tolist())
MODALIDADES   = ["Todas"] + sorted(df_cursos["tp_modalidade_ensino"].dropna().unique().tolist())
GRAUS         = ["Todos"] + sorted(df_cursos["tp_grau_academico"].dropna().unique().tolist())
REDES         = ["Todas"] + sorted(df_cursos["tp_rede"].dropna().unique().tolist())
ORG_ACAD      = ["Todas"] + sorted(df_ies["tp_organizacao_academica"].dropna().unique().tolist())
AREAS_GERAL   = ["Todas"] + sorted(df_cursos["no_cine_area_geral"].dropna().unique().tolist())

# ── Cores ─────────────────────────────────────────────────────────────────────
COR_HEADER  = "#1B3A5C"
COR_FUNDO   = "#F0F2F5"
COR_AZUL    = "#1565C0"
COR_VERDE   = "#2F855A"
COR_ROXO    = "#6B46C1"
COR_LARANJA = "#C05621"
COR_CINZA   = "#4A5568"

COR_REGIOES = {
    "Norte":        "#1D9E75",
    "Nordeste":     "#EF9F27",
    "Centro-Oeste": "#378ADD",
    "Sul":          "#7F77DD",
    "Sudeste":      "#D85A30",
}

# ── Helpers visuais ────────────────────────────────────────────────────────────
def _layout_base():
    return dict(
        margin=dict(l=40, r=20, t=10, b=40),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", size=12, color="#333"),
        xaxis=dict(showgrid=False, linecolor="#e0e0e0"),
        yaxis=dict(gridcolor="#f0f0f0", linecolor="#e0e0e0"),
        hoverlabel=dict(bgcolor="#fff", bordercolor="#ccc", font_size=12, font_color="#000"),
    )


def _kpi(valor, label, cor):
    return html.Div(
        [
            html.P(valor, style={"fontSize": 26, "fontWeight": 700, "color": "#fff",
                                  "margin": "0 0 4px 0"}),
            html.P(label, style={"fontSize": 10, "fontWeight": 600, "color": "#fff",
                                  "margin": 0, "textTransform": "uppercase",
                                  "letterSpacing": "0.05em"}),
        ],
        style={"backgroundColor": cor, "borderRadius": 8,
               "padding": "16px 20px", "flex": 1, "minWidth": 140},
    )


def _card(children, shadow=False):
    style = {
        "backgroundColor": "#ffffff",
        "borderRadius": 8,
        "padding": "20px 24px",
        "border": "1px solid #e2e8f0",
        "flex": 1,
    }
    if shadow:
        style["boxShadow"] = "0 2px 8px rgba(0,0,0,0.12)"
        style["border"] = "none"
    return html.Div(children, style=style)


def _titulo(texto):
    return html.P(texto, style={"fontSize": 13, "fontWeight": 600,
                                  "color": "#2d3748", "margin": "0 0 8px 0"})


def _nota(texto, cor="#718096"):
    return html.P(
        texto,
        style={"fontSize": 11, "color": cor, "margin": "6px 0 0 0",
               "fontStyle": "italic", "lineHeight": "1.4"},
    )


def _fmt_mil(val):
    """Formata número: mil / M / B."""
    v = float(val)
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f} bi"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f} M"
    if v >= 1_000:
        return f"{v/1_000:.0f} mil"
    return f"{v:,.0f}".replace(",", ".")


def _filtro_label(label, dropdown_id, options, value, width=180):
    return html.Div([
        html.Label(label, style={"fontSize": 11, "fontWeight": 600, "color": "#4a5568",
                                  "marginBottom": 4, "display": "block"}),
        dcc.Dropdown(
            id=dropdown_id,
            options=[{"label": o, "value": o} for o in options],
            value=value,
            clearable=False,
            style={"width": width, "fontSize": 13, "fontFamily": "Inter, sans-serif"},
        ),
    ])


# ── Tabela HTML genérica ───────────────────────────────────────────────────────
def _tabela_html(df_tab, cor_col=None, cor_fn=None, max_rows=50):
    """Gera html.Table a partir de um DataFrame."""
    colunas = df_tab.columns.tolist()
    header = html.Tr([
        html.Th(col, style={
            "padding": "10px 14px", "textAlign": "left", "fontSize": 11,
            "fontWeight": 600, "color": "#4a5568",
            "borderBottom": "2px solid #e2e8f0",
            "textTransform": "uppercase", "letterSpacing": "0.03em",
            "whiteSpace": "nowrap",
        })
        for col in colunas
    ])

    rows = []
    for i, (_, row) in enumerate(df_tab.head(max_rows).iterrows()):
        cells = []
        bg = "#fafafa" if i % 2 == 0 else "#ffffff"
        for col in colunas:
            val = row[col]
            style = {"padding": "8px 14px", "fontSize": 12,
                     "borderBottom": "1px solid #f0f0f0", "backgroundColor": bg}
            if cor_col and col == cor_col and cor_fn:
                style["color"] = cor_fn(val)
                style["fontWeight"] = 600
            cells.append(html.Td(val, style=style))
        rows.append(html.Tr(cells))

    return html.Table(
        [html.Thead(header), html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse"},
    )


# ── Filtro helper ──────────────────────────────────────────────────────────────
def _aplicar_filtros_cursos(regiao, uf, modalidade, grau, rede):
    df = df_cursos.copy()
    if regiao and regiao != "Todas":
        df = df[df["no_regiao"] == regiao]
    if uf and uf != "Todas":
        df = df[df["sg_uf"] == uf]
    if modalidade and modalidade != "Todas":
        df = df[df["tp_modalidade_ensino"] == modalidade]
    if grau and grau != "Todos":
        df = df[df["tp_grau_academico"] == grau]
    if rede and rede != "Todas":
        df = df[df["tp_rede"] == rede]
    return df


def _aplicar_filtros_ies(regiao, uf, org, rede):
    df = df_ies.copy()
    if regiao and regiao != "Todas":
        df = df[df["no_regiao_ies"] == regiao]
    if uf and uf != "Todas":
        df = df[df["sg_uf_ies"] == uf]
    if org and org != "Todas":
        df = df[df["tp_organizacao_academica"] == org]
    if rede and rede != "Todas":
        df = df[df["tp_rede"] == rede]
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# ABA 1 — PANORAMA GERAL
# ═══════════════════════════════════════════════════════════════════════════════
def _aba_panorama():
    df = df_cursos.copy()

    total_ies   = df_ies["co_ies"].nunique()
    total_cursos = df["co_curso"].nunique()
    total_mat   = int(df["qt_mat"].sum())
    total_ing   = int(df["qt_ing"].sum())
    total_conc  = int(df["qt_conc"].sum())

    # Gráfico: Matrículas por Região
    reg_mat = (
        df.groupby("no_regiao")["qt_mat"].sum()
          .sort_values(ascending=False)
          .reset_index()
    )
    fig_reg = go.Figure(go.Bar(
        x=reg_mat["no_regiao"],
        y=reg_mat["qt_mat"],
        marker_color=[COR_REGIOES.get(r, "#888") for r in reg_mat["no_regiao"]],
        hovertemplate="<b>%{x}</b><br>Matrículas: %{y:,.0f}<extra></extra>",
    ))
    fig_reg.update_layout(**_layout_base(), height=260,
                          yaxis_title="Matrículas", title_text="")

    # Gráfico: Matrículas Presencial vs EAD
    mod_mat = (
        df.groupby("tp_modalidade_ensino")["qt_mat"].sum()
          .reset_index()
    )
    fig_mod = go.Figure(go.Pie(
        labels=mod_mat["tp_modalidade_ensino"],
        values=mod_mat["qt_mat"],
        hole=0.55,
        marker_colors=[COR_AZUL, COR_VERDE],
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} (%{percent})<extra></extra>",
        textfont_size=12,
    ))
    fig_mod.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        height=260,
    )

    # Gráfico: Matrículas por Rede (Pública x Privada)
    rede_mat = df.groupby("tp_rede")["qt_mat"].sum().reset_index()
    fig_rede = go.Figure(go.Bar(
        x=rede_mat["tp_rede"],
        y=rede_mat["qt_mat"],
        marker_color=[COR_AZUL, COR_LARANJA],
        hovertemplate="<b>%{x}</b><br>Matrículas: %{y:,.0f}<extra></extra>",
    ))
    fig_rede.update_layout(**_layout_base(), height=260,
                           yaxis_title="Matrículas")

    # Gráfico: IES por Organização Acadêmica
    org_ies = (
        df_ies.groupby("tp_organizacao_academica")["co_ies"].nunique()
              .sort_values(ascending=True)
              .reset_index()
    )
    fig_org = go.Figure(go.Bar(
        x=org_ies["co_ies"],
        y=org_ies["tp_organizacao_academica"],
        orientation="h",
        marker_color=COR_ROXO,
        hovertemplate="<b>%{y}</b><br>IES: %{x:,d}<extra></extra>",
    ))
    fig_org.update_layout(**_layout_base(), height=260,
                          xaxis_title="Nº de IES")

    return html.Div([
        # KPIs
        html.Div([
            _kpi(_fmt_mil(total_ies),    "Instituições (IES)",  COR_AZUL),
            _kpi(_fmt_mil(total_cursos), "Cursos Ativos",       COR_VERDE),
            _kpi(_fmt_mil(total_mat),    "Matrículas",          COR_ROXO),
            _kpi(_fmt_mil(total_ing),    "Ingressantes",        COR_LARANJA),
            _kpi(_fmt_mil(total_conc),   "Concluintes",         COR_CINZA),
        ], className="edu-kpis-row",
           style={"display": "flex", "gap": 12, "marginBottom": 20, "flexWrap": "wrap"}),

        # Linha 1 — Regiões + Modal
        html.Div([
            _card([
                _titulo("Matrículas por Região"),
                dcc.Graph(figure=fig_reg, config={"displayModeBar": False}),
            ]),
            _card([
                _titulo("Distribuição por Modalidade (Presencial vs EAD)"),
                dcc.Graph(figure=fig_mod, config={"displayModeBar": False}),
            ]),
        ], style={"display": "flex", "gap": 12, "marginBottom": 12}),

        # Linha 2 — Rede + Org Acadêmica
        html.Div([
            _card([
                _titulo("Matrículas por Rede (Pública / Privada)"),
                dcc.Graph(figure=fig_rede, config={"displayModeBar": False}),
            ]),
            _card([
                _titulo("Nº de IES por Organização Acadêmica"),
                dcc.Graph(figure=fig_org, config={"displayModeBar": False}),
            ]),
        ], style={"display": "flex", "gap": 12, "marginBottom": 12}),

        # Nota rodapé
        _nota("Fonte: INEP — Censo da Educação Superior 2024. Dados consolidados."),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# ABA 2 — CURSOS E ALUNOS  (com filtros interativos)
# ═══════════════════════════════════════════════════════════════════════════════
def _aba_cursos_layout():
    """Retorna o layout estático da aba (filtros + containers de saída)."""
    return html.Div([
        # Barra de filtros
        _card([
            html.Div([
                _titulo("Filtros"),
                html.Div([
                    _filtro_label("Região",    "f-regiao",    REGIOES,     "Todas", 170),
                    _filtro_label("UF",        "f-uf",        UFS,         "Todas", 130),
                    _filtro_label("Modalidade","f-modal",     MODALIDADES, "Todas", 190),
                    _filtro_label("Grau",      "f-grau",      GRAUS,       "Todos", 180),
                    _filtro_label("Rede",      "f-rede",      REDES,       "Todas", 140),
                ], style={"display": "flex", "gap": 12, "flexWrap": "wrap",
                          "alignItems": "flex-end"}),
            ]),
        ], shadow=True),

        html.Div(style={"height": 16}),

        # KPIs dinâmicos
        html.Div(id="cursos-kpis",
                 style={"display": "flex", "gap": 12, "marginBottom": 12, "flexWrap": "wrap"}),

        # Linha de gráficos dinâmicos
        html.Div([
            _card([
                _titulo("Matrículas por Área do Conhecimento"),
                html.Div(id="graf-area-mat"),
            ]),
            _card([
                _titulo("Ingressantes por Grau Acadêmico"),
                html.Div(id="graf-grau-ing"),
            ]),
        ], style={"display": "flex", "gap": 12, "marginBottom": 12}),

        # Linha 2 de gráficos
        html.Div([
            _card([
                _titulo("Distribuição por Gênero — Matrículas"),
                html.Div(id="graf-genero"),
            ]),
            _card([
                _titulo("Acesso e Financiamento Estudantil"),
                html.Div(id="graf-financ"),
            ]),
        ], style={"display": "flex", "gap": 12, "marginBottom": 12}),

        # Tabela Top Cursos
        _card([
            html.Div([
                _titulo("Top Cursos por Número de Matrículas"),
                _filtro_label("Área", "f-area-tab", AREAS_GERAL, "Todas", 300),
            ], style={"display": "flex", "justifyContent": "space-between",
                      "alignItems": "flex-start", "marginBottom": 8, "flexWrap": "wrap", "gap": 8}),
            html.Div(id="tabela-top-cursos"),
        ]),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# ABA 3 — MAPA (distribuição por UF)
# ═══════════════════════════════════════════════════════════════════════════════
def _aba_mapa_layout():
    return html.Div([
        # Filtros do mapa
        _card([
            html.Div([
                _titulo("Filtros do Mapa"),
                html.Div([
                    _filtro_label("Indicador",  "mapa-indicador",
                                  ["Matrículas", "Ingressantes", "Concluintes",
                                   "Cursos", "IES", "Docentes (IES)"],
                                  "Matrículas", 210),
                    _filtro_label("Modalidade", "mapa-modal",     MODALIDADES, "Todas", 190),
                    _filtro_label("Rede",        "mapa-rede",      REDES,       "Todas", 140),
                    _filtro_label("Grau",        "mapa-grau",      GRAUS,       "Todos", 180),
                ], style={"display": "flex", "gap": 12, "flexWrap": "wrap",
                          "alignItems": "flex-end"}),
            ]),
        ], shadow=True),

        html.Div(style={"height": 16}),

        html.Div([
            _card([
                _titulo("Distribuição por UF"),
                _nota("Intensidade proporcional ao indicador selecionado."),
                html.Div(id="mapa-uf-container", style={"marginTop": 12}),
            ], shadow=True),
        ], style={"marginBottom": 12}),

        # Tabela ranking UF
        _card([
            _titulo("Ranking por UF"),
            html.Div(id="tabela-ranking-uf"),
        ]),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# APP DASH
# ═══════════════════════════════════════════════════════════════════════════════
app = dash.Dash(
    __name__,
    title="Educação Superior — INEP 2024",
    suppress_callback_exceptions=True,
    url_base_pathname=os.environ.get("DASH_PREFIX", "/educacao-superior/"),
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}],
)
server = app.server

_original_layout = html.Div(
    className="app-shell",
    style={"fontFamily": "Inter, sans-serif", "backgroundColor": COR_FUNDO, "minHeight": "100vh"},
    children=[
        # ── Header ────────────────────────────────────────────────────────────
        html.Div(
            [
                html.Div([
                    html.Div([
                        html.P("FUNASA / INEP", style={"fontSize": 10, "color": "#8BAFC8",
                                                        "margin": "0 0 2px 0",
                                                        "letterSpacing": "0.1em", "fontWeight": 600}),
                        html.H1("Educação Superior no Brasil",
                                style={"fontSize": 22, "fontWeight": 700,
                                       "color": "#fff", "margin": 0}),
                        html.P("Censo da Educação Superior 2024 · Fonte: INEP",
                               style={"fontSize": 12, "color": "#8BAFC8",
                                      "margin": "4px 0 0 0"}),
                    ], id="edu-header-titulo"),
                ], style={"display": "flex", "alignItems": "center", "flex": 1}),

                html.Div([
                    html.P(f"{df_ies['co_ies'].nunique():,}".replace(",", "."),
                           style={"fontSize": 28, "fontWeight": 700, "color": "#fff",
                                  "margin": 0, "textAlign": "center"}),
                    html.P("IES", style={"fontSize": 10, "color": "#8BAFC8",
                                         "margin": 0, "textAlign": "center",
                                         "letterSpacing": "0.05em"}),
                ], style={"backgroundColor": "#2d4a6b", "borderRadius": 8,
                          "padding": "12px 20px"}),
            ],
            id="edu-header",
            style={"backgroundColor": COR_HEADER, "padding": "20px 32px",
                   "display": "flex", "alignItems": "center",
                   "justifyContent": "space-between"},
        ),

        # ── Abas ──────────────────────────────────────────────────────────────
        html.Div(
            id="edu-tabs-container",
            style={"padding": "10px 32px 0 32px"},
            children=[
                dcc.Tabs(
                    id="edu-abas",
                    value="aba-panorama",
                    children=[
                        dcc.Tab(label="Panorama Geral",  value="aba-panorama",
                                className="edu-tab edu-tab--azul",
                                selected_className="edu-tab edu-tab--azul edu-tab--selected"),
                        dcc.Tab(label="Cursos e Alunos", value="aba-cursos",
                                className="edu-tab edu-tab--verde",
                                selected_className="edu-tab edu-tab--verde edu-tab--selected"),
                        dcc.Tab(label="Mapa por UF",     value="aba-mapa",
                                className="edu-tab edu-tab--roxo",
                                selected_className="edu-tab edu-tab--roxo edu-tab--selected"),
                    ],
                )
            ],
        ),

        # ── Conteúdo dinâmico ─────────────────────────────────────────────────
        html.Div(id="edu-conteudo", style={"padding": "24px 32px"}),
    ],
)

if _HAS_MIV:
    app.layout = html.Div([
        miv_style_tag(),
        funasa_page_loading(wrap_layout(_original_layout, active_path="/educacao-superior/")),
    ])
else:
    app.layout = _original_layout

# ── CSS das abas ──────────────────────────────────────────────────────────────
app.index_string = app.index_string.replace(
    "</head>",
    """<style>
    .edu-tab {
        font-family: Inter, 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 12px 24px !important;
        background-color: #ffffff !important;
        border: 1px solid #DBE3EA !important;
        border-radius: 8px 8px 0 0 !important;
        color: #2d3748 !important;
        border-bottom: none !important;
    }
    .edu-tab--azul  { border-top: 3px solid #1565C0 !important; }
    .edu-tab--verde { border-top: 3px solid #2F855A !important; }
    .edu-tab--roxo  { border-top: 3px solid #6B46C1 !important; }

    .edu-tab--azul.edu-tab--selected {
        background-color: #1565C0 !important;
        border-color: #1565C0 !important;
        border-top: 3px solid #1565C0 !important;
        color: #ffffff !important;
        box-shadow: 0 2px 4px rgba(16,24,40,.10);
    }
    .edu-tab--verde.edu-tab--selected {
        background-color: #2F855A !important;
        border-color: #2F855A !important;
        border-top: 3px solid #2F855A !important;
        color: #ffffff !important;
        box-shadow: 0 2px 4px rgba(16,24,40,.10);
    }
    .edu-tab--roxo.edu-tab--selected {
        background-color: #6B46C1 !important;
        border-color: #6B46C1 !important;
        border-top: 3px solid #6B46C1 !important;
        color: #ffffff !important;
        box-shadow: 0 2px 4px rgba(16,24,40,.10);
    }
    .tab-container { border-bottom: none !important; }
    </style></head>""",
)


# ═══════════════════════════════════════════════════════════════════════════════
# CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════════

# ── Roteamento das abas ───────────────────────────────────────────────────────
@app.callback(Output("edu-conteudo", "children"), Input("edu-abas", "value"))
def renderizar_aba(aba):
    if aba == "aba-panorama":
        return _aba_panorama()
    if aba == "aba-cursos":
        return _aba_cursos_layout()
    if aba == "aba-mapa":
        return _aba_mapa_layout()
    return html.Div()


# ── Callback cascata: Região → UF (aba Cursos) ───────────────────────────────
@app.callback(
    Output("f-uf", "options"),
    Output("f-uf", "value"),
    Input("f-regiao", "value"),
)
def filtrar_uf_por_regiao(regiao):
    if regiao and regiao != "Todas":
        ufs = sorted(df_cursos[df_cursos["no_regiao"] == regiao]["sg_uf"].dropna().unique())
    else:
        ufs = sorted(df_cursos["sg_uf"].dropna().unique())
    return [{"label": "Todas", "value": "Todas"}] + [{"label": u, "value": u} for u in ufs], "Todas"


# ── KPIs + Gráficos dinâmicos da Aba Cursos ──────────────────────────────────
@app.callback(
    Output("cursos-kpis",    "children"),
    Output("graf-area-mat",  "children"),
    Output("graf-grau-ing",  "children"),
    Output("graf-genero",    "children"),
    Output("graf-financ",    "children"),
    Input("f-regiao",  "value"),
    Input("f-uf",      "value"),
    Input("f-modal",   "value"),
    Input("f-grau",    "value"),
    Input("f-rede",    "value"),
)
def atualizar_cursos(regiao, uf, modal, grau, rede):
    df = _aplicar_filtros_cursos(regiao, uf, modal, grau, rede)

    n_cursos = int(df["co_curso"].nunique())
    n_mat    = int(df["qt_mat"].sum())
    n_ing    = int(df["qt_ing"].sum())
    n_conc   = int(df["qt_conc"].sum())
    n_vg     = int(df["qt_vg_total"].sum())

    kpis = html.Div([
        _kpi(_fmt_mil(n_cursos), "Cursos",       COR_AZUL),
        _kpi(_fmt_mil(n_mat),    "Matrículas",   COR_VERDE),
        _kpi(_fmt_mil(n_ing),    "Ingressantes", COR_ROXO),
        _kpi(_fmt_mil(n_conc),   "Concluintes",  COR_LARANJA),
        _kpi(_fmt_mil(n_vg),     "Vagas Totais", COR_CINZA),
    ], style={"display": "flex", "gap": 12, "flexWrap": "wrap"})

    # Gráfico: Área do conhecimento × Matrículas
    area_df = (
        df.groupby("no_cine_area_geral")["qt_mat"]
          .sum()
          .sort_values(ascending=True)
          .reset_index()
    )
    fig_area = go.Figure(go.Bar(
        x=area_df["qt_mat"],
        y=area_df["no_cine_area_geral"],
        orientation="h",
        marker_color=COR_AZUL,
        hovertemplate="<b>%{y}</b><br>Matrículas: %{x:,.0f}<extra></extra>",
    ))
    fig_area.update_layout(**_layout_base(), height=320, xaxis_title="Matrículas")

    # Gráfico: Grau acadêmico × Ingressantes
    grau_df = (
        df.groupby("tp_grau_academico")["qt_ing"]
          .sum()
          .sort_values(ascending=False)
          .reset_index()
    )
    fig_grau = go.Figure(go.Bar(
        x=grau_df["tp_grau_academico"],
        y=grau_df["qt_ing"],
        marker_color=COR_VERDE,
        hovertemplate="<b>%{x}</b><br>Ingressantes: %{y:,.0f}<extra></extra>",
    ))
    fig_grau.update_layout(**_layout_base(), height=320, yaxis_title="Ingressantes")

    # Gráfico: Gênero — Matrículas
    fem = int(df["qt_mat_fem"].sum())
    masc = int(df["qt_mat_masc"].sum())
    fig_gen = go.Figure(go.Pie(
        labels=["Feminino", "Masculino"],
        values=[fem, masc],
        hole=0.5,
        marker_colors=["#E05AA0", "#3182CE"],
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} (%{percent})<extra></extra>",
        textfont_size=13,
    ))
    fig_gen.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        height=300,
    )

    # Gráfico: Financiamento (ENEM, ProUni, FIES)
    labels_fin = ["ENEM (ing.)", "ProUni I (mat.)", "ProUni P (mat.)", "FIES (mat.)"]
    vals_fin   = [
        int(df["qt_ing_enem"].sum()),
        int(df["qt_mat_prounii"].sum()),
        int(df["qt_mat_prounip"].sum()),
        int(df["qt_mat_fies"].sum()),
    ]
    fig_fin = go.Figure(go.Bar(
        x=labels_fin, y=vals_fin,
        marker_color=[COR_AZUL, COR_VERDE, COR_ROXO, COR_LARANJA],
        hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>",
    ))
    fig_fin.update_layout(**_layout_base(), height=300, yaxis_title="Qtd. Alunos")

    return (
        kpis,
        dcc.Graph(figure=fig_area, config={"displayModeBar": False}),
        dcc.Graph(figure=fig_grau, config={"displayModeBar": False}),
        dcc.Graph(figure=fig_gen,  config={"displayModeBar": False}),
        dcc.Graph(figure=fig_fin,  config={"displayModeBar": False}),
    )


# ── Tabela top cursos ─────────────────────────────────────────────────────────
@app.callback(
    Output("tabela-top-cursos", "children"),
    Input("f-regiao",    "value"),
    Input("f-uf",        "value"),
    Input("f-modal",     "value"),
    Input("f-grau",      "value"),
    Input("f-rede",      "value"),
    Input("f-area-tab",  "value"),
)
def tabela_top_cursos(regiao, uf, modal, grau, rede, area):
    df = _aplicar_filtros_cursos(regiao, uf, modal, grau, rede)
    if area and area != "Todas":
        df = df[df["no_cine_area_geral"] == area]

    top = (
        df.groupby(["no_curso", "tp_grau_academico", "no_cine_area_geral",
                    "tp_modalidade_ensino", "tp_rede"])
          .agg(
              Matrículas=("qt_mat", "sum"),
              Ingressantes=("qt_ing", "sum"),
              Concluintes=("qt_conc", "sum"),
              IES=("co_ies", "nunique"),
          )
          .reset_index()
          .sort_values("Matrículas", ascending=False)
          .head(50)
    )
    top = top.rename(columns={
        "no_curso": "Curso", "tp_grau_academico": "Grau",
        "no_cine_area_geral": "Área",
        "tp_modalidade_ensino": "Modalidade", "tp_rede": "Rede",
    })
    top["Matrículas"]   = top["Matrículas"].apply(lambda v: f"{int(v):,}".replace(",", "."))
    top["Ingressantes"] = top["Ingressantes"].apply(lambda v: f"{int(v):,}".replace(",", "."))
    top["Concluintes"]  = top["Concluintes"].apply(lambda v: f"{int(v):,}".replace(",", "."))
    top["IES"]          = top["IES"].apply(lambda v: f"{int(v):,}".replace(",", "."))

    nota = html.P(
        f"Exibindo os 50 primeiros cursos, ordenados por matrículas.",
        style={"fontSize": 11, "color": "#9ca3af", "margin": "10px 0 0 0"},
    )
    return html.Div([
        html.Div(_tabela_html(top), style={"overflowX": "auto"}),
        nota,
    ])


# ── Callback Mapa por UF ──────────────────────────────────────────────────────
@app.callback(
    Output("mapa-uf-container",  "children"),
    Output("tabela-ranking-uf",  "children"),
    Input("mapa-indicador", "value"),
    Input("mapa-modal",     "value"),
    Input("mapa-rede",      "value"),
    Input("mapa-grau",      "value"),
)
def atualizar_mapa(indicador, modal, rede, grau):
    # Seleção da fonte de dados e campo
    if indicador in ["IES", "Docentes (IES)"]:
        df_m = _aplicar_filtros_ies("Todas", "Todas",
                                    "Todas", rede if rede != "Todas" else "Todas")
        if indicador == "IES":
            agg = df_m.groupby("sg_uf_ies")["co_ies"].nunique().reset_index()
            agg.columns = ["sg_uf", "valor"]
        else:
            agg = df_m.groupby("sg_uf_ies")["qt_doc_total"].sum().reset_index()
            agg.columns = ["sg_uf", "valor"]
    else:
        df_m = _aplicar_filtros_cursos("Todas", "Todas", modal, grau, rede)
        campo = {"Matrículas": "qt_mat", "Ingressantes": "qt_ing",
                 "Concluintes": "qt_conc", "Cursos": "qt_curso"}.get(indicador, "qt_mat")
        agg = df_m.groupby("sg_uf")[campo].sum().reset_index()
        agg.columns = ["sg_uf", "valor"]

    agg = agg.sort_values("valor", ascending=False).reset_index(drop=True)
    agg["rank"] = agg.index + 1

    # ── Mapa coroplético por estado ───────────────────────────────────────────
    hover_texts = []
    for _, row in agg.iterrows():
        hover_texts.append(
            f"<b>{row['sg_uf']}</b><br>{indicador}: {int(row['valor']):,}".replace(",", ".")
        )
    agg["hover"] = hover_texts

    fig_mapa = go.Figure(go.Choropleth(
        geojson=geojson_estados,
        locations=agg["sg_uf"],
        z=agg["valor"],
        featureidkey="properties.sigla",
        colorscale=[
            [0.0,  "#E6EFF9"],
            [0.25, "#63B3ED"],
            [0.55, "#1565C0"],
            [0.80, "#0C326F"],
            [1.0,  "#071D41"],
        ],
        marker_line_color="#ffffff",
        marker_line_width=1.0,
        colorbar=dict(
            title=dict(text=indicador, font=dict(size=11)),
            thickness=14,
            len=0.7,
            x=1.01,
        ),
        customdata=agg["hover"],
        hovertemplate="%{customdata}<extra></extra>",
        showscale=True,
    ))
    fig_mapa.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="#F0F2F5",
    )
    fig_mapa.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=520,
        paper_bgcolor="#F0F2F5",
        plot_bgcolor="#F0F2F5",
        geo=dict(bgcolor="#F0F2F5"),
        hoverlabel=dict(
            bgcolor="#ffffff",
            bordercolor="#DEE2E6",
            font=dict(family="Inter, sans-serif", size=12),
        ),
    )

    # ── Barras horizontais ranking UF ─────────────────────────────────────────
    agg_bar = agg.sort_values("valor", ascending=True)
    fig_bar = go.Figure(go.Bar(
        x=agg_bar["valor"],
        y=agg_bar["sg_uf"],
        orientation="h",
        marker=dict(
            color=agg_bar["valor"],
            colorscale=[
                [0.0, "#E6EFF9"], [0.4, "#63B3ED"],
                [0.7, "#1565C0"], [1.0, "#071D41"],
            ],
            showscale=False,
        ),
        hovertemplate="<b>%{y}</b><br>" + indicador + ": %{x:,.0f}<extra></extra>",
    ))
    fig_bar.update_layout(
        margin=dict(l=60, r=20, t=10, b=40),
        height=520,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", size=12),
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=indicador),
        yaxis=dict(showgrid=False, linecolor="#e0e0e0"),
        hoverlabel=dict(bgcolor="#fff", bordercolor="#ccc", font_size=12),
    )

    mapa_e_barras = html.Div([
        html.Div(
            dcc.Graph(figure=fig_mapa, config={"displayModeBar": False}),
            style={"flex": "1.2"},
        ),
        html.Div(
            dcc.Graph(figure=fig_bar, config={"displayModeBar": False}),
            style={"flex": "1", "borderLeft": "1px solid #e2e8f0", "paddingLeft": "8px"},
        ),
    ], style={"display": "flex", "gap": 8, "alignItems": "flex-start"})

    # Tabela ranking
    tab_df = agg[["rank", "sg_uf", "valor"]].copy()
    tab_df.columns = ["#", "UF", indicador]
    tab_df[indicador] = tab_df[indicador].apply(lambda v: f"{int(v):,}".replace(",", "."))

    return (
        mapa_e_barras,
        html.Div(_tabela_html(tab_df), style={"overflowX": "auto"}),
    )


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8051)
