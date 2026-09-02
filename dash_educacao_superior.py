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
from dash import Input, Output, State, dcc, html, callback_context
import pandas as pd
import plotly.graph_objects as go
import requests
import trino

# ── Loading component ─────────────────────────────────────────────────────────
from loading_components import educ_page_loading

# ── Shared layout MIV BigData FUNASA (opcional) ───────────────────────────────
try:
    from shared_layout import wrap_layout, miv_style_tag
    _HAS_MIV = True
except ImportError:
    _HAS_MIV = False

# ── Conexão Trino ─────────────────────────────────────────────────────────────
TRINO_HOST     = os.getenv("TRINO_HOST",     "trino.dataiesb.com")
TRINO_PORT     = int(os.getenv("TRINO_PORT", "443"))
TRINO_USER     = os.getenv("TRINO_USER",     "admin")
TRINO_PASSWORD = os.getenv("TRINO_PASSWORD", "JGtHJlSQV5TqDh8jJJ1U0u6WyaSUxeLW")
TRINO_CATALOG  = "seaweedfs"
TRINO_SCHEMA   = "raw"

def _trino_query(sql: str) -> pd.DataFrame:
    """Executa uma query no Trino e retorna um DataFrame."""
    conn = trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=TRINO_USER,
        http_scheme="https",
        auth=trino.auth.BasicAuthentication(TRINO_USER, TRINO_PASSWORD),
        catalog=TRINO_CATALOG,
        schema=TRINO_SCHEMA,
    )
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=cols)

print("[EDUC] Carregando tabela de cursos...", flush=True)

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

import time as _time

# Descobrir todos os anos disponíveis
_anos_df = _trino_query("SELECT DISTINCT nu_ano_censo FROM seaweedfs.raw.inep_educacao_superior_cursos ORDER BY nu_ano_censo")
ANOS_DISPONIVEIS = sorted(_anos_df["nu_ano_censo"].astype(int).tolist())
ANO_CENSO = ANOS_DISPONIVEIS[-1]  # mais recente, usado como padrão nos KPIs
print(f"[EDUC] Anos disponíveis: {ANOS_DISPONIVEIS} | Padrão: {ANO_CENSO}", flush=True)

# Carregar todos os anos de cursos
print(f"[EDUC] Carregando cursos (todos os anos)...", flush=True)
_t0 = _time.time()
df_cursos = _trino_query(
    f"SELECT {', '.join(COLS_CURSOS)} FROM seaweedfs.raw.inep_educacao_superior_cursos"
)
print(f"[EDUC] Cursos carregados: {len(df_cursos)} linhas em {_time.time()-_t0:.0f}s", flush=True)

# Carregar todos os anos de IES
print(f"[EDUC] Carregando IES (todos os anos)...", flush=True)
_t0 = _time.time()
df_ies = _trino_query(
    f"SELECT {', '.join(COLS_IES)} FROM seaweedfs.raw.inep_educacao_superior_ies"
)
print(f"[EDUC] IES carregadas: {len(df_ies)} linhas em {_time.time()-_t0:.0f}s", flush=True)

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
COR_AZUL    = "#2B6CB0"
COR_VERDE   = "#2F855A"
COR_ROXO    = "#6B46C1"
COR_LARANJA = "#C05621"
COR_CINZA   = "#5A6B7A"
# Aliases para manter compatibilidade com padrão dash_pib
COR_CARD_1 = "#2B6CB0"
COR_CARD_2 = "#2F855A"
COR_CARD_3 = "#6B46C1"
COR_CARD_4 = "#5A6B7A"
COR_CARD_5 = "#C05621"

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
            html.P(valor, style={"fontSize": 28, "fontWeight": 700, "color": "#fff",
                                  "margin": "0 0 4px 0", "whiteSpace": "nowrap"}),
            html.P(label, style={"fontSize": 11, "fontWeight": 600, "color": "#fff",
                                  "margin": 0, "textTransform": "uppercase",
                                  "letterSpacing": "0.05em", "whiteSpace": "nowrap"}),
        ],
        style={"backgroundColor": cor, "borderRadius": 8, "padding": "18px 22px",
               "flex": 1, "minWidth": 160},
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
    """Formata número inteiro com ponto como separador de milhar."""
    v = int(float(val))
    return f"{v:,}".replace(",", ".")


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
def _aplicar_filtros_cursos(regiao, uf, modalidade, grau, rede, ano=None):
    df = df_cursos.copy()
    # Filtro de ano — padrão: ano mais recente
    _ano = int(ano) if ano else ANO_CENSO
    df = df[df["nu_ano_censo"].astype(int) == _ano]
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


