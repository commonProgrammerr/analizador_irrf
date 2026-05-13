"""Interface de linha de comando (CLI) via Click."""

from typing import List

import click


def parse_amostras(raw: str) -> List[str]:
    """Converte string de amostras (A1,A2,A3) em lista."""
    return [a.strip().upper() for a in raw.split(",") if a.strip()]


# Opções compartilhadas como decorators reutilizáveis
_opt_output = click.option(
    "-o", "--output", required=True,
    help="CSV da planilha mestra (ex: output.csv)",
)
_opt_respostas = click.option(
    "-r", "--respostas", required=True,
    help="Pasta com CSVs de resposta ou arquivo individual",
)
_opt_amostras = click.option(
    "-a", "--amostras", required=True,
    help="Códigos de amostra separados por vírgula (ex: A1,A2,A3,A4)",
)
_opt_coluna_nome = click.option(
    "-n", "--coluna-nome", default="Nome", show_default=True,
    help="Coluna com o nome da pessoa na planilha mestra",
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
    help="Arquivo CSV de saída (padrão: somente tabela no terminal)",
)


def shared_options(func):
    """Agrupa todas as opções CLI compartilhadas."""
    for opt in reversed([
        _opt_output, _opt_respostas, _opt_amostras,
        _opt_coluna_nome, _opt_regex_codigo, _opt_stopwords, _opt_saida,
    ]):
        func = opt(func)
    return func
