"""Analisador IRRF — cruzamento de formulários com planilha mestra."""

import click

from .cli import parse_amostras, shared_options
from .matcher import processar
from .normalizer import normalizar_nome, normalizar_texto, normalizar_coluna
from .reader import ler_respostas, extrair_tipo_formulario
from .report import exibir_tabela, exibir_nao_encontrados


@click.command(name="analizador-irrf")
@shared_options
def main(
    output: str,
    respostas: str,
    amostras: str,
    coluna_nome: str,
    regex_codigo: str,
    stopwords: str,
    saida: str,
) -> None:
    """Cruza respostas de formulários com planilha mestra e exibe tabela.

    Detecta automaticamente os tipos de formulário (Sniff, Molho, Úmida, Seca)
    pelos nomes dos arquivos na pasta de respostas.
    """
    amostras_lista = parse_amostras(amostras)

    if not amostras_lista:
        raise click.UsageError("--amostras não pode estar vazio.")

    linhas = processar(
        caminho_output=output,
        pasta_respostas=respostas,
        amostras=amostras_lista,
        coluna_nome=coluna_nome,
        regex_codigo=regex_codigo,
        stopwords=stopwords,
        caminho_saida=saida,
    )

    exibir_tabela(linhas)


__all__ = [
    "main",
    "processar",
    "exibir_tabela",
    "exibir_nao_encontrados",
    "normalizar_nome",
    "normalizar_texto",
    "normalizar_coluna",
    "ler_respostas",
    "extrair_tipo_formulario",
]
