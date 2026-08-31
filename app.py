"""Entry-point WSGI — Educação Superior Dashboard."""
from dash_educacao_superior import server  # noqa: F401  (expõe o Flask server para gunicorn)

if __name__ == "__main__":
    from dash_educacao_superior import app
    app.run(debug=False, host="0.0.0.0", port=8051)
