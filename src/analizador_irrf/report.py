"""Geração de relatório com tabela formatada usando Rich."""

from typing import List, Dict

from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()

# Ordem preferida de exibição das colunas de formulário
TIPO_ORDEM: List[str] = ["SNIFF", "MOLHO", "UMIDA", "SECA"]

# Mapeamento de tipos detectados → nomes amigáveis
TIPO_LABEL: Dict[str, str] = {
    "SNIFF": "Sniff",
    "MOLHO": "Molhada",
    "UMIDA": "Úmida",
    "SECA": "Seca",
}


def _ordenar_tipos(tipos: List[str]) -> List[str]:
    """Ordena os tipos conforme a ordem preferida de exibição."""
    ordem_idx = {t: i for i, t in enumerate(TIPO_ORDEM)}
    return sorted(tipos, key=lambda t: ordem_idx.get(t, 99))


def _status_icon(val) -> Text:
    """Retorna ícone formatado: ✓ (exato), ? (parcial), ✗ (ausente)."""
    if val is True:
        return Text("✓", style="bold green")
    if val == "partial":
        return Text("?", style="bold yellow")
    return Text("✗", style="dim red")


def _is_preenchido(val) -> bool:
    """Considera True e 'partial' como preenchido para fins de contagem."""
    return val is True or val == "partial"


def exibir_tabela(
    linhas: List[Dict],
    titulo: str = "Acompanhamento de Formulários",
) -> None:
    """
    Exibe uma tabela formatada no terminal com Rich.

    Parâmetros
    ----------
    linhas : list[dict]
        Cada dict deve ter: 'nome', 'amostra', e uma chave por formulário
        (ex: 'SNIFF', 'MOLHO', 'UMIDA', 'SECA') com valor bool.
    titulo : str
        Título da tabela.
    """
    if not linhas:
        console.print("[yellow]Nenhum dado para exibir.[/]")
        return

    # Detecta colunas de formulário e ordena
    tipos_raw = [k for k in linhas[0] if k not in ("nome", "amostra")]
    tipos = _ordenar_tipos(tipos_raw)

    table = Table(
        title=f"[bold blue]{titulo}[/]",
        header_style="bold cyan",
        border_style="blue",
        row_styles=["", "dim"],
    )

    table.add_column("Nome", style="white", no_wrap=False, width=32)
    table.add_column("Amostra", style="bold yellow", justify="center", width=8)

    for t in tipos:
        label = TIPO_LABEL.get(t, t)
        table.add_column(label, justify="center", width=10)

    for linha in linhas:
        nome = linha["nome"]
        amostra = linha["amostra"]
        valores = [_status_icon(linha.get(t, False)) for t in tipos]
        table.add_row(nome, amostra, *valores)

    console.print()
    console.print(table)
    console.print()

    # Resumo
    total = len(linhas)
    n_tipos = len(tipos)

    # Completos: todos os formulários com match exato (True, não "partial")
    completos = sum(
        1 for l in linhas if all(l.get(t, False) is True for t in tipos)
    )
    # Pendentes: falta pelo menos um formulário
    pendentes = sum(
        1 for l in linhas
        if not all(_is_preenchido(l.get(t, False)) for t in tipos)
    )
    # Incompletos mas com algo: tem todos preenchidos mas algum é parcial
    incertos = total - completos - pendentes

    total_celulas = sum(
        sum(1 for t in tipos if _is_preenchido(l.get(t, False)))
        for l in linhas
    )
    total_parciais = sum(
        sum(1 for t in tipos if l.get(t, False) == "partial")
        for l in linhas
    )

    console.print(
        f"[bold]Total:[/] {total} registros  |  "
        f"[bold green]Completos:[/] {completos}  |  "
        f"[bold yellow]Incerto:[/] {incertos}  |  "
        f"[bold red]Pendentes:[/] {pendentes}  |  "
        f"[bold]Células:[/] {total_celulas}/{total * n_tipos}"
        + (f" [yellow]({total_parciais} ?)[/]" if total_parciais else "")
    )


def exibir_nao_encontrados(nomes: List[str]) -> None:
    """Exibe lista de pessoas nas respostas mas não na planilha mestra."""
    if not nomes:
        return

    console.print()
    console.print(
        f"[yellow]⚠ Pessoas nas respostas mas NÃO na lista ({len(nomes)}):[/]"
    )
    for n in nomes:
        console.print(f"  [dim]• {n}[/]")
    console.print()
