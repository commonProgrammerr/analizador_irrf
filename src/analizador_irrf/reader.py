"""Leitura de arquivos CSV de resposta e detecção de tipo de formulário."""

import os
import re
import tempfile
import time
import urllib.parse
import urllib.request
import pandas as pd
from typing import Optional
from .normalizer import normalizar_coluna, normalizar_nome, normalizar_texto


# ---------------------------------------------------------------------------
# Download de URI / resolução de caminho
# ---------------------------------------------------------------------------

# Padrões de URI do Google Sheets
_PADRAO_GSHEET = re.compile(
    r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)"
)


def resolver_arquivo(origem: str) -> str:
    """
    Recebe um caminho local ou URI e retorna o caminho
    para um arquivo CSV local.

    - Se for Google Sheets, baixa o CSV exportado para o diretório atual.
    - Se for outra URI, faz download para arquivo temporário.
    - Se for caminho local, retorna direto.
    """
    if _eh_google_sheets(origem):
        return _baixar_google_sheets(origem)

    if origem.startswith(("http://", "https://", "ftp://")):
        return _baixar_uri(origem)

    if not os.path.isfile(origem):
        raise FileNotFoundError(f"Arquivo não encontrado: {origem}")

    return origem


def _eh_google_sheets(uri: str) -> bool:
    """Verifica se a URI é uma planilha do Google Sheets."""
    return bool(_PADRAO_GSHEET.search(uri))


def _extrair_id_gsheet(uri: str) -> Optional[str]:
    """Extrai o ID da planilha de uma URI do Google Sheets."""
    match = _PADRAO_GSHEET.search(uri)
    return match.group(1) if match else None


def _baixar_google_sheets(uri: str) -> str:
    """
    Converte uma URI do Google Sheets para CSV exportado e baixa
    para o diretório local com nome padronizado.
    """
    sheet_id = _extrair_id_gsheet(uri)
    if not sheet_id:
        raise ValueError(f"Não foi possível extrair o ID da planilha: {uri}")

    # URL de exportação CSV
    export_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    )

    # Extrai um nome amigável do URI original (ex: "Relatorio" ou o último segmento)
    nome_base = _extrair_nome_planilha(uri, sheet_id)

    # Salva no diretório atual com timestamp
    ts = time.strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(os.getcwd(), f"{nome_base}_{ts}.csv")

    print(f"  [dim]Google Sheets:[/] {sheet_id}")
    print(f"  [dim]Baixando:[/] {export_url}")

    try:
        urllib.request.urlretrieve(export_url, destino)
    except Exception as e:
        raise RuntimeError(f"Falha ao baixar Google Sheets {sheet_id}: {e}") from e

    print(f"  [green]Salvo em:[/] {destino}")
    return destino


def _extrair_nome_planilha(uri: str, sheet_id: str) -> str:
    """
    Tenta extrair um nome amigável da URI.
    Fallback: usa os primeiros 8 caracteres do sheet_id.
    """
    # Tenta usar o nome do arquivo se for uma URI com caminho
    parsed = urllib.parse.urlparse(uri)
    path_parts = [p for p in parsed.path.split("/") if p]
    # Procura por algo após o ID que possa ser um nome
    if sheet_id in path_parts:
        idx = path_parts.index(sheet_id)
        if idx + 1 < len(path_parts):
            nome = path_parts[idx + 1]
            if nome not in ("edit", "export", "view"):
                return nome.replace(" ", "_").lower()[:40]

    return sheet_id[:8]


def _baixar_uri(uri: str) -> str:
    """Faz download de uma URI genérica e salva em um arquivo temporário."""
    print(f"  [dim]Baixando:[/] {uri}")
    try:
        with urllib.request.urlopen(uri, timeout=30) as resp:
            dados = resp.read()
    except Exception as e:
        raise RuntimeError(f"Falha ao baixar {uri}: {e}") from e

    suffix = ".csv"
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=suffix, delete=False
    ) as tmp:
        tmp.write(dados)
        return tmp.name
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