def _aplicar_filtros_ies(regiao, uf, org, rede, ano=None):
    df = df_ies.copy()
    # Filtro de ano — padrão: ano mais recente
    _ano = int(ano) if ano else ANO_CENSO
    df = df[df["nu_ano_censo"].astype(int) == _ano]
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
            _kpi(_fmt_mil(total_ies),    "Instituições (IES)",  COR_CARD_1),
            _kpi(_fmt_mil(total_cursos), "Cursos Ativos",       COR_CARD_2),
            _kpi(_fmt_mil(total_mat),    "Matrículas",          COR_CARD_3),
            _kpi(_fmt_mil(total_ing),    "Ingressantes",        COR_CARD_5),
            _kpi(_fmt_mil(total_conc),   "Concluintes",         COR_CARD_4),
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
                    _filtro_label("Ano",       "f-ano",       sorted(ANOS_DISPONIVEIS, reverse=True), ANO_CENSO, 100),
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
                    _filtro_label("Ano",        "mapa-ano",       sorted(ANOS_DISPONIVEIS, reverse=True), ANO_CENSO, 100),
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
# ABA 4 — VISÃO POR MUNICÍPIO (Reestruturada com foco em Faculdades, Cursos e Alunos)
# ═══════════════════════════════════════════════════════════════════════════════
def _aba_municipio_layout():
    ufs_validas = sorted([u for u in df_cursos["sg_uf"].dropna().unique() if u != "Todas"])
    uf_inicial = ufs_validas[0] if ufs_validas else "SP"
    
    return html.Div([
        dcc.Store(id="mun-ies-selecionada", data=None),
        
        # Filtros
        _card([
            _titulo("Filtros de Pesquisa por Município"),
            html.Div([
                _filtro_label("Ano", "mun-ano", sorted(ANOS_DISPONIVEIS, reverse=True), ANO_CENSO, 110),
                _filtro_label("Estado (UF)", "mun-uf", ufs_validas, uf_inicial, 120),
                html.Div([
                    html.Label("Município", style={"fontSize": 11, "fontWeight": 600, "color": "#4a5568", "marginBottom": 4, "display": "block"}),
                    dcc.Dropdown(id="mun-municipio", clearable=False, style={"width": 260, "fontSize": 13, "fontFamily": "Inter, sans-serif"}),
                ]),
            ], style={"display": "flex", "gap": 16, "alignItems": "flex-end", "flexWrap": "wrap"}),
        ], shadow=True),

        html.Div(style={"height": 16}),

        # Container da Tabela Master de Faculdades
        _card([
            html.Div([
                html.Div([
                    _titulo("Faculdades / Instituições (IES) no Município"),
                    _nota("Clique em uma faculdade na tabela abaixo para abrir o detalhamento completo de seus Cursos e Alunos."),
                ], style={"flex": 1}),
                html.Div(id="mun-kpi-ies",
                         style={"backgroundColor": COR_AZUL, "borderRadius": 8,
                                "padding": "10px 20px", "textAlign": "center",
                                "minWidth": 140}),
            ], style={"display": "flex", "alignItems": "center",
                      "gap": 16, "marginBottom": 12, "flexWrap": "wrap"}),
            html.Div(id="mun-tabela-ies-container"),
        ]),

        html.Div(style={"height": 16}),

        # Container do Detalhamento da Faculdade Selecionada (Cursos e Alunos)
        html.Div(id="mun-detalhe-ies-container"),
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
                        dcc.Tab(label="Visão por Município", value="aba-municipio",
                                className="edu-tab edu-tab--laranja",
                                selected_className="edu-tab edu-tab--laranja edu-tab--selected"),
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
    app.layout = educ_page_loading(_original_layout)

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
    .edu-tab--laranja { border-top: 3px solid #C05621 !important; }

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
    .edu-tab--laranja.edu-tab--selected {
        background-color: #C05621 !important;
        border-color: #C05621 !important;
        border-top: 3px solid #C05621 !important;
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
    if aba == "aba-municipio":
        return _aba_municipio_layout()
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
    Input("f-ano",     "value"),
    Input("f-regiao",  "value"),
    Input("f-uf",      "value"),
    Input("f-modal",   "value"),
    Input("f-grau",    "value"),
    Input("f-rede",    "value"),
)
def atualizar_cursos(ano, regiao, uf, modal, grau, rede):
    df = _aplicar_filtros_cursos(regiao, uf, modal, grau, rede, ano)

    n_cursos = int(df["co_curso"].nunique())
    n_mat    = int(df["qt_mat"].sum())
    n_ing    = int(df["qt_ing"].sum())
    n_conc   = int(df["qt_conc"].sum())
    n_vg     = int(df["qt_vg_total"].sum())

    kpis = html.Div([
        _kpi(_fmt_mil(n_cursos), "Cursos",       COR_CARD_1),
        _kpi(_fmt_mil(n_mat),    "Matrículas",   COR_CARD_2),
        _kpi(_fmt_mil(n_ing),    "Ingressantes", COR_CARD_3),
        _kpi(_fmt_mil(n_conc),   "Concluintes",  COR_CARD_5),
        _kpi(_fmt_mil(n_vg),     "Vagas Totais", COR_CARD_4),
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
    ))
    fig_gen.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=320)

    # Gráfico: Financiamento / Bolsas
    fies = int(df["qt_mat_fies"].sum())
    prouni_i = int(df["qt_mat_prounii"].sum())
    prouni_p = int(df["qt_mat_prounip"].sum())
    enem = int(df["qt_ing_enem"].sum())

    fig_fin = go.Figure(go.Bar(
        x=["Ingr. ENEM", "FIES", "ProUni Integral", "ProUni Parcial"],
        y=[enem, fies, prouni_i, prouni_p],
        marker_color=[COR_AZUL, COR_VERDE, COR_ROXO, COR_LARANJA],
        hovertemplate="<b>%{x}</b><br>Alunos: %{y:,.0f}<extra></extra>",
    ))
    fig_fin.update_layout(**_layout_base(), height=320, yaxis_title="Alunos")

    return kpis, dcc.Graph(figure=fig_area), dcc.Graph(figure=fig_grau), dcc.Graph(figure=fig_gen), dcc.Graph(figure=fig_fin)


# ── Callback Tabela Top Cursos ────────────────────────────────────────────────
@app.callback(
    Output("tabela-top-cursos", "children"),
    Input("f-ano", "value"),
    Input("f-regiao", "value"),
    Input("f-uf", "value"),
    Input("f-modal", "value"),
    Input("f-grau", "value"),
    Input("f-rede", "value"),
    Input("f-area-tab", "value"),
)
def atualizar_tabela_cursos(ano, regiao, uf, modal, grau, rede, area):
    df = _aplicar_filtros_cursos(regiao, uf, modal, grau, rede, ano)
    if area and area != "Todas":
        df = df[df["no_cine_area_geral"] == area]

    top = (
        df.groupby("no_curso")
          .agg({
              "qt_mat": "sum",
              "qt_ing": "sum",
              "qt_conc": "sum",
              "co_curso": "nunique",
          })
          .reset_index()
          .rename(columns={
              "no_curso": "Nome do Curso",
              "qt_mat": "Matrículas",
              "qt_ing": "Ingressantes",
              "qt_conc": "Concluintes",
              "co_curso": "Nº Turmas/Ofertados",
          })
          .sort_values(by="Matrículas", ascending=False)
          .head(15)
    )

    for c in ["Matrículas", "Ingressantes", "Concluintes", "Nº Turmas/Ofertados"]:
        top[c] = top[c].apply(_fmt_mil)

    return _tabela_html(top)


# ── Callback Mapa por UF ──────────────────────────────────────────────────────
@app.callback(
    Output("mapa-uf-container", "children"),
    Output("tabela-ranking-uf", "children"),
    Input("mapa-indicador", "value"),
    Input("mapa-ano", "value"),
    Input("mapa-modal", "value"),
    Input("mapa-rede", "value"),
    Input("mapa-grau", "value"),
)
def atualizar_mapa(indicador, ano, modal, rede, grau):
    # Filtrar dados para o mapa
    df = df_cursos.copy()
    df = df[df["nu_ano_censo"].astype(int) == int(ano)]
    if modal != "Todas":
        df = df[df["tp_modalidade_ensino"] == modal]
    if rede != "Todas":
        df = df[df["tp_rede"] == rede]
    if grau != "Todos":
        df = df[df["tp_grau_academico"] == grau]

    df_ies_f = df_ies[df_ies["nu_ano_censo"].astype(int) == int(ano)]
    if rede != "Todas":
        df_ies_f = df_ies_f[df_ies_f["tp_rede"] == rede]

    # Mapear indicador selecionado para coluna correspondente
    if indicador == "Matrículas":
        agrup = df.groupby("sg_uf")["qt_mat"].sum().reset_index().rename(columns={"qt_mat": "Valor"})
    elif indicador == "Ingressantes":
        agrup = df.groupby("sg_uf")["qt_ing"].sum().reset_index().rename(columns={"qt_ing": "Valor"})
    elif indicador == "Concluintes":
        agrup = df.groupby("sg_uf")["qt_conc"].sum().reset_index().rename(columns={"qt_conc": "Valor"})
    elif indicador == "Cursos":
        agrup = df.groupby("sg_uf")["co_curso"].nunique().reset_index().rename(columns={"co_curso": "Valor"})
    elif indicador == "IES":
        agrup = df_ies_f.groupby("sg_uf_ies")["co_ies"].nunique().reset_index().rename(columns={"sg_uf_ies": "sg_uf", "co_ies": "Valor"})
    else:  # Docentes
        agrup = df_ies_f.groupby("sg_uf_ies")["qt_doc_exe"].sum().reset_index().rename(columns={"sg_uf_ies": "sg_uf", "qt_doc_exe": "Valor"})

    fig_mapa = go.Figure(go.Choroplethmap(
        geojson=geojson_estados,
        locations=agrup["sg_uf"],
        z=agrup["Valor"],
        featureidkey="properties.sigla",
        colorscale=[
            [0.0,  "#EBF5FB"],
            [0.15, "#AED6F1"],
            [0.35, "#5DADE2"],
            [0.6,  "#2E86C1"],
            [0.8,  "#1A5276"],
            [1.0,  "#0B2B40"],
        ],
        marker_opacity=0.85,
        marker_line_width=1,
        marker_line_color="#ffffff",
        hovertemplate="<b>%{location}</b><br>" + indicador + ": %{z:,.0f}<extra></extra>",
    ))
    fig_mapa.update_layout(
        map_style="white-bg",
        map_zoom=3,
        map_center={"lat": -14.2350, "lon": -51.9253},
        margin=dict(l=0, r=0, t=0, b=0),
        height=450,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )

    # Tabela Ranking
    rk = agrup.sort_values("Valor", ascending=False).reset_index(drop=True)
    rk.index += 1
    rk.reset_index(inplace=True)
    rk.columns = ["Posição", "UF", indicador]
    rk[indicador] = rk[indicador].apply(_fmt_mil)

    return dcc.Graph(figure=fig_mapa), _tabela_html(rk)


# ═══════════════════════════════════════════════════════════════════════════════
# CALLBACKS DA ABA VISÃO POR MUNICÍPIO (Ajustados)
# ═══════════════════════════════════════════════════════════════════════════════

# 1. Atualizar lista de Municípios com base na UF selecionada
@app.callback(
    Output("mun-municipio", "options"),
    Output("mun-municipio", "value"),
    Input("mun-uf", "value"),
    Input("mun-ano", "value"),
)
def atualizar_municipios_por_uf(uf, ano):
    if not uf:
        return [], None
    df_m = df_cursos[(df_cursos["sg_uf"] == uf) & (df_cursos["nu_ano_censo"].astype(int) == int(ano))]
    muns = sorted([m for m in df_m["no_municipio"].dropna().unique() if m])
    val = muns[0] if muns else None
    return [{"label": m, "value": m} for m in muns], val


# 2. Resetar seleção de IES quando os filtros principais mudarem
@app.callback(
    Output("mun-ies-selecionada", "data"),
    Input("mun-uf", "value"),
    Input("mun-municipio", "value"),
    Input("mun-ano", "value"),
)
def reset_ies_selecionada(uf, mun, ano):
    return None


# 3. Gerenciar o clique no botão "Ver Cursos" para selecionar uma IES
@app.callback(
    Output("mun-ies-selecionada", "data", allow_duplicate=True),
    [Input({"type": "btn-sel-ies", "co_ies": dash.ALL}, "n_clicks")],
    prevent_initial_call=True
)
def capturar_clique_ies(n_clicks_list):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return dash.no_update
    trig_id = ctx.triggered[0]["prop_id"].split(".")[0]
    import json
    try:
        obj_id = json.loads(trig_id)
        return obj_id.get("co_ies")
    except Exception:
        return dash.no_update


# 4. Renderizar Tabela Master de Faculdades no Município
@app.callback(
    Output("mun-tabela-ies-container", "children"),
    Output("mun-kpi-ies", "children"),
    Input("mun-uf", "value"),
    Input("mun-municipio", "value"),
    Input("mun-ano", "value"),
    Input("mun-ies-selecionada", "data"),
)
def renderizar_tabela_faculdades(uf, mun, ano, ies_selecionada_co):
    if not uf or not mun:
        vazio = html.P("Selecione um Estado e um Município nos filtros acima.", style={"color": "#718096"})
        return vazio, html.Div()

    ano = int(ano)
    # Filtra cursos e IES no município
    df_c = df_cursos[(df_cursos["sg_uf"] == uf) & (df_cursos["no_municipio"] == mun) & (df_cursos["nu_ano_censo"].astype(int) == ano)]
    df_i = df_ies[(df_ies["sg_uf_ies"] == uf) & (df_ies["no_municipio_ies"] == mun) & (df_ies["nu_ano_censo"].astype(int) == ano)]

    if df_c.empty and df_i.empty:
        kpi_zero = html.Div([
            html.P("0", style={"fontSize": 26, "fontWeight": 700, "color": "#fff", "margin": 0}),
            html.P("IES no Município", style={"fontSize": 10, "color": "#BEE3F8", "margin": 0,
                                              "textTransform": "uppercase", "letterSpacing": "0.05em"}),
        ])
        return html.P("Nenhum dado encontrado para a combinação selecionada.",
                      style={"color": "#e53e3e"}), kpi_zero

    # Agrupa dados de cursos por IES (base: todos que têm cursos no município)
    ies_cursos = df_c.groupby("co_ies").agg(
        total_cursos=("no_curso", "nunique"),      # cursos únicos por nome
        total_mat=("qt_mat", "sum"),
        total_ing=("qt_ing", "sum"),
        total_conc=("qt_conc", "sum"),
    ).reset_index()

    # Dados cadastrais de todas as IES do ano (sem filtrar por município de sede)
    ies_info_global = df_ies[df_ies["nu_ano_censo"].astype(int) == ano].groupby("co_ies").agg(
        nome_ies=("no_ies", "first"),
        sigla_ies=("sg_ies", "first"),
        rede=("tp_rede", "first"),
        categoria=("tp_categoria_administrativa", "first"),
        no_municipio_sede=("no_municipio_ies", "first"),
        sg_uf_sede=("sg_uf_ies", "first"),
        docentes=("qt_doc_exe", "sum"),
    ).reset_index()

    # Merge: parte dos cursos (todas as IES que atuam no município)
    # e enriquece com dados cadastrais — inclui EAD de outras sedes
    tabela = pd.merge(ies_cursos, ies_info_global, on="co_ies", how="left")

    # IES sem cadastro na tabela ies (raro) recebem fallback
    tabela["nome_ies"] = tabela["nome_ies"].fillna("IES " + tabela["co_ies"].astype(str))
    tabela["sigla_ies"] = tabela["sigla_ies"].fillna("")
    tabela["rede"] = tabela["rede"].fillna("-")
    tabela["categoria"] = tabela["categoria"].fillna("-")
    tabela["no_municipio_sede"] = tabela["no_municipio_sede"].fillna("-")
    tabela["sg_uf_sede"] = tabela["sg_uf_sede"].fillna("-")

    tabela["total_cursos"] = tabela["total_cursos"].fillna(0).astype(int)
    tabela["total_mat"] = tabela["total_mat"].fillna(0).astype(int)
    tabela["total_ing"] = tabela["total_ing"].fillna(0).astype(int)
    tabela["total_conc"] = tabela["total_conc"].fillna(0).astype(int)

    # Ordena pelas faculdades com mais alunos
    tabela = tabela.sort_values(by="total_mat", ascending=False)

    # Construção da Tabela HTML customizada com Botão de Ação
    header = html.Tr([
        html.Th("Ação", style={"padding": "10px", "textAlign": "center", "fontSize": 11, "borderBottom": "2px solid #e2e8f0"}),
        html.Th("Cód. IES", style={"padding": "10px", "fontSize": 11, "borderBottom": "2px solid #e2e8f0"}),
        html.Th("Nome da Faculdade / IES", style={"padding": "10px", "fontSize": 11, "borderBottom": "2px solid #e2e8f0"}),
        html.Th("Sede", style={"padding": "10px", "fontSize": 11, "borderBottom": "2px solid #e2e8f0"}),
        html.Th("Rede", style={"padding": "10px", "fontSize": 11, "borderBottom": "2px solid #e2e8f0"}),
        html.Th("Cursos Únicos", style={"padding": "10px", "textAlign": "right", "fontSize": 11, "borderBottom": "2px solid #e2e8f0"}),
        html.Th("Matrículas", style={"padding": "10px", "textAlign": "right", "fontSize": 11, "borderBottom": "2px solid #e2e8f0"}),
        html.Th("Ingressantes", style={"padding": "10px", "textAlign": "right", "fontSize": 11, "borderBottom": "2px solid #e2e8f0"}),
        html.Th("Concluintes", style={"padding": "10px", "textAlign": "right", "fontSize": 11, "borderBottom": "2px solid #e2e8f0"}),
    ])

    rows = []
    for _, r in tabela.iterrows():
        co_ies_val = str(r["co_ies"])
        is_selected = (str(ies_selecionada_co) == co_ies_val)

        bg = "#ebf8ff" if is_selected else "#ffffff"
        btn_text = "✓ Selecionada" if is_selected else "Ver Cursos e Alunos"
        btn_color = COR_VERDE if is_selected else COR_AZUL

        btn = html.Button(
            btn_text,
            id={"type": "btn-sel-ies", "co_ies": co_ies_val},
            n_clicks=0,
            style={
                "backgroundColor": btn_color, "color": "#fff", "border": "none",
                "borderRadius": 4, "padding": "6px 12px", "fontSize": 11,
                "fontWeight": 600, "cursor": "pointer"
            }
        )
        sigla_str = f" ({r['sigla_ies']})" if r.get('sigla_ies') and str(r['sigla_ies']) not in ("nan", "-", "") else ""
        nome_completo = f"{r['nome_ies']}{sigla_str}"
        sede_str = f"{r.get('no_municipio_sede', '-')} / {r.get('sg_uf_sede', '-')}"
        # Marca IES com sede fora do município selecionado
        if str(r.get('sg_uf_sede', uf)) != uf or str(r.get('no_municipio_sede', mun)) != mun:
            sede_str += " ★"

        rows.append(html.Tr([
            html.Td(btn, style={"padding": "8px", "textAlign": "center", "borderBottom": "1px solid #f0f0f0", "backgroundColor": bg}),
            html.Td(co_ies_val, style={"padding": "8px", "fontSize": 12, "borderBottom": "1px solid #f0f0f0", "backgroundColor": bg}),
            html.Td(nome_completo, style={"padding": "8px", "fontSize": 12, "fontWeight": 600, "borderBottom": "1px solid #f0f0f0", "backgroundColor": bg}),
            html.Td(sede_str, style={"padding": "8px", "fontSize": 11, "color": "#718096", "borderBottom": "1px solid #f0f0f0", "backgroundColor": bg}),
            html.Td(r["rede"], style={"padding": "8px", "fontSize": 12, "borderBottom": "1px solid #f0f0f0", "backgroundColor": bg}),
            html.Td(_fmt_mil(r["total_cursos"]), style={"padding": "8px", "textAlign": "right", "fontSize": 12, "borderBottom": "1px solid #f0f0f0", "backgroundColor": bg}),
            html.Td(_fmt_mil(r["total_mat"]), style={"padding": "8px", "textAlign": "right", "fontSize": 12, "fontWeight": 700, "color": COR_AZUL, "borderBottom": "1px solid #f0f0f0", "backgroundColor": bg}),
            html.Td(_fmt_mil(r["total_ing"]), style={"padding": "8px", "textAlign": "right", "fontSize": 12, "borderBottom": "1px solid #f0f0f0", "backgroundColor": bg}),
            html.Td(_fmt_mil(r["total_conc"]), style={"padding": "8px", "textAlign": "right", "fontSize": 12, "borderBottom": "1px solid #f0f0f0", "backgroundColor": bg}),
        ]))

    n_ies = len(tabela)
    kpi_ies = html.Div([
        html.P(f"{n_ies}", style={"fontSize": 26, "fontWeight": 700, "color": "#fff", "margin": 0}),
        html.P("IES no Município", style={"fontSize": 10, "color": "#BEE3F8", "margin": 0,
                                          "textTransform": "uppercase", "letterSpacing": "0.05em"}),
    ])

    if df_c.empty and df_i.empty:
        return html.P("Nenhum dado encontrado para a combinação selecionada.",
                      style={"color": "#e53e3e"}), kpi_ies

    return html.Table([html.Thead(header), html.Tbody(rows)],
                      style={"width": "100%", "borderCollapse": "collapse"}), kpi_ies


# 5. Renderizar o Painel Detalhado de Cursos e Alunos da Faculdade Selecionada
@app.callback(
    Output("mun-detalhe-ies-container", "children"),
    Input("mun-ies-selecionada", "data"),
    Input("mun-uf", "value"),
    Input("mun-municipio", "value"),
    Input("mun-ano", "value"),
)
def renderizar_detalhes_ies(co_ies, uf, mun, ano):
    if not co_ies:
        return html.Div(
            _card([
                html.P("Selecione uma faculdade na tabela acima para visualizar detalhadamente os cursos ofertados, matrículas e informações de alunos.",
                       style={"textAlign": "center", "color": "#718096", "margin": "12px 0", "fontStyle": "italic"})
            ]),
        )

    ano = int(ano)
    df_c = df_cursos[(df_cursos["co_ies"].astype(str) == str(co_ies)) & (df_cursos["sg_uf"] == uf) & (df_cursos["no_municipio"] == mun) & (df_cursos["nu_ano_censo"].astype(int) == ano)]
    df_i = df_ies[(df_ies["co_ies"].astype(str) == str(co_ies)) & (df_ies["nu_ano_censo"].astype(int) == ano)]

    nome_ies = df_i["no_ies"].iloc[0] if not df_i.empty else (df_c["co_ies"].iloc[0] if not df_c.empty else co_ies)
    sigla = f" ({df_i['sg_ies'].iloc[0]})" if not df_i.empty and pd.notna(df_i['sg_ies'].iloc[0]) else ""

    # Métricas de Alunos
    mat_total = int(df_c["qt_mat"].sum())
    ing_total = int(df_c["qt_ing"].sum())
    conc_total = int(df_c["qt_conc"].sum())
    vagas_total = int(df_c["qt_vg_total"].sum())

    mat_fem = int(df_c["qt_mat_fem"].sum())
    mat_masc = int(df_c["qt_mat_masc"].sum())
    prouni = int(df_c["qt_mat_prounii"].sum() + df_c["qt_mat_prounip"].sum())
    fies = int(df_c["qt_mat_fies"].sum())
    enem = int(df_c["qt_ing_enem"].sum())
    defic = int(df_c["qt_mat_deficiente"].sum() + df_c["qt_aluno_deficiente"].sum())

    # Docentes
    doc_exe = int(df_i["qt_doc_exe"].sum()) if not df_i.empty else 0
    doc_dout = int(df_i["qt_doc_ex_dout"].sum()) if not df_i.empty else 0
    doc_mest = int(df_i["qt_doc_ex_mest"].sum()) if not df_i.empty else 0

    # Tabela de Cursos — agrupa por nome+modalidade+grau para consolidar autorizações múltiplas
    df_cursos_tab = (
        df_c.groupby(["no_curso", "tp_modalidade_ensino", "tp_grau_academico",
                      "no_cine_area_geral"], dropna=False)
        .agg(
            Vagas=("qt_vg_total", "sum"),
            Ingressantes=("qt_ing", "sum"),
            Matrículas=("qt_mat", "sum"),
            Concluintes=("qt_conc", "sum"),
            FIES=("qt_mat_fies", "sum"),
            ProUni=("qt_mat_prounii", "sum"),
            Mat_Fem=("qt_mat_fem", "sum"),
            Mat_Masc=("qt_mat_masc", "sum"),
            ENEM=("qt_ing_enem", "sum"),
            Deficientes=("qt_mat_deficiente", "sum"),
        )
        .reset_index()
        .sort_values("Matrículas", ascending=False)
    )
    df_cursos_tab.columns = [
        "Curso", "Modalidade", "Grau", "Área",
        "Vagas", "Ingressantes", "Matrículas", "Concluintes",
        "FIES", "ProUni", "Mat. Fem.", "Mat. Masc.", "ENEM", "Deficientes"
    ]
    for col in ["Vagas", "Ingressantes", "Matrículas", "Concluintes",
                "FIES", "ProUni", "Mat. Fem.", "Mat. Masc.", "ENEM", "Deficientes"]:
        df_cursos_tab[col] = df_cursos_tab[col].apply(_fmt_mil)

    return html.Div([
        # Header da Faculdade Selecionada
        _card([
            html.Div([
                html.H3(f"{nome_ies}{sigla}", style={"fontSize": 18, "fontWeight": 700, "color": COR_HEADER, "margin": 0}),
                html.P(f"Município: {mun} - {uf} | Código IES: {co_ies}", style={"fontSize": 12, "color": "#718096", "margin": "4px 0 0 0"}),
            ]),
            
            html.Hr(style={"margin": "16px 0", "border": "none", "borderTop": "1px solid #e2e8f0"}),

            # Cards de resumo de alunos da Faculdade
            _titulo("Resumo do Corpo Discente e Docente da Faculdade"),
            html.Div([
                _kpi(_fmt_mil(mat_total), "Matrículas Ativas", COR_AZUL),
                _kpi(_fmt_mil(ing_total), "Ingressantes", COR_VERDE),
                _kpi(_fmt_mil(conc_total), "Concluintes", COR_ROXO),
                _kpi(_fmt_mil(vagas_total), "Vagas Ofertadas", COR_CINZA),
            ], style={"display": "flex", "gap": 12, "marginBottom": 12, "flexWrap": "wrap"}),

            # Detalhes de Alunos & Apoio
            html.Div([
                html.Div([
                    _titulo("Perfil dos Alunos (Gênero e Programas de Apoio)"),
                    html.Ul([
                        html.Li(f"Feminino: {_fmt_mil(mat_fem)} matrículas"),
                        html.Li(f"Masculino: {_fmt_mil(mat_masc)} matrículas"),
                        html.Li(f"Alunos Financiados pelo FIES: {_fmt_mil(fies)}"),
                        html.Li(f"Bolsistas ProUni: {_fmt_mil(prouni)}"),
                        html.Li(f"Ingressantes via ENEM: {_fmt_mil(enem)}"),
                        html.Li(f"Alunos PCD / Deficientes: {_fmt_mil(defic)}"),
                    ], style={"fontSize": 13, "lineHeight": "1.8", "color": "#2d3748", "paddingLeft": 20}),
                ], style={"flex": 1, "backgroundColor": "#f7fafc", "padding": 12, "borderRadius": 6}),

                html.Div([
                    _titulo("Corpo Docente (Nível da Instituição)"),
                    html.Ul([
                        html.Li(f"Docentes em Exercício: {_fmt_mil(doc_exe)}"),
                        html.Li(f"Docentes Doutores: {_fmt_mil(doc_dout)}"),
                        html.Li(f"Docentes Mestres: {_fmt_mil(doc_mest)}"),
                    ], style={"fontSize": 13, "lineHeight": "1.8", "color": "#2d3748", "paddingLeft": 20}),
                ], style={"flex": 1, "backgroundColor": "#f7fafc", "padding": 12, "borderRadius": 6}),
            ], style={"display": "flex", "gap": 12, "marginBottom": 16, "flexWrap": "wrap"}),

            # Tabela Completa de Cursos Ofertados por essa IES
            _titulo(f"Cursos Ofertados — {len(df_cursos_tab)} cursos (agrupados por nome/modalidade/grau)"),
            _nota("Cursos com mesmo nome mas autorizações distintas foram consolidados."),
            html.Div(style={"height": 8}),
            html.Div(_tabela_html(df_cursos_tab), style={"overflowX": "auto"}),
        ], shadow=True)
    ])


# ── Execução do Servidor ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)