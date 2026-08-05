"""
Web app — Interface web para o Analisador IRRF.

Endpoints:
  GET  /           → formulário HTML para submeter os dados
  POST /submit     → JSON/aplicativo, roda o analisador, retorna resultado
  GET  /resultado  → tabela HTML gerada pelo Rich
"""

import os

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from .cli import parse_amostras
from .matcher import processar
from .reader import _baixar_google_sheets, _eh_google_sheets, resolver_arquivo
from .report import exibir_tabela_html

app = FastAPI(title="Analisador IRRF")


# ---------------------------------------------------------------------------
# Página inicial — formulário
# ---------------------------------------------------------------------------

_BASE = os.path.dirname(os.path.abspath(__file__))
_FORM_PATH = os.path.join(_BASE, "templates", "form.html")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(_FORM_PATH, encoding="utf-8") as f:
        return HTMLResponse(f.read())


# ---------------------------------------------------------------------------
# Submit — roda o analisador e guarda o resultado em memória
# ---------------------------------------------------------------------------

_ultimo_resultado: str | None = None


@app.post("/submit")
async def submit(
    nomes: str = Form(...),
    amostras: str = Form(...),
    sniff: str = Form(""),
    molhada: str = Form(""),
    umida: str = Form(""),
    seca: str = Form(""),
    coluna_nome: str = Form("Nome"),
    regex_codigo: str = Form(r"^\d+$"),
    stopwords: str = Form("de,da,do,dos,das,e,o,a,os,as"),
):
    global _ultimo_resultado

    # Processa nomes (textarea → lista)
    nomes_lista = [n.strip() for n in nomes.strip().split("\n") if n.strip()]
    if not nomes_lista:
        return {"erro": "Lista de nomes vazia."}

    amostras_lista = parse_amostras(amostras)
    if not amostras_lista:
        return {"erro": "--amostras não pode estar vazio."}

    # Coleta apenas os formulários que foram preenchidos
    form_args = {}
    for nome_campo, chave in [
        ("sniff", "SNIFF"),
        ("molhada", "MOLHO"),
        ("umida", "UMIDA"),
        ("seca", "SECA"),
    ]:
        val = locals()[nome_campo]
        if val and val.strip():
            entrada = val.strip()
            if _eh_google_sheets(entrada):
                entrada = _baixar_google_sheets(entrada)
            form_args[chave] = entrada

    if not form_args:
        return {"erro": "Informe ao menos um formulário (sniff/molhada/umida/seca)."}

    try:
        linhas = processar(
            nomes=nomes_lista,
            amostras=amostras_lista,
            arquivos_formulario=form_args,
            regex_codigo=regex_codigo,
            stopwords=stopwords if stopwords.strip() else None,
        )
    except Exception as e:
        return {"erro": str(e)}

    # Gera HTML e guarda
    _ultimo_resultado = exibir_tabela_html(linhas)

    return {"redirect": "/resultado", "total": len(linhas)}


# ---------------------------------------------------------------------------
# Resultado — tabela HTML
# ---------------------------------------------------------------------------


@app.get("/resultado", response_class=HTMLResponse)
async def resultado():
    if not _ultimo_resultado:
        return HTMLResponse("<p>Nenhum resultado ainda. <a href='/'>Voltar</a></p>")
    return HTMLResponse(_ultimo_resultado)
