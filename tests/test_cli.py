"""Testes do parsing de flags dinamicos --<name> na CLI."""

from unittest import TestCase

from click import UsageError

from analizador_irrf.cli import coletar_arquivos_formulario


class TestColetarArquivosFormulario(TestCase):
    def assert_usage_error(self, args):
        with self.assertRaises(UsageError):
            coletar_arquivos_formulario(args)

    def test_flag_simples(self):
        self.assertEqual(
            coletar_arquivos_formulario(["--sniff", "a.csv"]),
            {"SNIFF": "a.csv"},
        )

    def test_multiplos_flags_e_hifen_preservado(self):
        self.assertEqual(
            coletar_arquivos_formulario(
                ["--sniff", "a.csv", "--faro-seco", "b.csv"]
            ),
            {"SNIFF": "a.csv", "FARO-SECO": "b.csv"},
        )

    def test_sintaxe_com_igual(self):
        self.assertEqual(
            coletar_arquivos_formulario(["--faro-seco=b.csv"]),
            {"FARO-SECO": "b.csv"},
        )

    def test_sem_formularios_erro(self):
        self.assert_usage_error([])

    def test_nome_duplicado_erro(self):
        self.assert_usage_error(["--sniff", "a.csv", "--sniff", "b.csv"])

    def test_flag_sem_valor_erro(self):
        self.assert_usage_error(["--sniff"])

    def test_valor_comecando_com_hifen_erro(self):
        self.assert_usage_error(["--sniff", "-weird.csv"])

    def test_flag_curto_solto_erro(self):
        self.assert_usage_error(["-a"])

    def test_valor_vazio_erro(self):
        self.assert_usage_error(["--sniff="])

    def test_flag_vazio_erro(self):
        self.assert_usage_error(["--", "x.csv"])

    def test_valor_sem_flag_erro(self):
        self.assert_usage_error(["a.csv"])
