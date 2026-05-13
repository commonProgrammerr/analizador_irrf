"""Analisador IRRF — cruzamento de formulários com planilha mestra."""

import rich_click as click

from .cli import (
    parse_amostras,
    shared_options,
    coletar_arquivos_formulario,
    ler_nomes,
)
from .matcher import processar
from .normalizer import normalizar_nome, normalizar_texto, normalizar_coluna
from .reader import ler_respostas, extrair_tipo_formulario
from .report import exibir_tabela, exibir_nao_encontrados


@click.command(name="analizador-irrf")
@shared_options
def main(
    nomes: str,
    amostras: str,
    coluna_nome: str,
    regex_codigo: str,
    stopwords: str,
    saida: str,
    sniff: str = None,
    molhada: str = None,
    umida: str = None,
    seca: str = None,
) -> None:
    """Cruza respostas de formulários com a lista de nomes e exibe tabela.

    Forneça a lista de nomes via --nomes (arquivo .txt ou .csv)
    e os arquivos de resposta via --sniff, --molhada, --umida, --seca.
    """
    amostras_lista = parse_amostras(amostras)

    if not amostras_lista:
        raise click.UsageError("--amostras não pode estar vazio.")

    nomes_lista = ler_nomes(nomes, coluna_nome)

    arquivos_form = coletar_arquivos_formulario(
        sniff=sniff, molhada=molhada, umida=umida, seca=seca,
    )

    linhas = processar(
        nomes=nomes_lista,
        amostras=amostras_lista,
        arquivos_formulario=arquivos_form,
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
