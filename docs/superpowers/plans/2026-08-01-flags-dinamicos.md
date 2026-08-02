# Flags Dinâmicos `--<name>` na CLI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir os 4 flags fixos (`--sniff/--molhada/--umida/--seca`) por flags arbitrários `--<name> <arquivo>`, onde `<name>` vira a coluna no relatório.

**Architecture:** Usar `context_settings=dict(allow_extra_args=True, ignore_unknown_options=True)` no comando click: opções conhecidas continuam consumidas normalmente; tudo que não casa é coletado em `ctx.args`. Uma função pura `coletar_arquivos_formulario(args: List[str]) -> Dict[str, str]` converte os pares `--name valor` / `--name=valor` no dict `{NOME: caminho}` (nome em maiúsculas, preservando hífens). O resto do pipeline (`matcher.py`) já é genérico e não muda. Rótulos amigáveis dos 4 nomes conhecidos continuam no `report.py` via `TIPO_LABEL` (fallback já existente cobre nomes genéricos).

**Tech Stack:** Python 3.12, click 8 + rich_click (instalados no venv), stdlib `unittest` (sem pytest no venv — não adicionar dependências), pandas (usado nos fixtures de verificação).

**Spec:** `docs/superpowers/specs/2026-08-01-flags-dinamicos-design.md`

**Contexto de ambiente (já verificado):**
- Instalação é editable → `.venv/bin/irrf` executa o source atual; testes importam código vivo.
- Rodar testes: `.venv/bin/python -m unittest discover -s tests -v` (cwd = raiz do repo).
- Empiricamente comprovado: com as `context_settings` acima, `ctx.args` coleta `['--sniff', 'a.csv', '--faro-seco=b.csv']` e opções conhecidas parseiam normalmente mesmo depois de flags desconhecidos.

---

### Task 1: Testes TDD para `coletar_arquivos_formulario` e ordenação de tipos

**Files:**
- Create: `tests/test_cli.py`
- Create: `tests/test_report.py`
- Modify: `src/analizador_irrf/cli.py` (nova implementação da função + import `Dict`)

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_cli.py`:

```python
"""Testes do parsing de flags dinâmicos --<name> na CLI."""

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
```

`tests/test_report.py` (trava a promessa da spec: conhecidos primeiro na ordem fixa, desconhecidos depois na ordem de aparição):

```python
"""Testes de ordenação de colunas de formulário no relatório."""

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
            _ordenar_tipos(["FARO-SECO", "X1", "FARO-SECO"]),
            ["FARO-SECO", "X1", "FARO-SECO"],
        )
```

- [ ] **Step 2: Rodar e verificar que falham**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: FAILs em `test_flag_simples`, `test_multiplos_flags_e_hifen_preservado`, `test_sintaxe_com_igual`, `test_valor_sem_flag_erro` — a assinatura antiga (`coletar_arquivos_formulario(sniff=None, molhada=None, umida=None, seca=None)`) recebe a lista no lugar de `sniff` e retorna `{"SNIFF": ["--sniff", "a.csv"]}`. Os demais testes podem passar — ok.

- [ ] **Step 3: Implementar a nova função em `cli.py`**

Em `src/analizador_irrf/cli.py`:
1. Trocar o import da linha 3: `from typing import List` → `from typing import Dict, List`
2. Substituir a função `coletar_arquivos_formulario` inteira (linhas 67-83 atuais) por:

```python
def coletar_arquivos_formulario(args: List[str]) -> Dict[str, str]:
    """Coleta pares --<nome> <caminho> de ctx.args. Retorna {NOME: caminho}."""
    formularios: Dict[str, str] = {}
    pendente: str | None = None

    for token in args:
        if token.startswith("--"):
            if pendente is not None:
                raise click.UsageError(
                    f"Faltou o valor para o formulário --{pendente.lower()}."
                )
            nome, sep, valor = token[2:].partition("=")
            nome = nome.strip("-")
            if not nome:
                raise click.UsageError(f"Flag inválido: {token}")
            nome_norm = nome.upper()
            if nome_norm in formularios:
                raise click.UsageError(f"Formulário duplicado: --{nome}")
            if sep:
                if not valor:
                    raise click.UsageError(
                        f"Valor vazio para o formulário --{nome}."
                    )
                formularios[nome_norm] = valor
            else:
                pendente = nome_norm
            continue

        if token.startswith("-"):
            raise click.UsageError(f"Argumento inesperado: {token}")

        if pendente is None:
            raise click.UsageError(f"Argumento inesperado: {token}")

        formularios[pendente] = token
        pendente = None

    if pendente is not None:
        raise click.UsageError(
            f"Faltou o valor para o formulário --{pendente.lower()}."
        )
    if not formularios:
        raise click.UsageError(
            "Informe ao menos um formulário no formato --<nome> <arquivo>."
        )
    return formularios
