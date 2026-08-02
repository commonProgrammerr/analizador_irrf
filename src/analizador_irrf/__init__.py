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


@click.command(
    name="analizador-irrf",
    context_settings=dict(
        allow_extra_args=True,
        ignore_unknown_options=True,
    ),
)
@shared_options
@click.pass_context
def main(
    ctx,
    nomes: str,
    amostras: str,
    coluna_nome: str,
    regex_codigo: str,
    stopwords: str,
    saida: str,
) -> None:
    """Cruza respostas de formulários com a lista de nomes e exibe tabela.

    Forneça a lista de nomes via --nomes (arquivo .txt ou .csv)
    e os arquivos de resposta no formato --<nome> <caminho>, onde <nome>
    é o nome que aparecerá como coluna no relatório (ex: --sniff,
    --molhada, ou qualquer nome de sua escolha, como --faro-seco).

    Exemplo:
      irrf --nomes nomes.txt -a A1,A2 --sniff sniff.csv --faro-seco faro.csv
    """
    amostras_lista = parse_amostras(amostras)

    if not amostras_lista:
        raise click.UsageError("--amostras não pode estar vazio.")

    nomes_lista = ler_nomes(nomes, coluna_nome)

    arquivos_form = coletar_arquivos_formulario(ctx.args)

    linhas = processar(
        nomes=nomes_lista,
        amostras=amostras_lista,
        arquivos_formulario=arquivos_form,
        regex_codigo=regex_codigo,
        stopwords=stopwords,
        caminho_saida=saida,
    )

    exibir_tabela(linhas)


def web_main() -> None:
    """Inicia o servidor web (FastAPI + Uvicorn)."""
    import uvicorn
    from .web import app
    uvicorn.run(app, host="0.0.0.0", port=8000)


__all__ = [
    "main",
    "web_main",
    "processar",
    "exibir_tabela",
    "exibir_nao_encontrados",
    "normalizar_nome",
    "normalizar_texto",
    "normalizar_coluna",
    "ler_respostas",
    "extrair_tipo_formulario",
]
