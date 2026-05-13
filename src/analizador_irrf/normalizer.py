"""Funções de normalização de texto para nome de pessoas e colunas."""

import re
import unicodedata
from typing import Optional


def normalizar_texto(texto: str, manter_hifen: bool = False) -> str:
    """
    Remove acentos, converte para maiúsculas, remove caracteres especiais.
    Se manter_hifen=True, preserva o hífen (útil para nomes de colunas).
    """
    if not isinstance(texto, str) or not texto.strip():
        return ""

    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))

    if manter_hifen:
        limpo = re.sub(r"[^A-Z0-9 -]", "", sem_acento.upper())
    else:
        limpo = re.sub(r"[^A-Z0-9 ]", "", sem_acento.upper())

    return " ".join(limpo.split())


def normalizar_nome(nome: str, stopwords: Optional[set] = None) -> str:
    """Normaliza nome próprio: remove acentos, maiúsculas e stopwords."""
    limpo = normalizar_texto(nome)
    if not limpo:
        return ""

    if stopwords is None:
        stopwords = {"DE", "DA", "DO", "DOS", "DAS", "E", "O", "A", "OS", "AS"}

    tokens = [p for p in limpo.split() if p not in stopwords]
    return " ".join(tokens)


def normalizar_coluna(col: str) -> str:
    """Normaliza nome de coluna: uppercase, sem acentos, mantém hífen."""
    return normalizar_texto(col, manter_hifen=True)


def parse_stopwords(raw: Optional[str]) -> Optional[set]:
    """Converte string de stopwords (separadas por vírgula) em set."""
    if not raw:
        return None
    return {w.strip().upper() for w in raw.split(",") if w.strip()}