```

- [ ] **Step 4: Rodar e verificar que passam**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: `Ran 13 tests` — OK. (11 do test_cli + 2 do test_report)

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli.py tests/test_report.py src/analizador_irrf/cli.py
git commit -m "test: parsing de flags dinâmicos --<name> e ordenação de tipos
cobertura TDD para coletar_arquivos_formulario

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Wire a CLI — remover `_opts_form`, `context_settings`, `pass_context`

**Files:**
- Modify: `src/analizador_irrf/cli.py` (remover `_opts_form` e o loop em `shared_options`)
- Modify: `src/analizador_irrf/__init__.py` (decorators, assinatura de `main`, docstring, chamada)

- [ ] **Step 1: Remover `_opts_form` de `cli.py`**

Apagar o bloco inteiro (linhas 40-52 atuais):

```python
_opts_form = [
    click.option(
        f"--{tipo}",
        default=None,
        help=f"Arquivo ou URI do formulário {label}",
    )
    for tipo, label in [
        ("sniff", "Sniff"),
        ("molhada", "Molhada"),
        ("umida", "Úmida"),
        ("seca", "Seca"),
    ]
]
```

- [ ] **Step 2: Remover o loop de `_opts_form` em `shared_options`**

Em `src/analizador_irrf/cli.py`, a função `shared_options` (linhas 55-64) fica:

```python
def shared_options(func):
    """Agrupa todas as opções CLI."""
    for opt in reversed([
        _opt_nomes, _opt_amostras,
        _opt_coluna_nome, _opt_regex_codigo, _opt_stopwords, _opt_saida,
    ]):
        func = opt(func)
    return func
```

(apenas remover as linhas 62-63: `for opt in _opts_form:` e `func = opt(func)`)

- [ ] **Step 3: Atualizar `main()` em `__init__.py`**

Em `src/analizador_irrf/__init__.py` (linhas 17-56 atuais), trocar o bloco do comando por:

```python
@click.command(
    name="analizador-irrf",
    context_settings=dict(
        allow_extra_args=True,
        ignore_unknown_options=True,
    ),
)
@shared_options
@click.pass_context
def main(
    ctx,
    nomes: str,
    amostras: str,
    coluna_nome: str,
    regex_codigo: str,
    stopwords: str,
    saida: str,
) -> None:
    """Cruza respostas de formulários com a lista de nomes e exibe tabela.

    Forneça a lista de nomes via --nomes (arquivo .txt ou .csv)
    e os arquivos de resposta no formato --<nome> <caminho>, onde <nome>
    é o nome que aparecerá como coluna no relatório (ex: --sniff,
    --molhada, ou qualquer nome de sua escolha, como --faro-seco).

    Exemplo:
      irrf --nomes nomes.txt -a A1,A2 --sniff sniff.csv --faro-seco faro.csv
    """
    amostras_lista = parse_amostras(amostras)

    if not amostras_lista:
        raise click.UsageError("--amostras não pode estar vazio.")

    nomes_lista = ler_nomes(nomes, coluna_nome)

    arquivos_form = coletar_arquivos_formulario(ctx.args)

    linhas = processar(
        nomes=nomes_lista,
        amostras=amostras_lista,
        arquivos_formulario=arquivos_form,
        regex_codigo=regex_codigo,
        stopwords=stopwords,
        caminho_saida=saida,
    )

    exibir_tabela(linhas)
```

Notas: `ctx` fica sem anotação de tipo (rich_click não expõe `Context` com segurança); decorator `@click.pass_context` fica **abaixo** de `@shared_options` para `ctx` virar primeiro parâmetro.

- [ ] **Step 4: Rodar os testes**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: `Ran 13 tests` — OK (nada regrediu).

- [ ] **Step 5: Commit**

```bash
git add src/analizador_irrf/cli.py src/analizador_irrf/__init__.py
git commit -m "feat: flags dinâmicos --<name> substituem --sniff/--molhada/--umida/--seca

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Remover código morto `extrair_tipo_formulario`

**Files:**
- Modify: `src/analizador_irrf/reader.py`
- Modify: `src/analizador_irrf/__init__.py`

- [ ] **Step 1: Remover a função de `reader.py`**

Apagar de `src/analizador_irrf/reader.py` o bloco final (linhas 178-198):

```python
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
```

Também limpar o import não usado na linha 11:
`from .normalizer import normalizar_coluna, normalizar_nome, normalizar_texto` → `from .normalizer import normalizar_coluna, normalizar_nome`

(verifique se `normalizar_texto` não é usado em outro ponto do arquivo — `grep normalizar_texto src/analizador_irrf/reader.py` deve retornar só a linha do import após a remoção)

