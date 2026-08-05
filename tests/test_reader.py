"""Testes do leitor de respostas (ler_respostas)."""

import os
import tempfile
import unittest

from analizador_irrf.reader import ler_respostas


def _csv_temp(conteudo: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return path


class TestLerRespostas(unittest.TestCase):
    def tearDown(self):
        for path in getattr(self, "_tmp_paths", []):
            if os.path.exists(path):
                os.remove(path)

    def _write(self, conteudo: str) -> str:
        path = _csv_temp(conteudo)
        self._tmp_paths = getattr(self, "_tmp_paths", []) + [path]
        return path

    def test_codigo_numerico_e_convertido_para_string(self):
        # Google Sheets exporta códigos numéricos como int → não pode quebrar no .str
        path = self._write(
            "Nome Completo,Código\nMaria Silva,308\nJoão Pereira,126\n"
        )
        df = ler_respostas(path, regex_codigo=r"^\d+$")
        self.assertEqual(len(df), 2)
        self.assertEqual(df["codigo"].tolist(), ["308", "126"])

    def test_regex_filtra_codigo_numerico(self):
        path = self._write(
            "Nome Completo,Código\nMaria Silva,308\nJoão Pereira,A2\n"
        )
        df = ler_respostas(path, regex_codigo=r"^\d+$")
        self.assertEqual(df["codigo"].tolist(), ["308"])

    def test_codigo_texto_continua_funcionando(self):
        path = self._write(
            "Nome Completo,Código\nMaria Silva,A1\nJoão Pereira,A2\n"
        )
        df = ler_respostas(path, regex_codigo=r"^A[1-4]$")
        self.assertEqual(df["codigo"].tolist(), ["A1", "A2"])


if __name__ == "__main__":
    unittest.main()
