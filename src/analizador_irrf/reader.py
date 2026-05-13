"""Leitura de arquivos CSV de resposta e detecção de tipo de formulário."""

import os
import re
import pandas as pd
from typing import Optional
from .normalizer import normalizar_coluna, normalizar_nome, normalizar_texto


# ---------------------------------------------------------------------------
# Leitura de arquivo de resposta
# ---------------------------------------------------------------------------


def ler_respostas(
    caminho_csv: str,
    regex_codigo: str = r"^A[1-4]$",
) -> pd.DataFrame:
    """
    Lê um CSV de respostas, extrai nome e código da amostra.

    Detecta automaticamente as colunas de nome e código.
    Filtra linhas que não correspondem ao regex de código.
    """
    try:
        df = pd.read_csv(caminho_csv, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(caminho_csv, encoding="latin-1")

    df.columns = df.columns.str.strip()

    # Detecta coluna de nome
    col_nome = _detectar_coluna(df, lambda cn: cn.startswith("NOME COMPLETO") or cn == "NOME")

    # Detecta coluna de código
    col_codigo = _detectar_coluna(df, lambda cn: cn == "CODIGO")

    if col_nome is None or col_codigo is None:
        raise ValueError(
            f"Colunas 'Nome' e/ou 'Código' não encontradas em {caminho_csv}. "
            f"Disponíveis: {list(df.columns)}"
        )

    df = df[[col_nome, col_codigo]].copy()
    df.columns = ["nome", "codigo"]

    # Remove vazios e linhas de teste
    df = df.dropna(subset=["nome"])
    df = df[~df["nome"].str.lower().str.startswith("teste")]
    df = df[df["codigo"].astype(str).str.upper().str.match(regex_codigo, na=False)]

    df["codigo"] = df["codigo"].str.upper().str.strip()
    df["nome_norm"] = df["nome"].apply(normalizar_nome)
    df = df[df["nome_norm"] != ""]

    return df


def _detectar_coluna(df: pd.DataFrame, predicate) -> Optional[str]:
    """Encontra a primeira coluna que satisfaz o predicado (após normalização)."""
    for c in df.columns:
        if predicate(normalizar_coluna(c)):
            return c
    return None


# ---------------------------------------------------------------------------
# Detecção do tipo de formulário pelo nome do arquivo
# ---------------------------------------------------------------------------


def extrair_tipo_formulario(nome_arquivo: str) -> Optional[str]:
    """
    Extrai o tipo de formulário do nome do arquivo.
    Ex: 'Acompanhamento - Sniff.csv' → 'SNIFF'
         'avaliacao_molho.csv'       → 'MOLHO'
         'resultados_umida.csv'      → 'UMIDA'
         'teste_seca_final.csv'      → 'SECA'
    """
    nome_norm = normalizar_texto(nome_arquivo, manter_hifen=True)

    for tipo in ["SNIFF", "MOLHO", "UMIDA", "SECA"]:
        if tipo in nome_norm:
            return tipo

    return None