- [ ] **Step 2: Remover import/export em `__init__.py`**

1. Linha 13: `from .reader import ler_respostas, extrair_tipo_formulario` → `from .reader import ler_respostas`
2. Remover `"extrair_tipo_formulario",` do `__all__` (linha 76).

- [ ] **Step 3: Rodar testes e smoke check**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: `Ran 13 tests` — OK.

Run: `.venv/bin/irrf --help`
Expected: comando carrega sem erro (imports limpos) e mostra o novo docstring com `--<nome> <caminho>`.

- [ ] **Step 4: Commit**

```bash
git add src/analizador_irrf/reader.py src/analizador_irrf/__init__.py
git commit -m "refactor: remove extrair_tipo_formulario (código morto com tipos fixos)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Verificação de integração (critérios de aceite da spec)

**Files:** nenhum (apenas execução)

- [ ] **Step 1: Criar fixtures em /tmp**

```bash
mkdir -p /tmp/irrf_fixture
printf 'Maria Silva\nJoão Pereira\nAna Souza\n' > /tmp/irrf_fixture/nomes.txt
printf 'NOME COMPLETO,CODIGO\nMaria Silva,A1\nJoão Pereira,A2\n' > /tmp/irrf_fixture/sniff.csv
printf 'NOME COMPLETO,CODIGO\nMaria Silva,A1\nAna Souza,A3\n' > /tmp/irrf_fixture/faro.csv
```

- [ ] **Step 2: Backward compat — `--sniff` sozinho**

Run: `.venv/bin/irrf --nomes /tmp/irrf_fixture/nomes.txt -a A1,A2,A3 --sniff /tmp/irrf_fixture/sniff.csv`
Expected: tabela com coluna **Sniff**; Maria Silva ✓, João Pereira ✓, Ana Souza ✗; resumo "Completos: 1, Pendentes: 2".

- [ ] **Step 3: Nome arbitrário — `--sniff` + `--faro-seco`**

Run: `.venv/bin/irrf --nomes /tmp/irrf_fixture/nomes.txt -a A1,A2,A3 --sniff /tmp/irrf_fixture/sniff.csv --faro-seco /tmp/irrf_fixture/faro.csv`
Expected: colunas **Sniff** e **FARO-SECO**; Maria Silva ✓✓, João Pereira ✓✗, Ana Souza ✗✓.

- [ ] **Step 4: Sintaxe `=`**

Run: `.venv/bin/irrf --nomes /tmp/irrf_fixture/nomes.txt -a A1,A2,A3 --faro-seco=/tmp/irrf_fixture/faro.csv`
Expected: coluna **FARO-SECO** apenas.

- [ ] **Step 5: Erros**

Run: `.venv/bin/irrf --nomes /tmp/irrf_fixture/nomes.txt -a A1`
Expected: `Error: Informe ao menos um formulário no formato --<nome> <arquivo>.`

Run: `.venv/bin/irrf --nomes /tmp/irrf_fixture/nomes.txt -a A1 --sniff /tmp/irrf_fixture/sniff.csv --sniff /tmp/irrf_fixture/faro.csv`
Expected: `Error: Formulário duplicado: --sniff`

Run: `.venv/bin/irrf --nomes /tmp/irrf_fixture/nomes.txt -a A1 --sniff`
Expected: `Error: Faltou o valor para o formulário --sniff.`

- [ ] **Step 6: Help**

Run: `.venv/bin/irrf --help`
Expected: rich_click renderiza; docstring mostra o exemplo `--sniff sniff.csv --faro-seco faro.csv`; as opções `--sniff/--molhada/--umida/--seca` não aparecem mais.

---

## Self-Review (checklist do plano × spec)

**Cobertura da spec:**
- Regras de parsing (flag, `=`, valor pendente, `-x`, duplicata, vazio, sem formulário) → Task 1 (testes) + Task 1 Step 3 (implementação) ✓
- Remoção de `_opts_form` e `shared_options` → Task 2 Steps 1-2 ✓
- `context_settings` + `pass_context` + docstring → Task 2 Step 3 ✓
- `report.py` sem mudanças, fallback de rótulos → testado em Task 1 (`test_report.py`) ✓
- Remoção de `extrair_tipo_formulario` + `__all__` → Task 3 ✓
- Critérios de aceite da spec → Task 4 (todos os 7) ✓

**Placeholders:** nenhum — todo passo tem código/commando concreto.

**Consistência de tipos:** `coletar_arquivos_formulario(args: List[str]) -> Dict[str, str]` é a mesma assinatura em testes, implementação e chamada em `main()` (`coletar_arquivos_formulario(ctx.args)` — `ctx.args` é `List[str]`). Nomes das variáveis consistentes entre tarefas (`pendente`, `formularios`).
