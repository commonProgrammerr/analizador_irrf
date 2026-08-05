"""Motor de cruzamento: processa respostas e gera relatório de acompanhamento."""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import pandas as pd
from rich import print as rprint

from .normalizer import normalizar_nome, parse_stopwords
from .reader import ler_respostas


def processar(
    nomes: List[str],
    amostras: Optional[List[str]] = None,
    arquivos_formulario: Optional[Dict[str, str]] = None,
    regex_codigo: str = r"^\d+$",
    stopwords: Optional[str] = None,
    caminho_saida: Optional[str] = None,
) -> List[Dict]:
    """
    Cruza respostas com a lista de nomes e retorna dados para relatório.

    Parâmetros
    ----------
    nomes : list[str]
        Lista de nomes a serem conferidos.
    amostras : list[str] or None
        Códigos de amostra, ex: ['A1','A2','A3','A4'].
    arquivos_formulario : dict[str, str] or None
        Mapeamento {tipo: caminho_ou_uri}.
    regex_codigo : str
        Regex para validar códigos de amostra nas respostas.
    stopwords : str or None
        Stopwords separadas por vírgula.
    caminho_saida : str or None
        Caminho para salvar CSV.

    Retorna
    -------
    list[dict] com chaves 'nome', 'amostra', e chaves bool por formulário.
    """
    sw_set = parse_stopwords(stopwords)

    # --- Monta mapa de nomes normalizados ---
    nome_map: Dict[str, str] = {}
    for n in nomes:
        n_norm = normalizar_nome(n, sw_set)
        if n_norm:
            nome_map[n_norm] = n

    if not nome_map:
        rprint("[red]Nenhum nome válido fornecido.[/]")
        return []

    # --- Monta lista de (tipo, caminho) a partir do dict ---
    if not arquivos_formulario:
        rprint("[yellow]Nenhum arquivo de resposta fornecido.[/]")
        return []

    entradas = [(t, p) for t, p in arquivos_formulario.items() if p]
    if not entradas:
        rprint("[yellow]Nenhum arquivo de resposta fornecido.[/]")
        return []

    tipos_form = list(dict.fromkeys(t for t, _ in entradas))

    rprint(f"[bold]Amostras:[/] {amostras}")
    rprint(f"[bold]Formulários:[/] {tipos_form}")
    rprint(f"[bold]Arquivos:[/] {len(entradas)}")
    print()

    # --- Estrutura de resultado ---
    resultado: Dict[Tuple[str, str], Dict[str, bool]] = defaultdict(
        lambda: {t: False for t in tipos_form}
    )
    pessoas_sem_match: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)

    from .reader import resolver_arquivo

    for tipo, origem in entradas:
        rprint(f"  [dim]{origem}[/] → [bold]{tipo}[/]")

        try:
            caminho_local = resolver_arquivo(origem)
            df_resp = ler_respostas(caminho_local, regex_codigo)
        except Exception as e:
            rprint(f"  [red][ERRO][/] {e}")
            continue

        for _, r in df_resp.iterrows():
            nome_norm = r["nome_norm"]
            codigo = r["codigo"]

            if nome_norm in nome_map:
                resultado[(nome_norm, codigo)][tipo] = True
                continue

            matched = _match_parcial(nome_norm, nome_map)
            if matched:
                resultado[(matched, codigo)][tipo] = "partial"
                continue

            pessoas_sem_match[tipo].append((r["nome"], nome_norm, codigo))

    # --- Converte para lista de dicionários ---
    linhas = []
    for (nome_norm, codigo), forms in sorted(resultado.items()):
        nome_original = nome_map.get(nome_norm, nome_norm)
        linhas.append({"nome": nome_original, "amostra": codigo, **forms})

    # --- Relatório de pessoas não encontradas ---
    if pessoas_sem_match:
        print()
        todos = set()
        for items in pessoas_sem_match.values():
            for nome_original, _, _ in items:
                todos.add(nome_original.strip())
        rprint(
            f"[yellow]⚠ Pessoas nas respostas mas NÃO na lista "
            f"({len(todos)}):[/]"
        )
        for n in sorted(todos):
            rprint(f"  [dim]• {n}[/]")

    # --- Salva CSV se solicitado ---
    if caminho_saida:
        _salvar_csv(linhas, caminho_saida)

    return linhas



# ---------------------------------------------------------------------------
# Funções auxiliares internas
# ---------------------------------------------------------------------------


def _match_parcial(nome_norm: str, nome_map: Dict[str, str]) -> Optional[str]:
    """Tenta match por primeiro + último nome. Retorna chave normalizada ou None."""
    partes = nome_norm.split()
    if len(partes) < 2:
        return None
    p, u = partes[0], partes[-1]
    for chave in nome_map:
        if p in chave and u in chave:
            return chave
    return None


def _salvar_csv(linhas: List[Dict], caminho: str) -> None:
    """Salva resultado em CSV."""
    if not linhas:
        return
    df = pd.DataFrame(linhas)
    df.to_csv(caminho, index=False, encoding="utf-8")
    rprint(f"\n[dim]CSV salvo em: {caminho}[/]")
