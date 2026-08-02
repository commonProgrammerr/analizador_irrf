"""Testes de ordenacao de colunas de formulario no relatorio."""

from unittest import TestCase

from analizador_irrf.report import _ordenar_tipos


class TestOrdenarTipos(TestCase):
    def test_conhecidos_primeiro_na_ordem_fixa(self):
        self.assertEqual(
            _ordenar_tipos(["FARO-SECO", "SNIFF", "MOLHO", "OUTRO"]),
            ["SNIFF", "MOLHO", "FARO-SECO", "OUTRO"],
        )

    def test_apenas_desconhecidos_mantem_ordem_de_aparicao(self):
        self.assertEqual(
            _ordenar_tipos(["X1", "FARO-SECO", "X2"]),
            ["X1", "FARO-SECO", "X2"],
        )
