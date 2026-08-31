"""Componentes de carregamento do Dashboard Educação Superior."""
from dash import dcc, html


def educ_spinner():
    """Spinner simples com animação de pulso."""
    return html.Div(
        [
            html.Div(className="educ-spinner__ring"),
            html.P("Carregando...", className="educ-spinner__label"),
        ],
        className="educ-spinner",
        role="status",
        **{"aria-label": "Carregando dados do Painel Educação Superior"},
    )


def educ_page_loading(children, **kwargs):
    """Loading global. Usa custom_spinner se a versão do Dash suportar."""
    try:
        import inspect
        params = inspect.signature(dcc.Loading).parameters
        loading_kwargs = {}
        if "custom_spinner" in params:
            loading_kwargs["custom_spinner"] = educ_spinner()
        if "overlay_style" in params:
            loading_kwargs["overlay_style"] = {"visibility": "visible"}
        if "parent_className" in params:
            loading_kwargs["parent_className"] = "educ-loading-wrapper"
        if "delay_show" in params:
            loading_kwargs["delay_show"] = 0
        if "delay_hide" in params:
            loading_kwargs["delay_hide"] = 500
        if not loading_kwargs.get("custom_spinner"):
            loading_kwargs["type"] = "default"
            loading_kwargs["color"] = "#1565C0"
        return dcc.Loading(children, **loading_kwargs, **kwargs)
    except Exception:
        return children
