"""Motor de cruzamento: processa respostas e gera relatório de acompanhamento."""

import os
import sys
import pandas as pd
from collections import defaultdict
from glob import glob
from typing import Dict, List, Optional, Tuple

from .normalizer import normalizar_nome, normalizar_coluna, parse_stopwords
from .reader import ler_respostas, extrair_tipo_formulario


def processar(
    caminho_output: str,
    pasta_respostas: str,
    amostras: List[str],
    coluna_nome: str = "Nome",
    regex_codigo: str = r"^A[1-4]$",
    stopwords: Optional[str] = None,
    caminho_saida: Optional[str] = None,
) -> List[Dict]:
    """
    Cruza respostas com a planilha mestra e retorna dados para relatório.

    Retorna
    -------
    list[dict] com chaves 'nome', 'amostra', e uma chave bool por formulário.
    """
    sw_set = parse_stopwords(stopwords)

    # --- Carrega planilha mestra ---
    df_mestra = pd.read_csv(caminho_output, encoding="utf-8")
    df_mestra.columns = df_mestra.columns.str.strip()

    if coluna_nome not in df_mestra.columns:
        raise ValueError(
            f"Coluna '{coluna_nome}' não encontrada. "
            f"Disponíveis: {list(df_mestra.columns)}"
        )

    # Normaliza nomes da lista mestra
    df_mestra["_nome_norm"] = df_mestra[coluna_nome].apply(
        lambda n: normalizar_nome(n, sw_set)
    )
    # Mapa: nome_normalizado → nome_original
    nome_map = dict(zip(df_mestra["_nome_norm"], df_mestra[coluna_nome]))

    # --- Descobre arquivos e tipos ---
    arquivos_csv = _listar_arquivos(pasta_respostas)
    tipos_form = _detectar_tipos(arquivos_csv)

    if not arquivos_csv:
        print("[AVISO] Nenhum CSV encontrado.", file=sys.stderr)
        return []

    print(f"[bold]Amostras:[/] {amostras}")
    print(f"[bold]Formulários:[/] {tipos_form}")
    print(f"[bold]Arquivos:[/] {len(arquivos_csv)}\n")

    # --- Estrutura de resultado: {(nome_norm, codigo): {tipo: bool}} ---
    resultado: Dict[Tuple[str, str], Dict[str, bool]] = defaultdict(
        lambda: {t: False for t in tipos_form}
    )

    pessoas_sem_match: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)

    for caminho in arquivos_csv:
        nome_arquivo = os.path.basename(caminho)
        tipo = extrair_tipo_formulario(nome_arquivo)
        if tipo is None:
            tipo = os.path.splitext(nome_arquivo)[0].upper()

        print(f"  [dim]{nome_arquivo}[/] → [bold]{tipo}[/]")

        try:
            df_resp = ler_respostas(caminho, regex_codigo)
        except Exception as e:
            print(f"  [red][ERRO][/] {e}")
            continue

        for _, r in df_resp.iterrows():
            nome_norm = r["nome_norm"]
            codigo = r["codigo"]

            # Match exato
            if nome_norm in nome_map:
                resultado[(nome_norm, codigo)][tipo] = True
                continue

            # Match parcial: primeiro + último nome (incerto → "partial")
            matched = _match_parcial(nome_norm, nome_map)
            if matched:
                resultado[(matched, codigo)][tipo] = "partial"
                continue

            pessoas_sem_match[tipo].append((r["nome"], nome_norm, codigo))

    # --- Converte para lista de dicionários (formato da tabela) ---
    linhas = []
    # Ordena por nome original, depois por código
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
        print(
            f"[yellow]⚠ Pessoas nas respostas mas NÃO na lista "
            f"({len(todos)}):[/]"
        )
        for n in sorted(todos):
            print(f"  [dim]• {n}[/]")

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


def _listar_arquivos(pasta: str) -> List[str]:
    """Lista CSVs de uma pasta ou retorna arquivo único."""
    if os.path.isdir(pasta):
        return sorted(glob(os.path.join(pasta, "*.csv")))
    return [pasta]


def _detectar_tipos(arquivos: List[str]) -> List[str]:
    """Detecta tipos de formulário pelos nomes dos arquivos."""
    tipos = []
    for arq in arquivos:
        tipo = extrair_tipo_formulario(os.path.basename(arq))
        if tipo and tipo not in tipos:
            tipos.append(tipo)

    if not tipos:
        tipos = [os.path.splitext(os.path.basename(a))[0].upper() for a in arquivos]

    return tipos


def _salvar_csv(linhas: List[Dict], caminho: str) -> None:
    """Salva resultado em CSV no formato Nome, Amostra, Form1, Form2, ..."""
    if not linhas:
        return
    df = pd.DataFrame(linhas)
    df.to_csv(caminho, index=False, encoding="utf-8")
    print(f"\n[dim]CSV salvo em: {caminho}[/]")



def _log_aviso(msg: str):
    print(f"[AVISO] {msg}", file=sys.stderr)


def _imprimir_relatorio(
    df, colunas_form, coluna_nome, matches, nao_encontradas,
    n_amostras, n_tipos,
):
    sep = "=" * 60
    print(f"\n{sep}\nRELATÓRIO\n{sep}")
    print(f"Matches: {matches}")

    if nao_encontradas:
        nomes = sorted(set(n.strip() for n, _, _ in nao_encontradas))
        print(f"\nPessoas nas respostas mas NÃO na lista ({len(nomes)}):")
        for n in nomes:
            print(f"  • {n}")

    print(f"\n{sep}\nRESUMO POR PESSOA\n{sep}")
    total_possivel = n_amostras * n_tipos
    for _, row in df.iterrows():
        n = sum(row[colunas_form].astype(bool))
        status = "COMPLETO" if row["FINAL"] else f"{n}/{total_possivel}"
        print(f"  {row[coluna_nome]:<40s} {status}")

    total = len(df)
    completos = df["FINAL"].sum()
    print(f"\nTotal: {total} | Completos: {completos} | Pendentes: {total - completos}")
