"""Interface de linha de comando (CLI) via Click + rich_click."""

from typing import List

import click
import rich_click


def parse_amostras(raw: str) -> List[str]:
    """Converte string de amostras (A1,A2,A3) em lista."""
    return [a.strip().upper() for a in raw.split(",") if a.strip()]


# Opções compartilhadas
_opt_nomes = click.option(
    "--nomes", required=True,
    help="Arquivo com nomes a conferir. "
         "Aceita .txt (um nome por linha) ou .csv (use --coluna-nome para indicar a coluna)",
)
_opt_amostras = click.option(
    "-a", "--amostras", required=True,
    help="Códigos de amostra separados por vírgula (ex: A1,A2,A3,A4)",
)
_opt_coluna_nome = click.option(
    "-n", "--coluna-nome", default="Nome", show_default=True,
    help="Coluna com o nome da pessoa (quando --nomes é um CSV)",
)
_opt_regex_codigo = click.option(
    "--regex-codigo", default=r"^A[1-4]$", show_default=True,
    help="Regex para validar códigos de amostra nas respostas",
)
_opt_stopwords = click.option(
    "--stopwords", default="de,da,do,dos,das,e,o,a,os,as", show_default=True,
    help="Stopwords separadas por vírgula",
)
_opt_saida = click.option(
    "-s", "--saida", default=None,
    help="Arquivo CSV de saída",
)
_opts_form = [
    click.option(
        f"--{tipo}",
        default=None,
        help=f"Arquivo ou URI do formulário {label}",
    )
    for tipo, label in [
        ("sniff", "Sniff"),
        ("molhada", "Molhada"),
        ("umida", "Úmida"),
        ("seca", "Seca"),
    ]
]


def shared_options(func):
    """Agrupa todas as opções CLI."""
    for opt in reversed([
        _opt_nomes, _opt_amostras,
        _opt_coluna_nome, _opt_regex_codigo, _opt_stopwords, _opt_saida,
    ]):
        func = opt(func)
    for opt in _opts_form:
        func = opt(func)
    return func


def coletar_arquivos_formulario(
    sniff: str = None,
    molhada: str = None,
    umida: str = None,
    seca: str = None,
) -> dict:
    """Coleta os caminhos/URIs dos formulários. Retorna {tipo: caminho}."""
    formas = {"SNIFF": sniff, "MOLHO": molhada, "UMIDA": umida, "SECA": seca}
    explicitos = {t: p for t, p in formas.items() if p is not None}

    if not explicitos:
        raise click.UsageError(
            "Informe ao menos um de "
            "--sniff/--molhada/--umida/--seca."
        )

    return explicitos


def ler_nomes(caminho: str, coluna: str = "Nome") -> List[str]:
    """Lê nomes de um arquivo .txt (um por linha) ou .csv (aplica --coluna-nome).
    Se for uma URI do Google Sheets, baixa o CSV automaticamente.
    """
    from .reader import _eh_google_sheets, _baixar_google_sheets

    # Google Sheets: baixa CSV primeiro
    if _eh_google_sheets(caminho):
        caminho = _baixar_google_sheets(caminho)

    # CSV: lê coluna específica
    if caminho.lower().endswith(".csv"):
        import pandas as pd
        df = pd.read_csv(caminho, encoding="utf-8")
        df.columns = df.columns.str.strip()
        if coluna not in df.columns:
            raise click.UsageError(
                f"Coluna '{coluna}' não encontrada no CSV. "
                f"Disponíveis: {list(df.columns)}"
            )
        return df[coluna].dropna().str.strip().tolist()

    # TXT: um nome por linha
    with open(caminho, encoding="utf-8") as f:
        nomes = [line.strip() for line in f if line.strip()]

    if not nomes:
        raise click.UsageError(f"Nenhum nome encontrado em {caminho}.")

    return nomes
