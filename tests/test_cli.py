"""Testes do parsing de flags dinamicos --<name> na CLI."""

from unittest import TestCase

from click import UsageError

from analizador_irrf.cli import coletar_arquivos_formulario


class TestColetarArquivosFormulario(TestCase):
    def assert_usage_error(self, args, msg_fragment=None):
        with self.assertRaises(UsageError) as ctx:
            coletar_arquivos_formulario(args)
        if msg_fragment is not None:
            self.assertIn(msg_fragment, str(ctx.exception))

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
        self.assert_usage_error([], "Informe ao menos um formulário")

    def test_nome_duplicado_erro(self):
        self.assert_usage_error(
            ["--sniff", "a.csv", "--sniff", "b.csv"],
            "Formulário duplicado: --sniff",
        )

    def test_flag_sem_valor_erro(self):
        self.assert_usage_error(["--sniff"], "Faltou o valor para o formulário --sniff.")

    def test_valor_comecando_com_hifen_erro(self):
        self.assert_usage_error(["--sniff", "-weird.csv"])

    def test_flag_curto_solto_erro(self):
        self.assert_usage_error(["-a"])

    def test_valor_vazio_erro(self):
        self.assert_usage_error(["--sniff="], "Valor vazio para o formulário --sniff.")

    def test_flag_vazio_erro(self):
        self.assert_usage_error(["--", "x.csv"])

    def test_valor_sem_flag_erro(self):
        self.assert_usage_error(["a.csv"], "Argumento inesperado: a.csv")

    def test_pendente_antes_de_valor_vazio(self):
        # o erro de valor pendente para --sniff vem antes do --faro-seco= vazio
        self.assert_usage_error(
            ["--sniff", "--faro-seco="], "Faltou o valor para o formulário --sniff."
        )
