"""Interface de linha de comando (CLI) via Click + rich_click."""

from typing import Dict, List

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


def coletar_arquivos_formulario(args: List[str]) -> Dict[str, str]:
    """Coleta pares --<nome> <caminho> de ctx.args. Retorna {NOME: caminho}."""
    formularios: Dict[str, str] = {}
    pendente: str | None = None

    for token in args:
        if token.startswith("--"):
            if pendente is not None:
                raise click.UsageError(
                    f"Faltou o valor para o formulário --{pendente.lower()}."
                )
            nome, sep, valor = token[2:].partition("=")
            nome = nome.strip("-")
            if not nome:
                raise click.UsageError(f"Flag inválido: {token}")
            nome_norm = nome.upper()
            if nome_norm in formularios:
                raise click.UsageError(f"Formulário duplicado: --{nome}")
            if sep:
                if not valor:
                    raise click.UsageError(
                        f"Valor vazio para o formulário --{nome}."
                    )
                formularios[nome_norm] = valor
            else:
                pendente = nome_norm
            continue

        if token.startswith("-"):
            raise click.UsageError(f"Argumento inesperado: {token}")

        if pendente is None:
            raise click.UsageError(f"Argumento inesperado: {token}")

        formularios[pendente] = token
        pendente = None

    if pendente is not None:
        raise click.UsageError(
            f"Faltou o valor para o formulário --{pendente.lower()}."
        )
    if not formularios:
        raise click.UsageError(
            "Informe ao menos um formulário no formato --<nome> <arquivo>."
        )
    return formularios


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
